import pandas as pd
from fitment_logic import (
    find_missing_custom_fitments,
    build_metadata_rows_from_matches_and_custom_fitments,
    get_matching_custom_fitment_rows,
    get_matching_csv_rows,
)

def normalize_rows(rows):
    return sorted(rows, key=lambda r: (
        r["SKU"],
        r["year"],
        r["make"],
        r["model"],
        r["submodel"],
        r["universal"],
    ))


def assert_custom_fitments_equal(actual, expected, test_name):
    actual_sorted = normalize_rows(actual)
    expected_sorted = normalize_rows(expected)

    assert actual_sorted == expected_sorted, (
        f"\nFAILED: {test_name}\n"
        f"Expected:\n{expected_sorted}\n\n"
        f"Actual:\n{actual_sorted}\n"
    )

    print(f"PASSED: {test_name}")


def make_product_row(sku="SKU123"):
    return pd.Series({
        "Variant SKU": sku
    })


def run_find_missing_custom_fitments_tests():
    product_row = make_product_row("SKU123")

    # ------------------------------------------------------------
    # Test 1:
    # CSV matches only broad model RS7, but AI requested RS7 Sportback.
    # Exact model is missing, so create full custom range.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2013, "make": "Audi", "model": "RS7", "submodel": "Base"},
        {"year": 2014, "make": "Audi", "model": "RS7", "submodel": "Performance"},
        {"year": 2015, "make": "Audi", "model": "RS7", "submodel": "Premium"},
        {"year": 2016, "make": "Audi", "model": "RS7", "submodel": "Base"},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2017,
        make="Audi",
        model="RS7 Sportback",
        submodel=""
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2012-2017",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        }
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Exact model missing creates full custom AI fitment"
    )

    # ------------------------------------------------------------
    # Test 2:
    # Exact model exists, but years 2012 and 2016-2017 are missing.
    # AI did not provide submodel, so use CSV submodels.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2013, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2014, "make": "Audi", "model": "RS7 Sportback", "submodel": "Performance"},
        {"year": 2015, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2017,
        make="Audi",
        model="RS7 Sportback",
        submodel=""
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2012",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2012",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Performance",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2016-2017",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2016-2017",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Performance",
            "universal": "",
        },
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Exact model exists and missing years use CSV submodels"
    )

    # ------------------------------------------------------------
    # Test 3:
    # Exact model exists and all requested years exist.
    # Nothing should be created.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2012, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2013, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2014, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2014,
        make="Audi",
        model="RS7 Sportback",
        submodel=""
    )

    expected = []

    assert_custom_fitments_equal(
        actual,
        expected,
        "Exact model exists and all years covered creates nothing"
    )

    # ------------------------------------------------------------
    # Test 4:
    # Exact model exists, AI provides submodel.
    # Missing years should use AI submodel only.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2013, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2014, "make": "Audi", "model": "RS7 Sportback", "submodel": "Performance"},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2015,
        make="Audi",
        model="RS7 Sportback",
        submodel="Performance"
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2012",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Performance",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2015",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Performance",
            "universal": "",
        },
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "AI submodel provided uses AI submodel only"
    )

    # ------------------------------------------------------------
    # Test 5:
    # Matches are completely empty.
    # Create full custom fitment.
    # ------------------------------------------------------------
    matches = pd.DataFrame(columns=["year", "make", "model", "submodel"])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2020,
        end_year=2023,
        make="BMW",
        model="M3",
        submodel=""
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2020-2023",
            "make": "BMW",
            "model": "M3",
            "submodel": "Base",
            "universal": "",
        }
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Empty matches creates full custom fitment"
    )

    # ------------------------------------------------------------
    # Test 6:
    # Missing years have a gap: 2012, 2014, 2015.
    # Should become 2012 and 2014-2015, not 2012-2015.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2013, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2016, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2016,
        make="Audi",
        model="RS7 Sportback",
        submodel=""
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2012",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2014-2015",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Missing years with gap stay separated"
    )

    # ------------------------------------------------------------
    # Test 7:
    # CSV submodel is empty.
    # For custom output, empty CSV submodel becomes Base.
    # Universal stays empty.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2013, "make": "Audi", "model": "RS7 Sportback", "submodel": ""},
    ])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row,
        start_year=2012,
        end_year=2014,
        make="Audi",
        model="RS7 Sportback",
        submodel=""
    )

    expected = [
        {
            "SKU": "SKU123",
            "year": "2012",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
        {
            "SKU": "SKU123",
            "year": "2014",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        },
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Empty CSV submodel becomes Base only for custom output"
    )

    # ------------------------------------------------------------
    # Test 8:
    # SKU is missing.
    # Should use empty SKU instead of crashing.
    # ------------------------------------------------------------
    product_row_missing_sku = make_product_row(pd.NA)

    matches = pd.DataFrame(columns=["year", "make", "model", "submodel"])

    actual = find_missing_custom_fitments(
        matches=matches,
        product_row=product_row_missing_sku,
        start_year=2020,
        end_year=2020,
        make="Porsche",
        model="911",
        submodel=""
    )

    expected = [
        {
            "SKU": "",
            "year": "2020",
            "make": "Porsche",
            "model": "911",
            "submodel": "Base",
            "universal": "",
        }
    ]

    assert_custom_fitments_equal(
        actual,
        expected,
        "Missing SKU becomes empty string"
    )

    print("\nAll find_missing_custom_fitments tests passed.")


# ---------------------------------------------------------------------------
# Tests for build_metadata_rows_from_matches_and_custom_fitments
# ---------------------------------------------------------------------------

def run_build_metadata_rows_from_matches_and_custom_fitments_tests():
    print("\nRunning build_metadata_rows_from_matches_and_custom_fitments tests...\n")

    # ------------------------------------------------------------
    # Test 1:
    # CSV has 2012, 2014, 2015.
    # Custom gap fills 2013.
    # Final metadata should be compressed into one range:
    # 2012-2015|Audi|RS7|Base.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2012, "make": "Audi", "model": "RS7", "submodel": "Base"},
        {"year": 2014, "make": "Audi", "model": "RS7", "submodel": "Base"},
        {"year": 2015, "make": "Audi", "model": "RS7", "submodel": "Base"},
    ])

    missing_custom_fitments = [
        {
            "SKU": "SKU123",
            "year": "2013",
            "make": "Audi",
            "model": "RS7",
            "submodel": "Base",
            "universal": "",
        }
    ]

    print("Test 1 matches input:")
    print(matches)
    print("Test 1 missing custom fitments input:")
    print(missing_custom_fitments)

    actual = build_metadata_rows_from_matches_and_custom_fitments(
        matches,
        missing_custom_fitments,
    )

    expected = [
        "2012-2015|Audi|RS7|Base",
    ]

    print("Test 1 actual compressed metadata rows:")
    print(actual)

    assert sorted(actual) == sorted(expected), (
        "\nFAILED: CSV rows plus one custom gap should produce compressed metadata rows\n"
        f"Expected:\n{sorted(expected)}\n\n"
        f"Actual:\n{sorted(actual)}\n"
    )

    print("PASSED: CSV rows plus one custom gap produce compressed metadata rows")

    # ------------------------------------------------------------
    # Test 2:
    # Custom fitment has a year range.
    # The method should combine CSV years plus custom range into one compressed range.
    # ------------------------------------------------------------
    matches = pd.DataFrame([
        {"year": 2014, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
        {"year": 2015, "make": "Audi", "model": "RS7 Sportback", "submodel": "Base"},
    ])

    missing_custom_fitments = [
        {
            "SKU": "SKU123",
            "year": "2016-2017",
            "make": "Audi",
            "model": "RS7 Sportback",
            "submodel": "Base",
            "universal": "",
        }
    ]

    print("\nTest 2 matches input:")
    print(matches)
    print("Test 2 missing custom fitments input:")
    print(missing_custom_fitments)

    actual = build_metadata_rows_from_matches_and_custom_fitments(
        matches,
        missing_custom_fitments,
    )

    expected = [
        "2014-2017|Audi|RS7 Sportback|Base",
    ]

    print("Test 2 actual compressed metadata rows:")
    print(actual)

    assert sorted(actual) == sorted(expected), (
        "\nFAILED: CSV rows plus custom year range should compress into one metadata row\n"
        f"Expected:\n{sorted(expected)}\n\n"
        f"Actual:\n{sorted(actual)}\n"
    )

    print("PASSED: CSV rows plus custom year range compress into one metadata row")

    # ------------------------------------------------------------
    # Test 3:
    # Empty matches, only custom fitment.
    # Should still create compressed metadata from the custom fitment.
    # ------------------------------------------------------------
    matches = pd.DataFrame(columns=["year", "make", "model", "submodel"])

    missing_custom_fitments = [
        {
            "SKU": "SKU123",
            "year": "2020-2021",
            "make": "BMW",
            "model": "M3",
            "submodel": "Base",
            "universal": "",
        }
    ]

    print("\nTest 3 matches input:")
    print(matches)
    print("Test 3 missing custom fitments input:")
    print(missing_custom_fitments)

    actual = build_metadata_rows_from_matches_and_custom_fitments(
        matches,
        missing_custom_fitments,
    )

    expected = [
        "2020-2021|BMW|M3|Base",
    ]

    print("Test 3 actual compressed metadata rows:")
    print(actual)

    assert sorted(actual) == sorted(expected), (
        "\nFAILED: Empty CSV matches should still create compressed metadata from custom fitments\n"
        f"Expected:\n{sorted(expected)}\n\n"
        f"Actual:\n{sorted(actual)}\n"
    )

    print("PASSED: Empty CSV matches still create compressed metadata from custom fitments")

    print("\nAll build_metadata_rows_from_matches_and_custom_fitments tests passed.")

def run_get_matching_custom_fitment_rows_tests():
    print("\nRunning get_matching_custom_fitment_rows tests...\n")

    custom_fitment_df = pd.DataFrame([
        {
            "SKU": "SKU1",
            "Year": "2016-2020",
            "Make": "Ferrari",
            "Model": "GTC4 Lusso",
            "Submodel": "V12",
            "Universal": "",
        },
        {
            "SKU": "SKU2",
            "Year": "2020",
            "Make": "Ferrari",
            "Model": "GTC4Lusso T",
            "Submodel": "Base",
            "Universal": "",
        },
        {
            "SKU": "SKU3",
            "Year": "2018-2019",
            "Make": "BMW",
            "Model": "M3",
            "Submodel": "Competition",
            "Universal": "",
        },
    ])

    # ------------------------------------------------------------
    # Test 1:
    # Custom fitment has range 2016-2020.
    # Request 2017-2019 should return yearly rows 2017, 2018, 2019.
    # ------------------------------------------------------------
    actual = get_matching_custom_fitment_rows(
        custom_fitment_df=custom_fitment_df,
        start_year=2017,
        end_year=2019,
        make="Ferrari",
        model="GTC4 Lusso",
        submodel="V12",
    )

    expected = pd.DataFrame([
        {"year": 2017, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2018, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2019, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
    ])

    print("Test 1 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: Custom range should expand and return overlapping requested years\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: Custom range expands to overlapping requested years")

    # ------------------------------------------------------------
    # Test 2:
    # If AI does not provide submodel, return matching custom rows
    # regardless of submodel.
    # ------------------------------------------------------------
    actual = get_matching_custom_fitment_rows(
        custom_fitment_df=custom_fitment_df,
        start_year=2016,
        end_year=2020,
        make="Ferrari",
        model="GTC4 Lusso",
        submodel="",
    )

    expected = pd.DataFrame([
        {"year": 2016, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2017, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2018, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2019, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
        {"year": 2020, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
    ])

    print("\nTest 2 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: Empty requested submodel should return all matching custom submodels\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: Empty requested submodel returns matching custom rows")

    # ------------------------------------------------------------
    # Test 3:
    # No overlapping years should return an empty DataFrame.
    # ------------------------------------------------------------
    actual = get_matching_custom_fitment_rows(
        custom_fitment_df=custom_fitment_df,
        start_year=2021,
        end_year=2022,
        make="Ferrari",
        model="GTC4 Lusso",
        submodel="V12",
    )

    print("\nTest 3 actual:")
    print(actual)

    assert actual.empty, (
        "\nFAILED: Non-overlapping years should return empty DataFrame\n"
        f"Actual:\n{actual}\n"
    )

    print("PASSED: Non-overlapping years return empty DataFrame")

    # ------------------------------------------------------------
    # Test 4:
    # Case and spaces should not matter.
    # ------------------------------------------------------------
    actual = get_matching_custom_fitment_rows(
        custom_fitment_df=custom_fitment_df,
        start_year=2018,
        end_year=2018,
        make=" ferrari ",
        model=" gtc4 lusso ",
        submodel=" v12 ",
    )

    expected = pd.DataFrame([
        {"year": 2018, "make": "Ferrari", "model": "GTC4 Lusso", "submodel": "V12"},
    ])

    print("\nTest 4 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: Matching should ignore case and surrounding spaces\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: Case and surrounding spaces do not affect matching")

    # ------------------------------------------------------------
    # Test 5:
    # Wrong model should return empty DataFrame.
    # ------------------------------------------------------------
    actual = get_matching_custom_fitment_rows(
        custom_fitment_df=custom_fitment_df,
        start_year=2018,
        end_year=2019,
        make="Ferrari",
        model="812 Superfast",
        submodel="Base",
    )

    print("\nTest 5 actual:")
    print(actual)

    assert actual.empty, (
        "\nFAILED: Wrong model should return empty DataFrame\n"
        f"Actual:\n{actual}\n"
    )

    print("PASSED: Wrong model returns empty DataFrame")

    print("\nAll get_matching_custom_fitment_rows tests passed.")

def run_get_matching_csv_rows_tests():
    print("\nRunning get_matching_csv_rows tests...\n")

    fitment_df = pd.DataFrame([
        {"year": 2017, "make": "BMW", "model": "M550i", "submodel": "Base"},
        {"year": 2018, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2019, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2020, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2021, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2022, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2020, "make": "BMW", "model": "M5", "submodel": "Base"},
        {"year": 2020, "make": "BMW", "model": "M5 Touring", "submodel": "Base"},
    ])

    # Test 1:
    # AI says M550i.
    # CSV has M550i xDrive.
    # We want exact M550i plus prefix M550i xDrive.
    actual = get_matching_csv_rows(
        fitment_df=fitment_df,
        start_year=2017,
        end_year=2022,
        make="BMW",
        model="M550i",
        submodel="",
    )

    expected = pd.DataFrame([
        {"year": 2017, "make": "BMW", "model": "M550i", "submodel": "Base"},
        {"year": 2018, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2019, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2020, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2021, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
        {"year": 2022, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
    ])

    print("\nTest 1 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: M550i should match exact M550i and prefix M550i xDrive\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: M550i matches exact and M550i xDrive prefix rows")

    # Test 2:
    # AI says M5.
    # It should match M5 and M5 Touring,
    # but NOT M550i xDrive.
    actual = get_matching_csv_rows(
        fitment_df=fitment_df,
        start_year=2020,
        end_year=2020,
        make="BMW",
        model="M5",
        submodel="",
    )

    expected = pd.DataFrame([
        {"year": 2020, "make": "BMW", "model": "M5", "submodel": "Base"},
        {"year": 2020, "make": "BMW", "model": "M5 Touring", "submodel": "Base"},
    ])

    print("\nTest 2 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: M5 should match M5 and M5 Touring, but not M550i xDrive\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: M5 does not incorrectly match M550i xDrive")

    # Test 3:
    # Case and spaces should not matter.
    actual = get_matching_csv_rows(
        fitment_df=fitment_df,
        start_year=2018,
        end_year=2018,
        make=" bmw ",
        model=" m550i ",
        submodel="",
    )

    expected = pd.DataFrame([
        {"year": 2018, "make": "BMW", "model": "M550i xDrive", "submodel": "Base"},
    ])

    print("\nTest 3 actual:")
    print(actual)

    assert actual.to_dict("records") == expected.to_dict("records"), (
        "\nFAILED: Matching should ignore case and surrounding spaces\n"
        f"Expected:\n{expected}\n\nActual:\n{actual}\n"
    )

    print("PASSED: Case and surrounding spaces do not affect matching")

    print("\nAll get_matching_csv_rows tests passed.")

if __name__ == "__main__":
    run_find_missing_custom_fitments_tests()
    run_build_metadata_rows_from_matches_and_custom_fitments_tests()
    run_get_matching_custom_fitment_rows_tests()
    run_get_matching_csv_rows_tests()