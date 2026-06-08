from __future__ import annotations

import numpy as np
import pandas as pd


def add_amazon_sales_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ecommerce features discovered in the Amazon Sales EDA notebook.

    The function is intentionally tolerant of missing optional columns so it can
    be used while the ingestion pipeline is still evolving.
    """
    result = df.copy()

    _add_time_features(result)
    _add_status_features(result)
    _add_promotion_feature(result)
    _add_revenue_features(result)

    return result


def _add_time_features(df: pd.DataFrame) -> None:
    if "date" not in df.columns:
        return

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["order_year"] = df["date"].dt.year
    df["order_month"] = df["date"].dt.to_period("M").astype("string")
    df["order_day"] = df["date"].dt.day
    df["order_day_name"] = df["date"].dt.day_name()


def _add_status_features(df: pd.DataFrame) -> None:
    if "status" in df.columns:
        df["status_clean"] = df["status"].astype("string").str.lower()
    else:
        df["status_clean"] = ""

    df["is_cancelled"] = df["status_clean"].str.contains("cancelled", na=False)
    df["is_shipped"] = df["status_clean"].str.contains("shipped", na=False)
    df["is_delivered"] = df["status_clean"].str.contains("delivered", na=False)


def _add_promotion_feature(df: pd.DataFrame) -> None:
    if "promotion_ids" in df.columns:
        df["has_promotion"] = df["promotion_ids"].notna()
    else:
        df["has_promotion"] = False


def _add_revenue_features(df: pd.DataFrame) -> None:
    if "amount" in df.columns:
        amount = pd.to_numeric(df["amount"], errors="coerce")
        df["revenue"] = amount
    else:
        amount = pd.Series(np.nan, index=df.index)
        df["revenue"] = np.nan

    if "qty" in df.columns:
        qty = pd.to_numeric(df["qty"], errors="coerce")
    else:
        qty = pd.Series(np.nan, index=df.index)

    df["amount_per_item"] = np.where(qty > 0, amount / qty, np.nan)
