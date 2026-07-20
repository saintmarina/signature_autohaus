import pandas as pd

def normalize_text(value):
    # Convert NaN/None into empty string, then trim spaces and lowercase.
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def group_years_into_ranges(years):
    # Convert [2012, 2013, 2017] into [(2012, 2013), (2017, 2017)].
    years = sorted(set(int(y) for y in years))

    # If there are no missing years, return an empty list.
    if not years:
        return []

    # Start the first range.
    ranges = []
    range_start = range_end = years[0]

    # Walk through the remaining years.
    for year in years[1:]:
        # If this year continues the current range, extend the range.
        if year == range_end + 1:
            range_end = year
        # Otherwise close the current range and start a new one.
        else:
            ranges.append((range_start, range_end))
            range_start = range_end = year

    # Add the final open range.
    ranges.append((range_start, range_end))

    return ranges


def year_range_text(start_year, end_year):
    # Return "2017" for one year, or "2012-2017" for a range.
    return str(start_year) if start_year == end_year else f"{start_year}-{end_year}"



def find_missing_custom_fitments(matches, product_row, start_year, end_year, make, model, submodel=""):
    """
    Finds fitments that AI requested but the CSV did not fully cover.

    Rules:
    1. If the exact AI model is not present in CSV matches,
       create one custom fitment for the full requested AI range/model.
    2. If the exact model is present but some requested years are missing,
       create custom fitments only for the missing years.
    3. For CSV-derived submodels, preserve exactly what the CSV has.
    4. For custom AI fitment with no submodel, use Base.
    """

    custom_fitments = []

    sku = (
        ""
        if product_row is None or pd.isna(product_row["Variant SKU"])
        else str(product_row["Variant SKU"]).strip()
    )

    requested_years = set(range(int(start_year), int(end_year) + 1))

    requested_model_normalized = normalize_text(model)
    requested_submodel_normalized = normalize_text(submodel)

    custom_submodel = str(submodel).strip() if str(submodel).strip() else "Base"

    if matches.empty:
        custom_fitments.append({
            "SKU": sku,
            "year": year_range_text(start_year, end_year),
            "make": make,
            "model": model,
            "submodel": custom_submodel,
            "universal": "",
        })

        print(
            f"No CSV fitment found for SKU {sku}: "
            f"{start_year}-{end_year} {make} {model} {custom_submodel}"
        )

        return custom_fitments

    matches = matches.copy()

    matches["model_normalized"] = matches["model"].apply(normalize_text)
    matches["submodel"] = matches["submodel"].fillna("").astype(str).str.strip()

    exact_model_matches = matches[
        matches["model_normalized"] == requested_model_normalized
    ]

    if exact_model_matches.empty:
        custom_fitments.append({
            "SKU": sku,
            "year": year_range_text(start_year, end_year),
            "make": make,
            "model": model,
            "submodel": custom_submodel,
            "universal": "",
        })

        return custom_fitments

    found_years = set(
        exact_model_matches["year"]
        .dropna()
        .astype(int)
        .tolist()
    )

    missing_years = sorted(requested_years - found_years)

    if not missing_years:
        return custom_fitments

    if requested_submodel_normalized:
        submodels_to_create = [str(submodel).strip()]
    else:
        submodels_to_create = (
            exact_model_matches["submodel"]
            .drop_duplicates()
            .tolist()
        )

        submodels_to_create = [
            sm if sm else "Base"
            for sm in submodels_to_create
        ]

    for missing_start, missing_end in group_years_into_ranges(missing_years):
        for missing_submodel in submodels_to_create:
            custom_fitments.append({
                "SKU": sku,
                "year": year_range_text(missing_start, missing_end),
                "make": make,
                "model": model,
                "submodel": missing_submodel,
                "universal": "",
            })

    return custom_fitments


def get_matching_csv_rows(fitment_df, start_year, end_year, make, model, submodel=""):
    """
    Returns matching rows from nexus_ymms.csv for a vehicle fitment.

    Matching is based on:
    - year range
    - make
    - exact model match
    - plus model prefix match when the model has spaces

    Submodel behavior:
    - Returns submodels exactly as they exist in the CSV.
    - If submodel is provided and exact submodel matches exist, returns only those.
    - Otherwise returns all matching rows for year/make/model logic.
    """

    normalized_make = make.strip().lower()
    normalized_model = model.strip().lower()
    normalized_submodel = submodel.strip().lower() if submodel else ""

    base_matches = fitment_df[
        (fitment_df["year"].astype(int) >= int(start_year)) &
        (fitment_df["year"].astype(int) <= int(end_year)) &
        (fitment_df["make"].astype(str).str.strip().str.lower() == normalized_make)
    ].copy()

    if base_matches.empty:
        return base_matches

    csv_model_normalized = base_matches["model"].astype(str).str.strip().str.lower()

    exact_model_mask = csv_model_normalized == normalized_model

    model_parts = normalized_model.split()

    if len(model_parts) > 1:
        first_model_part = model_parts[0]
        prefix_model_mask = csv_model_normalized.str.startswith(first_model_part)
        model_mask = exact_model_mask | prefix_model_mask
    else:
        prefix_model_mask = csv_model_normalized.str.startswith(normalized_model + " ")
        model_mask = exact_model_mask | prefix_model_mask

    matches = base_matches[model_mask].copy()

    if matches.empty:
        return matches

    matches["submodel"] = matches["submodel"].fillna("").astype(str).str.strip()

    if normalized_submodel:
        exact_submodel_matches = matches[
            matches["submodel"].str.lower() == normalized_submodel
        ]

        if not exact_submodel_matches.empty:
            return exact_submodel_matches

    return matches

def save_custom_fitments(custom_fitment_df, custom_fitment_file, missing_custom_fitments):
    if not missing_custom_fitments:
        return custom_fitment_df

    new_rows = pd.DataFrame([
        {
            "SKU": str(f["SKU"]).strip(),
            "Year": str(f["year"]).strip(),
            "Make": str(f["make"]).strip(),
            "Model": str(f["model"]).strip(),
            "Submodel": str(f["submodel"]).strip(),
            "Universal": str(f.get("universal", "")).strip(),
        }
        for f in missing_custom_fitments
    ])

    custom_fitment_df = pd.concat(
        [custom_fitment_df, new_rows],
        ignore_index=True
    )

    custom_fitment_df = (
        custom_fitment_df
        .drop_duplicates()
        .sort_values(["Make", "Model", "Year", "Submodel", "SKU"])
    )

    custom_fitment_df.to_excel(custom_fitment_file, index=False)

    return custom_fitment_df

def compress_fitment_years(metadata_rows):
    """
    Converts yearly fitments into year ranges.

    Example:
        2019|BMW|M340i|Base
        2020|BMW|M340i|Base
        2021|BMW|M340i|Base

    Becomes: 2019-2021|BMW|M340i|Base
    """
    grouped = {}

    for row in metadata_rows:
        parts = row.split("|")

        if len(parts) == 3:
            year_text, make, model = parts
            submodel = None
        elif len(parts) == 4:
            year_text, make, model, submodel = parts
        else:
            raise ValueError(f"Invalid metadata row format: {row}")

        if "-" in year_text:
            start_year, end_year = [int(x) for x in year_text.split("-", 1)]
            years = list(range(start_year, end_year + 1))
        else:
            years = [int(year_text)]

        grouped.setdefault((make, model, submodel), []).extend(years)

    compressed_rows = []

    for (make, model, submodel), years in grouped.items():
        years = sorted(set(years))
        start = end = years[0]

        for year in years[1:]:
            if year == end + 1:
                end = year
                continue

            year_text = f"{start}-{end}" if start != end else str(start)
            compressed_rows.append(f"{year_text}|{make}|{model}" if submodel is None else f"{year_text}|{make}|{model}|{submodel}")
            start = end = year

        year_text = f"{start}-{end}" if start != end else str(start)
        compressed_rows.append(f"{year_text}|{make}|{model}" if submodel is None else f"{year_text}|{make}|{model}|{submodel}")

    return compressed_rows


def build_metadata_rows_from_matches_and_custom_fitments(matches, missing_custom_fitments):
    """
    Combines CSV matches and missing custom fitments into raw yearly metadata rows.

    Returns uncompressed metadata strings in this format:
        year|make|model|submodel

    These rows should be passed into compress_fitment_years() afterward.
    """
    metadata_rows = []

    if matches is not None and not matches.empty:
        for _, row in matches.iterrows():
            year = int(row["year"])
            make = str(row["make"]).strip()
            model = str(row["model"]).strip()
            submodel = "" if pd.isna(row["submodel"]) else str(row["submodel"]).strip()

            metadata_rows.append(f"{year}|{make}|{model}|{submodel}")

    for fitment in missing_custom_fitments:
        year = str(fitment["year"]).strip()
        make = str(fitment["make"]).strip()
        model = str(fitment["model"]).strip()
        submodel = str(fitment["submodel"]).strip()

        metadata_rows.append(f"{year}|{make}|{model}|{submodel}")

    return compress_fitment_years(metadata_rows)

def resolve_vehicle_fitments_to_metadata(
    fitment_df,
    vehicle_fitments,
    custom_fitment_df,
    custom_fitment_file,
    product_row=None,
):
    """
    Converts AI vehicle_fitments into final Convermax metadata.

    Flow:
    1. Get matching CSV rows.
    2. Find missing custom fitments.
    3. Save missing custom fitments.
    4. Build compressed metadata from both CSV matches and custom fitments.

    Returns:
        metadata_rows,
        custom_fitment_df,
        fitment_review_notes,
        created_custom_fitments
    """

    all_metadata_rows = []
    fitment_review_notes = []
    all_created_custom_fitments = []

    for vf in vehicle_fitments:
        start_year = int(vf["start_year"])
        end_year = int(vf["end_year"])
        make = str(vf["make"]).strip()
        model = str(vf["model"]).strip()
        submodel = str(vf.get("submodel", "")).strip()

        review_reason = get_generic_fitment_review_reason(
            start_year,
            end_year,
            make,
            model,
            submodel,
        )

        if review_reason:
            fitment_review_notes.append(review_reason)
            continue

        csv_matches = get_matching_csv_rows(
            fitment_df=fitment_df,
            start_year=start_year,
            end_year=end_year,
            make=make,
            model=model,
            submodel=submodel,
        )

        custom_matches = get_matching_custom_fitment_rows(
            custom_fitment_df=custom_fitment_df,
            start_year=start_year,
            end_year=end_year,
            make=make,
            model=model,
            submodel=submodel,
        )

        matches = pd.concat(
            [csv_matches, custom_matches],
            ignore_index=True
        ).drop_duplicates()

        missing_custom_fitments = find_missing_custom_fitments(
            matches=matches,
            product_row=product_row,
            start_year=start_year,
            end_year=end_year,
            make=make,
            model=model,
            submodel=submodel,
        )

        custom_fitment_df = save_custom_fitments(
            custom_fitment_df=custom_fitment_df,
            custom_fitment_file=custom_fitment_file,
            missing_custom_fitments=missing_custom_fitments,
        )

        metadata_rows = build_metadata_rows_from_matches_and_custom_fitments(
            matches=matches,
            missing_custom_fitments=missing_custom_fitments,
        )

        all_metadata_rows.extend(metadata_rows)
        all_created_custom_fitments.extend(missing_custom_fitments)

    all_metadata_rows = sorted(set(all_metadata_rows))
    return (all_metadata_rows, custom_fitment_df, fitment_review_notes, all_created_custom_fitments)

def get_generic_fitment_review_reason(start_year, end_year, make, model, submodel):
    """
    Returns a review reason if the AI fitment is too generic
    to create metadata or custom fitments.

    Returns:
        None if the fitment is acceptable.
        Otherwise a review reason string.
    """

    model_lower = model.lower()
    submodel_lower = submodel.lower()

    if "series" not in model_lower and "series" not in submodel_lower:
        return None

    year_text = (
        str(start_year)
        if start_year == end_year
        else f"{start_year}-{end_year}"
    )

    vehicle = f"{year_text} {make} {model}".strip()

    if submodel:
        vehicle += f" {submodel}"

    return f"No fitment found: {vehicle}"

def expand_year_text_to_years(year_text):
    """
    Converts a year or year range into a list of years.

    Examples:
        "2018" -> [2018]
        "2018-2020" -> [2018, 2019, 2020]
    """

    year_text = str(year_text).strip()

    if "-" not in year_text:
        return [int(year_text)]

    start_year, end_year = [
        int(year)
        for year in year_text.split("-", 1)
    ]

    return list(range(start_year, end_year + 1))

def get_matching_custom_fitment_rows(custom_fitment_df, start_year, end_year, make, model, submodel=""):
    """
    Returns matching rows from existing custom_fitments.xlsx.
    Output columns match get_matching_csv_rows():
        year, make, model, submodel
    """

    if custom_fitment_df is None or custom_fitment_df.empty:
        return pd.DataFrame(columns=["year", "make", "model", "submodel"])

    requested_years = set(range(int(start_year), int(end_year) + 1))

    normalized_make = make.strip().lower()
    normalized_model = model.strip().lower()
    normalized_submodel = submodel.strip().lower() if submodel else ""

    rows = []

    for _, row in custom_fitment_df.iterrows():
        row_make = str(row["Make"]).strip()
        row_model = str(row["Model"]).strip()
        row_submodel = "" if pd.isna(row["Submodel"]) else str(row["Submodel"]).strip()
        row_year_text = str(row["Year"]).strip()

        if row_make.lower() != normalized_make:
            continue

        if row_model.lower() != normalized_model:
            continue

        if normalized_submodel and row_submodel.lower() != normalized_submodel:
            continue

        custom_years = set(expand_year_text_to_years(row_year_text))
        matching_years = sorted(requested_years & custom_years)

        for year in matching_years:
            rows.append({
                "year": year,
                "make": row_make,
                "model": row_model,
                "submodel": row_submodel,
            })

    return pd.DataFrame(rows, columns=["year", "make", "model", "submodel"])

def metadata_to_fitment_tag(metadata_rows, max_tag_length=255):
    """
    Returns one or more comma-separated Shopify fitment tags.
    Every individual tag is at most 255 characters.
    """

    if not metadata_rows:
        return ""

    converted_rows = [
        row.replace("|", "`")
        for row in metadata_rows
    ]

    tags = []
    current_rows = []

    for row in converted_rows:
        single_tag = f"fits_{row}"

        if len(single_tag) > max_tag_length:
            raise ValueError(
                f"Individual fitment exceeds Shopify's "
                f"{max_tag_length}-character limit "
                f"({len(single_tag)} characters): {row}"
            )

        candidate = "fits_" + "~".join(current_rows + [row])

        if len(candidate) <= max_tag_length:
            current_rows.append(row)
        else:
            tags.append("fits_" + "~".join(current_rows))
            current_rows = [row]

    if current_rows:
        tags.append("fits_" + "~".join(current_rows))

    return ", ".join(tags)

def filter_review_notes(review_notes):
    """
    Removes ignored review notes.
    Returns:
        filtered_review_notes,
        ignored_review_notes
    """

    ignored_review_reasons = {
        "title_price_description_scope_conflict",
        "vehicle_fitment_submodel_unclear",
        "vehicle_fitment_submodel_ambiguous",
        "weight_low_confidence",
        "fitment_year_conflict",
    }

    ignored_review_reason_prefixes = (
        "fitment_conflict",
    )

    filtered = []
    ignored = []

    for note in sorted(set(review_notes)):
        if (
            note in ignored_review_reasons
            or any(note.startswith(prefix) for prefix in ignored_review_reason_prefixes)
        ):
            ignored.append(note)
        else:
            filtered.append(note)

    return filtered, ignored
