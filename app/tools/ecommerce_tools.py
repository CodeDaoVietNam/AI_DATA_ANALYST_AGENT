from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def get_sales_overview(df: pd.DataFrame) -> dict[str, Any]:
    require_columns(df, ["order_id", "date", "revenue", "qty", "is_cancelled", "amount"])

    date_min = df["date"].min()
    date_max = df["date"].max()
    missing_amount_rows = int(df["amount"].isna().sum())
    rows = int(len(df))

    notes = [
        "Revenue is calculated from available amount values.",
        "Rows with missing amount are excluded from revenue sums.",
    ]

    if missing_amount_rows:
        notes.append(f"{missing_amount_rows} rows have missing amount.")

    return {
        "rows": rows,
        "columns": int(df.shape[1]),
        "unique_orders": int(df["order_id"].nunique(dropna=True)),
        "date_min": _date_to_string(date_min),
        "date_max": _date_to_string(date_max),
        "total_revenue": float(df["revenue"].sum(skipna=True)),
        "total_qty": int(df["qty"].sum(skipna=True)),
        "cancel_rate": _safe_mean(df["is_cancelled"]),
        "missing_amount_rows": missing_amount_rows,
        "missing_amount_percent": _safe_percent(missing_amount_rows, rows),
        "notes": notes,
    }


def get_data_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    missing_values = df.isna().sum().astype(int).to_dict()
    missing_percent = (df.isna().mean() * 100).round(2).to_dict()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_order_id_rows = int(df["order_id"].duplicated().sum()) if "order_id" in df.columns else 0

    warnings = []
    amount_missing = missing_values.get("amount", 0)
    if amount_missing:
        warnings.append(f"{amount_missing} rows have missing amount; revenue is calculated from available values.")

    shipping_missing = {
        column: missing_values.get(column, 0)
        for column in ["ship_city", "ship_state", "ship_country"]
        if missing_values.get(column, 0)
    }
    if shipping_missing:
        warnings.append(f"Shipping fields have missing values: {shipping_missing}.")

    if duplicate_rows:
        warnings.append(f"{duplicate_rows} duplicate rows were found after cleaning.")

    if duplicate_order_id_rows:
        warnings.append(
            f"{duplicate_order_id_rows} repeated order_id rows were found; this is likely because the dataset is line-item level."
        )

    return {
        "duplicate_rows": duplicate_rows,
        "duplicate_order_id_rows": duplicate_order_id_rows,
        "missing_values": {key: int(value) for key, value in missing_values.items()},
        "missing_percent": {key: float(value) for key, value in missing_percent.items()},
        "warnings": warnings,
    }


def revenue_by_month(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["order_month", "revenue", "order_id", "qty", "is_cancelled"])

    result = (
        df.groupby("order_month", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            qty=("qty", "sum"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("order_month")
    )

    result["revenue"] = result["revenue"].astype(float)
    result["orders"] = result["orders"].astype(int)
    result["qty"] = result["qty"].astype(int)
    result["cancel_rate"] = result["cancel_rate"].astype(float)
    return records(result)


def revenue_by_category(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["category", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby("category", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
            avg_amount=("revenue", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    total_revenue = result["revenue"].sum(skipna=True)
    if total_revenue:
        result["revenue_share"] = (result["revenue"] / total_revenue * 100).round(2)
    else:
        result["revenue_share"] = 0.0

    result = result[
        ["category", "revenue", "revenue_share", "qty", "orders", "cancel_rate", "avg_amount"]
    ]
    result["revenue"] = result["revenue"].astype(float)
    result["qty"] = result["qty"].astype(int)
    result["orders"] = result["orders"].astype(int)
    result["cancel_rate"] = result["cancel_rate"].astype(float)
    return records(result)


def top_states_by_revenue(df: pd.DataFrame, n: int = 10) -> list[dict[str, Any]]:
    _validate_limit(n)

    require_columns(df, ["ship_state", "revenue", "order_id", "qty", "is_cancelled"])

    result = (
        df.groupby("ship_state", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            qty=("qty", "sum"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(n)
    )

    result["revenue"] = result["revenue"].astype(float)
    result["orders"] = result["orders"].astype(int)
    result["qty"] = result["qty"].astype(int)
    result["cancel_rate"] = result["cancel_rate"].astype(float)
    return records(result)


def top_skus_by_revenue(df: pd.DataFrame, n: int = 20) -> list[dict[str, Any]]:
    _validate_limit(n)
    require_columns(df, ["sku", "category", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby(["sku", "category"], dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
            avg_amount=("revenue", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(n)
    )
    return _typed_records(result)


def revenue_by_size(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["size", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby("size", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
            avg_amount=("revenue", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return _typed_records(result)


def category_cancellation_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["category", "order_id", "is_cancelled", "revenue"])

    result = (
        df.groupby("category", dropna=False)
        .agg(
            rows=("order_id", "count"),
            orders=("order_id", "nunique"),
            cancelled_rows=("is_cancelled", "sum"),
            cancel_rate=("is_cancelled", "mean"),
            revenue=("revenue", "sum"),
        )
        .reset_index()
        .sort_values("cancel_rate", ascending=False)
    )
    return _typed_records(result)


def fulfilment_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["fulfilment", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby("fulfilment", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
            avg_amount=("revenue", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return _typed_records(result)


def courier_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    require_columns(df, ["courier_status", "revenue", "qty", "order_id"])

    result = (
        df.groupby("courier_status", dropna=False)
        .agg(
            rows=("order_id", "count"),
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    return _typed_records(result)


def promotion_summary(df: pd.DataFrame) -> dict[str, Any]:
    require_columns(df, ["has_promotion", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby("has_promotion", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            avg_amount=("revenue", "mean"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return {
        "items": _typed_records(result),
        "warning": "Promotion comparison is associative, not causal. Missing promotion_ids may overlap with cancellation behavior.",
    }


def b2b_summary(df: pd.DataFrame) -> dict[str, Any]:
    require_columns(df, ["b2b", "revenue", "qty", "order_id", "is_cancelled"])

    result = (
        df.groupby("b2b", dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            qty=("qty", "sum"),
            orders=("order_id", "nunique"),
            avg_amount=("revenue", "mean"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    items = _typed_records(result)
    total_orders = sum(int(item.get("orders") or 0) for item in items)
    b2b_orders = sum(int(item.get("orders") or 0) for item in items if item.get("b2b") is True)
    warning = None
    if total_orders and b2b_orders / total_orders < 0.05:
        warning = "B2B sample is small compared with non-B2B, so interpret differences cautiously."

    return {
        "items": items,
        "warning": warning,
    }


def top_cities_by_revenue(df: pd.DataFrame, n: int = 20) -> list[dict[str, Any]]:
    _validate_limit(n)
    require_columns(df, ["ship_city", "ship_state", "revenue", "order_id", "qty", "is_cancelled"])

    result = (
        df.groupby(["ship_city", "ship_state"], dropna=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            qty=("qty", "sum"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(n)
    )
    return _typed_records(result)


def state_cancellation_summary(df: pd.DataFrame, min_orders: int = 1000, n: int = 20) -> list[dict[str, Any]]:
    _validate_limit(n)
    if min_orders < 0:
        raise ValueError("min_orders must be non-negative.")
    require_columns(df, ["ship_state", "order_id", "revenue", "is_cancelled"])

    result = (
        df.groupby("ship_state", dropna=False)
        .agg(
            orders=("order_id", "nunique"),
            revenue=("revenue", "sum"),
            cancel_rate=("is_cancelled", "mean"),
            cancelled_rows=("is_cancelled", "sum"),
        )
        .reset_index()
    )
    result = (
        result[result["orders"] >= min_orders]
        .sort_values("cancel_rate", ascending=False)
        .head(n)
    )
    return _typed_records(result)


def cancellation_summary(df: pd.DataFrame) -> dict[str, Any]:
    require_columns(df, ["order_id", "is_cancelled", "category", "fulfilment"])

    cancelled = df[df["is_cancelled"]]

    by_category = (
        df.groupby("category", dropna=False)
        .agg(
            rows=("order_id", "count"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("cancel_rate", ascending=False)
    )

    by_fulfilment = (
        df.groupby("fulfilment", dropna=False)
        .agg(
            rows=("order_id", "count"),
            orders=("order_id", "nunique"),
            cancel_rate=("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values("cancel_rate", ascending=False)
    )

    return {
        "overall_cancel_rate": _safe_mean(df["is_cancelled"]),
        "cancelled_rows": int(cancelled.shape[0]),
        "cancelled_orders": int(cancelled["order_id"].nunique(dropna=True)),
        "by_category": records(by_category),
        "by_fulfilment": records(by_fulfilment),
    }


def _date_to_string(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def _safe_mean(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    value = series.mean()
    if pd.isna(value):
        return 0.0
    return float(value)


def _safe_percent(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _validate_limit(n: int) -> None:
    if n < 1 or n > 100:
        raise ValueError("n must be between 1 and 100.")


def _typed_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    for column in df.columns:
        if column in {"revenue", "cancel_rate", "avg_amount"}:
            df[column] = df[column].astype(float)
        elif column in {"qty", "orders", "rows", "cancelled_rows"}:
            df[column] = df[column].astype(int)
    return records(df)
