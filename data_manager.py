"""Load canteen records from CSV and reject data the dashboard cannot use."""

from pathlib import Path

import pandas as pd

# sample_data.csv lives in the data folder next to this file.
SAMPLE_DATA_PATH = Path(__file__).resolve().parent / "data" / "sample_data.csv"

REQUIRED_COLUMNS = [
    "date",
    "meal",
    "item",
    "category",
    "portions_prepared",
    "portions_served",
    "portions_wasted",
    "waste_kg",
    "cost_per_portion",
    "reason",
]

NUMBER_COLUMNS = [
    "portions_prepared",
    "portions_served",
    "portions_wasted",
    "waste_kg",
    "cost_per_portion",
]


class DataError(Exception):
    """The canteen file is missing or cannot be shown safely."""


def load_records(csv_path=None):
    """Read canteen rows into a table.

    Returns (table, warnings).
    Raises DataError with a short message when the file cannot be used.
    csv_path: optional path to another CSV. Uses the sample file when omitted.
    """
    path = Path(csv_path) if csv_path else SAMPLE_DATA_PATH
    table = _read_csv(path)
    _check_columns(table)

    cleaned, warnings = _clean_rows(table)
    cleaned = cleaned.sort_values(["date", "meal", "item"]).reset_index(drop=True)
    return cleaned, warnings


def _read_csv(path):
    """Open the CSV or raise DataError with a message for the dashboard."""
    if not path.exists():
        raise DataError(
            f"Could not find the canteen file at {path}. "
            "Add data/sample_data.csv, then refresh this page."
        )

    try:
        table = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise DataError("The canteen file is empty. Add at least one food record.")
    except pd.errors.ParserError:
        raise DataError(
            "The canteen file is not a valid CSV. Check for broken quotes or extra commas."
        )
    except OSError as error:
        raise DataError(f"The canteen file could not be read. Details: {error}")

    if table.empty:
        raise DataError("The canteen file has column names but no food records.")

    return table


def _check_columns(table):
    """Make sure every column the dashboard expects is present."""
    missing = [name for name in REQUIRED_COLUMNS if name not in table.columns]
    if missing:
        names = ", ".join(missing)
        raise DataError(f"The canteen file is missing required columns: {names}.")


def _clean_rows(table):
    """Keep rows with real dates and numbers. Collect a short warning list."""
    cleaned = table.copy()
    warnings = []

    for column in NUMBER_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    invalid_numbers = cleaned[NUMBER_COLUMNS].isna().any(axis=1)
    invalid_count = int(invalid_numbers.sum())
    cleaned = cleaned.loc[~invalid_numbers].copy()

    if cleaned.empty:
        raise DataError(
            "Every row has a missing or non-numeric portion, weight, or cost. "
            "Fix sample_data.csv, then refresh this page."
        )

    negative_numbers = (cleaned[NUMBER_COLUMNS] < 0).any(axis=1)
    negative_count = int(negative_numbers.sum())
    cleaned = cleaned.loc[~negative_numbers].copy()

    if cleaned.empty:
        raise DataError(
            "Every row has a missing, non-numeric, or negative value. "
            "Portions, weight, and cost must be zero or greater."
        )

    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    bad_dates = int(cleaned["date"].isna().sum())
    cleaned = cleaned.dropna(subset=["date"]).copy()

    if cleaned.empty:
        raise DataError("None of the dates could be read. Use dates like 2026-10-26.")

    if invalid_count:
        warnings.append(f"Skipped {invalid_count} row(s) with missing or invalid numbers.")
    if negative_count:
        warnings.append(f"Skipped {negative_count} row(s) with negative numbers.")
    if bad_dates:
        warnings.append(f"Skipped {bad_dates} row(s) with a date that could not be read.")

    return cleaned, warnings
