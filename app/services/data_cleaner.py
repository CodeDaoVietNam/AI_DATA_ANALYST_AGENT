from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


AMAZON_DROP_COLUMNS = ("index", "unnamed_22")

AMAZON_TEXT_COLUMNS = (
    "status",
    "fulfilment",
    "sales_channel",
    "ship_service_level",
    "category",
    "size",
    "courier_status",
    "currency",
    "ship_country",
    "ship_city",
    "ship_state",
    "fulfilled_by",
)

AMAZON_LOCATION_COLUMNS = ("ship_city", "ship_state", "ship_country")


def clean_column_name(column: str) -> str:
    """Normalize a column name into a predictable snake_case-like format."""
    cleaned = str(column).strip().lower()
    cleaned = cleaned.replace("-", "_").replace(" ", "_").replace(":", "")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the DataFrame with normalized column names."""
    result = df.copy()
    result.columns = [clean_column_name(column) for column in result.columns]
    return result


def clean_amazon_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the Amazon Sales dataset shape discovered in the EDA notebook.

    Generic CSVs should use `clean_column_names`; this function is intentionally
    domain-specific because it knows about Amazon sales columns such as date,
    ship_city, ship_state, and category.
    """
    result = clean_column_names(df)

    result = result.drop(
        columns=[column for column in AMAZON_DROP_COLUMNS if column in result.columns],
        errors="ignore",
    )

    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"], format="%m-%d-%y", errors="coerce")

    _strip_text_columns(result, AMAZON_TEXT_COLUMNS)
    _uppercase_text_columns(result, AMAZON_LOCATION_COLUMNS)

    if "category" in result.columns:
        result["category"] = result["category"].str.title()

    return result


def _strip_text_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for column in columns:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()


def _uppercase_text_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for column in columns:
        if column in df.columns:
            df[column] = df[column].str.upper()
