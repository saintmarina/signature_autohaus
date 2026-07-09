from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill
from openpyxl.utils import get_column_letter
import random
from openai import RateLimitError
import time
import json
import pandas as pd

def pixels_to_excel_width(px):
    return px / 7

def format_products_workbook(file_path):
    wb = load_workbook(file_path)
    ws = wb.active

    column_widths_px = {
        "Title": 260,
        "Tags": 260,
        "Metafield: convermax.fitment [list.single_line_text_field]": 360,
        "AI Review Reasons": 260,
        "Custom Collections": 160,
        "Variant SKU": 170,
        "Type": 120,
    }

    review_fill = PatternFill(
        start_color="F2F2F2",
        end_color="F2F2F2",
        fill_type="solid"
    )

    for cell in ws[1]:
        col_name = cell.value
        if col_name in column_widths_px:
            col_letter = get_column_letter(cell.column)
            ws.column_dimensions[col_letter].width = pixels_to_excel_width(
                column_widths_px[col_name]
            )

            for row_cell in ws[col_letter]:
                row_cell.alignment = Alignment(
                    wrap_text=True,
                    vertical="top"
                )

            if col_name == "AI Review Reasons":
                for row_cell in ws[col_letter]:
                    row_cell.fill = review_fill

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    wb.save(file_path)

def safe_call_ai_for_row(client, prompt_id, prompt_version, row_index, row, max_retries=6):
    for attempt in range(max_retries):
        try:
            return call_ai_for_row(
                client,
                prompt_id,
                prompt_version,
                row_index,
                row
            )

        except RateLimitError as e:
            wait = min(60, (2 ** attempt) + random.uniform(0, 1))
            print(e)
            time.sleep(wait)

    raise RuntimeError(f"Failed row {row_index} after {max_retries} retries")

def format_tags(tags):
    """
    Converts a list of tags back into a clean Shopify comma-separated tag string.

    Also:
    - trims whitespace
    - removes empty tags
    - removes duplicate tags
    - sorts tags for stable output
    """

    tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    return ", ".join(sorted(set(tags)))

def call_ai_for_row(client, prompt_id, prompt_version, row_index, row):
    """
    Sends one spreadsheet row to OpenAI and returns parsed JSON.
    Returns:
        {
            "row_index": row_index,
            "ai_result": parsed_ai_json
        }
    """

    product = build_product_input(row)

    response = client.responses.create(
        prompt={
            "id": prompt_id,
            "version": prompt_version,
            "variables": {
                "product": json.dumps(product, ensure_ascii=False)
            }
        }
    )

    return {
        "row_index": row_index,
        "ai_result": json.loads(response.output_text)
    }

def parse_tags(value):
    """
    Converts Shopify comma-separated tags into a Python list.
    Example: "BMW, Exhaust, M340i"
    Returns: ["BMW", "Exhaust", "M340i"]
    """

    if pd.isna(value) or str(value).strip() == "":
        return []

    return [
        tag.strip()
        for tag in str(value).split(",")
        if tag.strip()
    ]

def build_product_input(row):
    """
    Converts a spreadsheet row into the JSON object that is sent to OpenAI.
    This is the ONLY place where spreadsheet columns are mapped into AI input fields.
    """

    return {
        "title": "" if pd.isna(row["Title"]) else str(row["Title"]),
        "body_html": "" if pd.isna(row["Body HTML"]) else str(row["Body HTML"]),
        "vendor": "" if pd.isna(row["Vendor"]) else str(row["Vendor"]),
        "tags": parse_tags(row["Tags"]),
        "current_weight": (
            0
            if pd.isna(row["Variant Weight"])
            else float(row["Variant Weight"])
        ),
        "price": 0 if pd.isna(row["Variant Price"]) else float(row["Variant Price"]),
    }
