from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def retail_margin_summary(df: pd.DataFrame, profile) -> dict[str, Any]:
    revenue = _role_column(profile, "revenue")
    profit = _role_column(profile, "profit")
    if not revenue or not profit:
        return {"warning": "Retail margin needs revenue and profit roles.", "items": []}
    total_revenue = _sum(df, revenue)
    total_profit = _sum(df, profit)
    return {
        "revenue_column": revenue,
        "profit_column": profit,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "margin": _safe_div(total_profit, total_revenue),
        "loss_rows": int((pd.to_numeric(df[profit], errors="coerce") < 0).sum()),
    }


def retail_loss_analysis(df: pd.DataFrame, profile, by_role: str = "category", limit: int = 20) -> list[dict[str, Any]]:
    revenue = _role_column(profile, "revenue")
    profit = _role_column(profile, "profit")
    group = _role_column(profile, by_role)
    if not revenue or not profit or not group:
        return []
    temp = _numeric_frame(df, [revenue, profit], [group])
    grouped = (
        temp.groupby(group, dropna=False)
        .agg(revenue=(revenue, "sum"), profit=(profit, "sum"), rows=(profit, "count"))
        .reset_index()
    )
    grouped["margin"] = grouped.apply(lambda row: _safe_div(row["profit"], row["revenue"]), axis=1)
    result = grouped[grouped["profit"] < 0].sort_values("profit").head(limit)
    return _records(result)


def retail_discount_effect(df: pd.DataFrame, profile, limit: int = 20) -> dict[str, Any]:
    discount = _role_column(profile, "discount")
    revenue = _role_column(profile, "revenue")
    profit = _role_column(profile, "profit")
    if not discount or not revenue:
        return {"warning": "No discount role detected.", "items": []}
    temp = _numeric_frame(df, [discount, revenue] + ([profit] if profit else []), [])
    temp["discount_band"] = pd.cut(
        temp[discount].fillna(0),
        bins=[-np.inf, 0, 0.1, 0.2, 0.4, np.inf],
        labels=["0", "0-10%", "10-20%", "20-40%", "40%+"],
    )
    aggregations: dict[str, tuple[str, str]] = {
        "rows": (discount, "count"),
        "avg_discount": (discount, "mean"),
        "revenue": (revenue, "sum"),
    }
    if profit:
        aggregations["profit"] = (profit, "sum")
    grouped = temp.groupby("discount_band", dropna=False, observed=False).agg(**aggregations).reset_index()
    if profit:
        grouped["margin"] = grouped.apply(lambda row: _safe_div(row["profit"], row["revenue"]), axis=1)
    return {"items": _records(grouped.head(limit))}


def retail_interaction(df: pd.DataFrame, profile, limit: int = 30) -> list[dict[str, Any]]:
    revenue = _role_column(profile, "revenue")
    profit = _role_column(profile, "profit")
    groups = [_role_column(profile, role) for role in ["segment", "state", "category"]]
    groups = list(dict.fromkeys(group for group in groups if group))
    if not revenue or len(groups) < 2:
        return []
    temp = _numeric_frame(df, [revenue] + ([profit] if profit else []), groups)
    aggregations: dict[str, tuple[str, str]] = {"revenue": (revenue, "sum"), "rows": (revenue, "count")}
    if profit:
        aggregations["profit"] = (profit, "sum")
    grouped = temp.groupby(groups, dropna=False).agg(**aggregations).reset_index().sort_values("revenue", ascending=False)
    if profit:
        grouped["margin"] = grouped.apply(lambda row: _safe_div(row["profit"], row["revenue"]), axis=1)
    return _records(grouped.head(limit))


def retail_top_opportunities(df: pd.DataFrame, profile, by_role: str = "category", limit: int = 20) -> list[dict[str, Any]]:
    revenue = _role_column(profile, "revenue")
    profit = _role_column(profile, "profit")
    group = _role_column(profile, by_role)
    if not revenue or not profit or not group:
        return []
    temp = _numeric_frame(df, [revenue, profit], [group])
    grouped = temp.groupby(group, dropna=False).agg(revenue=(revenue, "sum"), profit=(profit, "sum"), rows=(group, "count")).reset_index()
    grouped["margin"] = grouped.apply(lambda row: _safe_div(row["profit"], row["revenue"]), axis=1)
    revenue_cutoff = grouped["revenue"].quantile(0.6)
    result = grouped[grouped["revenue"] >= revenue_cutoff].sort_values(["margin", "revenue"], ascending=[True, False])
    return _records(result.head(limit))


def marketing_response_by_segment(df: pd.DataFrame, profile, by_role: str = "country", limit: int = 20) -> dict[str, Any]:
    target = _target_column(profile)
    group = _role_column(profile, by_role)
    if not target or not group:
        return {"warning": "Marketing response summary needs target/conversion and group roles.", "items": []}
    return {"target_column": target, "items": _target_group(df, target, group, limit)}


def marketing_campaign_acceptance(df: pd.DataFrame, profile) -> list[dict[str, Any]]:
    campaign_columns = [column for column in df.columns if _normalize(column).startswith("acceptedcmp")]
    if not campaign_columns:
        campaign = _role_column(profile, "campaign")
        target = _target_column(profile)
        if campaign and target:
            return _target_group(df, target, campaign, 20)
        return []
    rows = []
    for column in campaign_columns:
        positive = df[column].map(_is_positive)
        rows.append({"campaign": column, "acceptance_rate": float(positive.mean()), "accepted": int(positive.sum()), "rows": int(len(df))})
    return sorted(rows, key=lambda item: item["acceptance_rate"], reverse=True)


def marketing_rfm_summary(df: pd.DataFrame, profile) -> dict[str, Any]:
    recency_col = _role_column(profile, "recency")
    monetary_cols = [column for column in df.columns if _normalize(column).startswith("mnt")]
    frequency_cols = [column for column in df.columns if _normalize(column).startswith("num") and "purchase" in _normalize(column)]
    result: dict[str, Any] = {
        "recency_column": recency_col,
        "monetary_columns": monetary_cols,
        "frequency_columns": frequency_cols,
        "items": [],
    }
    if not monetary_cols and not frequency_cols and not recency_col:
        result["warning"] = "No RFM-like columns detected."
        return result
    temp = pd.DataFrame(index=df.index)
    if recency_col:
        temp["recency"] = pd.to_numeric(df[recency_col], errors="coerce")
    if monetary_cols:
        temp["monetary"] = df[monetary_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    if frequency_cols:
        temp["frequency"] = df[frequency_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    result["summary"] = {
        column: {
            "mean": None if pd.isna(temp[column].mean()) else float(temp[column].mean()),
            "median": None if pd.isna(temp[column].median()) else float(temp[column].median()),
        }
        for column in temp.columns
    }
    if {"monetary", "frequency"} <= set(temp.columns):
        temp["rfm_segment"] = pd.qcut(temp["monetary"].rank(method="first"), q=min(4, max(1, temp["monetary"].nunique())), duplicates="drop")
        grouped = temp.groupby("rfm_segment", dropna=False, observed=False).agg(
            customers=("monetary", "count"),
            monetary=("monetary", "mean"),
            frequency=("frequency", "mean"),
        ).reset_index()
        result["items"] = _records(grouped)
    return result


def marketing_income_band_response(df: pd.DataFrame, profile) -> dict[str, Any]:
    income = _role_column(profile, "salary")
    target = _target_column(profile)
    if not income or not target:
        return {"warning": "Income band response needs income and target roles.", "items": []}
    temp = df[[income, target]].copy()
    temp[income] = pd.to_numeric(temp[income], errors="coerce")
    temp["income_band"] = pd.qcut(temp[income].rank(method="first"), q=min(5, max(1, temp[income].nunique())), duplicates="drop")
    temp["_positive"] = temp[target].map(_is_positive)
    grouped = temp.groupby("income_band", dropna=False, observed=False).agg(rows=(target, "count"), positive_rate=("_positive", "mean"), avg_income=(income, "mean")).reset_index()
    return {"items": _records(grouped)}


def marketing_purchase_channel_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    channels = {
        "web": "numwebpurchases",
        "catalog": "numcatalogpurchases",
        "store": "numstorepurchases",
        "deals": "numdealspurchases",
    }
    rows = []
    normalized = {_normalize(column): column for column in df.columns}
    for channel, normalized_col in channels.items():
        column = normalized.get(normalized_col)
        if column:
            values = pd.to_numeric(df[column], errors="coerce")
            rows.append({"channel": channel, "total_purchases": float(values.sum(skipna=True)), "avg_purchases": float(values.mean(skipna=True))})
    return sorted(rows, key=lambda item: item["total_purchases"], reverse=True)


def hr_attrition_by_role(df: pd.DataFrame, profile, by_role: str, min_rows: int = 1, limit: int = 20) -> dict[str, Any]:
    target = _target_column(profile)
    group = _role_column(profile, by_role)
    if not target or not group:
        return {"warning": f"HR attrition summary needs target and {by_role} roles.", "items": []}
    rows = [row for row in _target_group(df, target, group, limit=500) if row["rows"] >= min_rows]
    rows = sorted(rows, key=lambda item: item["positive_rate"], reverse=True)[:limit]
    return {"target_column": target, "group_column": group, "items": rows}


def hr_income_band_attrition(df: pd.DataFrame, profile) -> dict[str, Any]:
    income = _role_column(profile, "salary")
    target = _target_column(profile)
    if not income or not target:
        return {"warning": "Income band attrition needs salary and target roles.", "items": []}
    temp = df[[income, target]].copy()
    temp[income] = pd.to_numeric(temp[income], errors="coerce")
    temp["income_band"] = pd.qcut(temp[income].rank(method="first"), q=min(5, max(1, temp[income].nunique())), duplicates="drop")
    temp["_positive"] = temp[target].map(_is_positive)
    grouped = temp.groupby("income_band", dropna=False, observed=False).agg(rows=(target, "count"), attrition_rate=("_positive", "mean"), avg_income=(income, "mean")).reset_index()
    return {"items": _records(grouped)}


def hr_tenure_risk(df: pd.DataFrame, profile) -> dict[str, Any]:
    tenure = _role_column(profile, "tenure")
    target = _target_column(profile)
    if not tenure or not target:
        return {"warning": "Tenure risk needs tenure and target roles.", "items": []}
    temp = df[[tenure, target]].copy()
    temp[tenure] = pd.to_numeric(temp[tenure], errors="coerce")
    temp["tenure_band"] = pd.cut(temp[tenure], bins=[-np.inf, 1, 3, 5, 10, np.inf], labels=["<=1", "1-3", "3-5", "5-10", "10+"])
    temp["_positive"] = temp[target].map(_is_positive)
    grouped = temp.groupby("tenure_band", dropna=False, observed=False).agg(rows=(target, "count"), attrition_rate=("_positive", "mean"), avg_tenure=(tenure, "mean")).reset_index()
    return {"items": _records(grouped)}


def hr_high_risk_segments(df: pd.DataFrame, profile, min_rows: int = 10, limit: int = 20) -> list[dict[str, Any]]:
    target = _target_column(profile)
    groups = [_role_column(profile, role) for role in ["department", "job_role", "overtime"]]
    groups = [group for group in groups if group]
    if not target or len(groups) < 2:
        return []
    temp = df[[*groups, target]].copy()
    temp["_positive"] = temp[target].map(_is_positive)
    grouped = temp.groupby(groups, dropna=False).agg(rows=(target, "count"), attrition_rate=("_positive", "mean")).reset_index()
    grouped = grouped[grouped["rows"] >= min_rows].sort_values(["attrition_rate", "rows"], ascending=[False, False]).head(limit)
    return _records(grouped)


def generic_numeric_distributions(df: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    rows = []
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            series = pd.to_numeric(df[column], errors="coerce")
            rows.append({
                "column": column,
                "mean": _clean_float(series.mean()),
                "median": _clean_float(series.median()),
                "min": _clean_float(series.min()),
                "max": _clean_float(series.max()),
                "missing": int(series.isna().sum()),
            })
    return rows[:limit]


def generic_top_categorical_values(df: pd.DataFrame, limit: int = 5, values_per_column: int = 10) -> list[dict[str, Any]]:
    rows = []
    for column in df.columns:
        if pd.api.types.is_object_dtype(df[column]) or isinstance(df[column].dtype, pd.CategoricalDtype):
            unique = df[column].nunique(dropna=True)
            if 1 < unique <= max(50, len(df) * 0.5):
                values = df[column].value_counts(dropna=False).head(values_per_column).reset_index()
                values.columns = ["value", "count"]
                rows.append({"column": column, "unique": int(unique), "top_values": _records(values)})
    return rows[:limit]


def _target_group(df: pd.DataFrame, target: str, group: str, limit: int = 20) -> list[dict[str, Any]]:
    temp = df[[group, target]].copy()
    temp["_positive"] = temp[target].map(_is_positive)
    grouped = (
        temp.groupby(group, dropna=False)
        .agg(rows=(target, "count"), positive_rate=("_positive", "mean"), positives=("_positive", "sum"))
        .reset_index()
        .sort_values(["positive_rate", "rows"], ascending=[False, False])
        .head(limit)
    )
    return _records(grouped)


def _numeric_frame(df: pd.DataFrame, numeric_columns: list[str], group_columns: list[str]) -> pd.DataFrame:
    temp = df[[*group_columns, *numeric_columns]].copy()
    for column in numeric_columns:
        temp[column] = pd.to_numeric(temp[column], errors="coerce")
    return temp


def _role_column(profile, role: str) -> str | None:
    match = profile.roles.get(role)
    return match.column if match else None


def _target_column(profile) -> str | None:
    return _role_column(profile, "target") or _role_column(profile, "conversion")


def _sum(df: pd.DataFrame, column: str) -> float:
    return float(pd.to_numeric(df[column], errors="coerce").sum(skipna=True))


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    if denominator in (0, None) or pd.isna(denominator):
        return None
    return None if pd.isna(numerator) else float(numerator) / float(denominator)


def _is_positive(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"yes", "true", "1", "y", "accepted", "converted"}


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.astype(object).where(pd.notna(df), None)
    return [
        {key: _json_safe_value(value) for key, value in row.items()}
        for row in clean.to_dict(orient="records")
    ]


def _clean_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    return str(value)


def _normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")
