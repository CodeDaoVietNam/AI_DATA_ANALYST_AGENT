import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from app.services.data_cleaner import (
    clean_amazon_sales_data,
    clean_column_name,
    clean_column_names,
)


def test_clean_column_name():
    assert clean_column_name("Order ID") == "order_id"
    assert clean_column_name("Sales Channel ") == "sales_channel"
    assert clean_column_name("ship-service-level") == "ship_service_level"
    assert clean_column_name("Unnamed: 22") == "unnamed_22"


def test_clean_column_names_does_not_mutate_input():
    df = pd.DataFrame({
        "Order ID": ["1"],
        "Sales Channel ": ["Amazon.in"],
    })

    cleaned = clean_column_names(df)

    assert list(df.columns) == ["Order ID", "Sales Channel "]
    assert list(cleaned.columns) == ["order_id", "sales_channel"]


def test_clean_amazon_sales_columns():
    df = pd.DataFrame({
        "index": [0],
        "Order ID": ["1"],
        "Date": ["04-30-22"],
        "Sales Channel ": ["Amazon.in"],
        "ship-city": ["Hyderabad"],
        "ship-state": ["Telangana"],
        "Category": ["kurta"],
        "Unnamed: 22": [None],
    })

    cleaned = clean_amazon_sales_data(df)

    assert "order_id" in cleaned.columns
    assert "sales_channel" in cleaned.columns
    assert "ship_city" in cleaned.columns
    assert "index" not in cleaned.columns
    assert "unnamed_22" not in cleaned.columns
    assert is_datetime64_any_dtype(cleaned["date"])
    assert cleaned.loc[0, "ship_city"] == "HYDERABAD"
    assert cleaned.loc[0, "ship_state"] == "TELANGANA"
    assert cleaned.loc[0, "category"] == "Kurta"


def test_clean_amazon_sales_handles_missing_optional_columns():
    df = pd.DataFrame({
        "Order ID": ["1"],
        "Date": ["not-a-date"],
    })

    cleaned = clean_amazon_sales_data(df)

    assert "order_id" in cleaned.columns
    assert pd.isna(cleaned.loc[0, "date"])
