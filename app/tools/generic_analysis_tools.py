from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}


def get_dataset_overview(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "numeric_columns": [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])],
        "datetime_columns": [column for column in df.columns if pd.api.types.is_datetime64_any_dtype(df[column])],
        "duplicate_rows": int(df.duplicated().sum()),
    }


def get_missing_values(df: pd.DataFrame) -> dict[str, Any]:
    missing_values = df.isna().sum().astype(int)
    missing_percent = (df.isna().mean() * 100).round(2)
    return {
        "missing_values": missing_values.to_dict(),
        "missing_percent": missing_percent.to_dict(),
        "columns_with_missing": [
            column for column, value in missing_values.items() if int(value) > 0
        ],
    }


def get_duplicate_rows(df: pd.DataFrame) -> dict[str, Any]:
    duplicate_count = int(df.duplicated().sum())
    return {
        "duplicate_rows": duplicate_count,
        "duplicate_percent": round(duplicate_count / max(len(df), 1) * 100, 2),
    }


def groupby_aggregate(
    df: pd.DataFrame,
    group_by: str,
    metric: str,
    aggregation: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    _require_columns(df, [group_by, metric])
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}.")
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500.")

    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric]):
        raise ValueError(f"Metric column '{metric}' must be numeric for aggregation '{aggregation}'.")

    result = (
        df.groupby(group_by, dropna=False)[metric]
        .agg(aggregation)
        .reset_index(name=f"{aggregation}_{metric}")
        .sort_values(f"{aggregation}_{metric}", ascending=False)
        .head(limit)
    )
    return _records(result)


def correlation_analysis(df: pd.DataFrame, columns: list[str] | None = None) -> dict[str, Any]:
    if columns:
        _require_columns(df, columns)
        numeric_columns = [column for column in columns if pd.api.types.is_numeric_dtype(df[column])]
    else:
        numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]

    if len(numeric_columns) < 2:
        return {
            "columns": numeric_columns,
            "correlations": [],
            "warning": "At least two numeric columns are required for correlation analysis.",
        }

    corr = df[numeric_columns].corr(numeric_only=True).replace({np.nan: None})
    rows = []
    for left in numeric_columns:
        for right in numeric_columns:
            rows.append({
                "column_a": left,
                "column_b": right,
                "correlation": None if pd.isna(corr.loc[left, right]) else float(corr.loc[left, right]),
            })

    return {
        "columns": numeric_columns,
        "correlations": rows,
    }


def semantic_overview(df: pd.DataFrame, profile) -> dict[str, Any]:
    return {
        "domain": profile.domain,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "roles": {role: match.column for role, match in profile.roles.items()},
        "warnings": list(profile.warnings),
    }


def semantic_kpis(df: pd.DataFrame, profile) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "warnings": [],
    }
    for role in ["revenue", "profit", "cost", "quantity", "salary"]:
        column = _role_column(profile, role)
        if column and pd.api.types.is_numeric_dtype(df[column]):
            result[role] = float(df[column].sum(skipna=True))

    target = _role_column(profile, "target") or _role_column(profile, "conversion")
    if target:
        result["target_rate"] = _positive_rate(df[target])

    if "revenue" not in result and profile.domain in {"retail", "ecommerce", "finance"}:
        result["warnings"].append("Revenue role is missing or non-numeric.")
    return result


def semantic_time_series(df: pd.DataFrame, profile, metric_role: str | None = None) -> list[dict[str, Any]]:
    date_col = _role_column(profile, "date")
    requested_metric_col = _role_column(profile, metric_role) if metric_role else None
    metric_col = requested_metric_col if requested_metric_col and pd.api.types.is_numeric_dtype(df[requested_metric_col]) else None
    metric_col = metric_col or _role_column(profile, "revenue") or _role_column(profile, "profit") or _role_column(profile, "quantity")
    if not date_col or not metric_col:
        return []
    if not pd.api.types.is_numeric_dtype(df[metric_col]):
        return []

    temp = df[[date_col, metric_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])
    if temp.empty:
        return []
    result = (
        temp.groupby(temp[date_col].dt.to_period("M").astype(str))[metric_col]
        .sum()
        .reset_index(name=metric_col)
        .rename(columns={date_col: "period"})
        .sort_values("period")
    )
    return _records(result)


def semantic_breakdown(
    df: pd.DataFrame,
    profile,
    by_role: str,
    metric_role: str = "revenue",
    limit: int = 20,
) -> list[dict[str, Any]]:
    by_col = _role_column(profile, by_role)
    metric_col = _role_column(profile, metric_role)
    if not by_col or not metric_col:
        return []
    if not pd.api.types.is_numeric_dtype(df[metric_col]):
        return []

    result = (
        df.groupby(by_col, dropna=False)[metric_col]
        .sum()
        .reset_index(name=metric_col)
        .sort_values(metric_col, ascending=False)
        .head(limit)
    )
    return _records(result)


def semantic_target_summary(df: pd.DataFrame, profile, by_role: str | None = None, limit: int = 20) -> dict[str, Any]:
    target_col = _role_column(profile, "target") or _role_column(profile, "conversion")
    if not target_col:
        return {"target_column": None, "positive_rate": None, "by_group": [], "warning": "No target/conversion column detected."}

    result: dict[str, Any] = {
        "target_column": target_col,
        "positive_rate": _positive_rate(df[target_col]),
        "by_group": [],
    }
    if by_role:
        by_col = _role_column(profile, by_role)
        if by_col:
            # Extract as Series to handle duplicate column names safely
            s_by = df[by_col].iloc[:, 0] if isinstance(df[by_col], pd.DataFrame) else df[by_col]
            s_target = df[target_col].iloc[:, 0] if isinstance(df[target_col], pd.DataFrame) else df[target_col]
            
            temp = pd.DataFrame({
                "by_val": s_by,
                "target_val": s_target
            })
            temp["_target_positive"] = temp["target_val"].map(_is_positive)
            grouped = (
                temp.groupby("by_val", dropna=False)
                .agg(rows=("target_val", "count"), positive_rate=("_target_positive", "mean"))
                .reset_index()
                .rename(columns={"by_val": by_col})
                .sort_values("positive_rate", ascending=False)
                .head(limit)
            )
            result["by_group"] = _records(grouped)
    return result


def compare_segments(
    df: pd.DataFrame,
    segment_column: str,
    segment_a: str,
    segment_b: str,
    metric_column: str,
    aggregation: str = "mean",
) -> dict[str, Any]:
    _require_columns(df, [segment_column, metric_column])
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}.")
    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    val_a = df[df[segment_column] == segment_a][metric_column].agg(aggregation)
    val_b = df[df[segment_column] == segment_b][metric_column].agg(aggregation)

    val_a = float(val_a) if pd.notna(val_a) else 0.0
    val_b = float(val_b) if pd.notna(val_b) else 0.0

    diff = val_a - val_b
    pct_diff = (diff / val_b * 100) if val_b != 0 else 0.0

    return {
        "segment_column": segment_column,
        "segment_a": segment_a,
        "segment_b": segment_b,
        "metric_column": metric_column,
        "aggregation": aggregation,
        "value_a": val_a,
        "value_b": val_b,
        "absolute_difference": diff,
        "percentage_difference": round(pct_diff, 2),
        "conclusion": f"Segment '{segment_a}' is {round(abs(pct_diff), 2)}% {'higher' if diff > 0 else 'lower'} than '{segment_b}'"
    }


def detect_outliers(
    df: pd.DataFrame,
    metric_column: str,
    method: str = "iqr",
) -> dict[str, Any]:
    _require_columns(df, [metric_column])
    if not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    clean_series = df[metric_column].dropna()
    if clean_series.empty:
        return {"metric_column": metric_column, "outliers_count": 0, "outliers_percent": 0.0, "bounds": None, "outlier_sample": []}

    if method == "iqr":
        q1 = clean_series.quantile(0.25)
        q3 = clean_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
    else:  # z-score
        mean = clean_series.mean()
        std = clean_series.std()
        lower_bound = mean - 3 * std
        upper_bound = mean + 3 * std

    outliers = df[(df[metric_column] < lower_bound) | (df[metric_column] > upper_bound)]
    outliers_count = len(outliers)
    outliers_percent = round((outliers_count / len(df)) * 100, 2)

    return {
        "metric_column": metric_column,
        "method": method,
        "outliers_count": outliers_count,
        "outliers_percent": outliers_percent,
        "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)},
        "outlier_sample": _records(outliers.head(10)),
    }


def trend_analysis(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    freq: str = "M",
    aggregation: str = "sum",
) -> dict[str, Any]:
    _require_columns(df, [date_column, metric_column])
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}.")
    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    temp = df[[date_column, metric_column]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column])
    if temp.empty:
        return {"warning": "No valid dates found."}

    grouped = (
        temp.groupby(temp[date_column].dt.to_period(freq).astype(str))[metric_column]
        .agg(aggregation)
        .reset_index(name="metric_value")
        .sort_values(date_column)
    )

    grouped["pct_change"] = grouped["metric_value"].pct_change() * 100
    grouped = grouped.replace({np.nan: None})

    records = _records(grouped)
    avg_growth = grouped["pct_change"].dropna().mean() if not grouped["pct_change"].dropna().empty else 0.0

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "freq": freq,
        "aggregation": aggregation,
        "average_growth_rate": round(float(avg_growth), 2) if pd.notna(avg_growth) else 0.0,
        "trend_records": records,
    }


def period_over_period_change(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    aggregation: str = "sum",
) -> dict[str, Any]:
    _require_columns(df, [date_column, metric_column])
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}.")
    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    temp = df[[date_column, metric_column]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")

    # Filter periods
    p_a_start = pd.to_datetime(period_a_start)
    p_a_end = pd.to_datetime(period_a_end)
    p_b_start = pd.to_datetime(period_b_start)
    p_b_end = pd.to_datetime(period_b_end)

    val_a = temp[(temp[date_column] >= p_a_start) & (temp[date_column] <= p_a_end)][metric_column].agg(aggregation)
    val_b = temp[(temp[date_column] >= p_b_start) & (temp[date_column] <= p_b_end)][metric_column].agg(aggregation)

    val_a = float(val_a) if pd.notna(val_a) else 0.0
    val_b = float(val_b) if pd.notna(val_b) else 0.0

    diff = val_a - val_b
    pct_diff = (diff / val_b * 100) if val_b != 0 else 0.0

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "period_a": {"start": period_a_start, "end": period_a_end, "value": val_a},
        "period_b": {"start": period_b_start, "end": period_b_end, "value": val_b},
        "absolute_difference": diff,
        "percentage_difference": round(pct_diff, 2),
    }


def top_bottom_contributors(
    df: pd.DataFrame,
    group_column: str,
    metric_column: str,
    n: int = 5,
) -> dict[str, Any]:
    _require_columns(df, [group_column, metric_column])
    if not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    grouped = (
        df.groupby(group_column, dropna=False)[metric_column]
        .sum()
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
    )

    total_sum = grouped["total_value"].sum()
    grouped["contribution_percent"] = (grouped["total_value"] / total_sum * 100).round(2) if total_sum != 0 else 0.0

    top = grouped.head(n)
    bottom = grouped.tail(n).iloc[::-1]  # reverse to show smallest first

    return {
        "group_column": group_column,
        "metric_column": metric_column,
        "total_sum": float(total_sum),
        "top_contributors": _records(top),
        "bottom_contributors": _records(bottom),
    }


def pareto_analysis(
    df: pd.DataFrame,
    category_column: str,
    metric_column: str,
) -> dict[str, Any]:
    _require_columns(df, [category_column, metric_column])
    if not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    grouped = (
        df.groupby(category_column, dropna=False)[metric_column]
        .sum()
        .reset_index(name="total_value")
        .sort_values("total_value", ascending=False)
    )

    total_sum = grouped["total_value"].sum()
    if total_sum == 0:
        return {"warning": "Total sum is zero."}

    grouped["cumulative_value"] = grouped["total_value"].cumsum()
    grouped["cumulative_percent"] = (grouped["cumulative_value"] / total_sum * 100).round(2)

    pareto_80 = grouped[grouped["cumulative_percent"] <= 80]
    # If empty (first item is already > 80%), take the first item
    if pareto_80.empty:
        pareto_80 = grouped.head(1)

    contributors_count = len(pareto_80)
    total_categories = len(grouped)
    categories_percent = round((contributors_count / total_categories * 100), 2) if total_categories != 0 else 0.0

    return {
        "category_column": category_column,
        "metric_column": metric_column,
        "total_sum": float(total_sum),
        "contributors_count": contributors_count,
        "total_categories": total_categories,
        "categories_percent": categories_percent,
        "contributors": _records(pareto_80),
        "conclusion": f"{contributors_count} categories out of {total_categories} ({categories_percent}%) contribute to 80% of the total '{metric_column}'."
    }


def cohort_summary(
    df: pd.DataFrame,
    cohort_date_column: str,
    activity_date_column: str,
    user_id_column: str,
) -> list[dict[str, Any]]:
    _require_columns(df, [cohort_date_column, activity_date_column, user_id_column])
    
    temp = df[[cohort_date_column, activity_date_column, user_id_column]].copy()
    temp[cohort_date_column] = pd.to_datetime(temp[cohort_date_column], errors="coerce")
    temp[activity_date_column] = pd.to_datetime(temp[activity_date_column], errors="coerce")
    temp = temp.dropna(subset=[cohort_date_column, activity_date_column])

    if temp.empty:
        return []

    temp["cohort_period"] = temp[cohort_date_column].dt.to_period("M")
    temp["activity_period"] = temp[activity_date_column].dt.to_period("M")

    # Cohort group
    grouped = temp.groupby(["cohort_period", "activity_period"]).agg(users=(user_id_column, "nunique")).reset_index()

    # Cohort lifetime (in months)
    grouped["cohort_lifetime"] = (grouped["activity_period"] - grouped["cohort_period"]).apply(lambda x: x.n)
    
    # Filter only positive lifetimes
    grouped = grouped[grouped["cohort_lifetime"] >= 0]

    # Find size of each cohort
    cohort_sizes = grouped[grouped["cohort_lifetime"] == 0].set_index("cohort_period")["users"].to_dict()

    grouped["cohort_size"] = grouped["cohort_period"].map(cohort_sizes)
    grouped["retention_rate"] = (grouped["users"] / grouped["cohort_size"] * 100).round(2)

    grouped["cohort_period"] = grouped["cohort_period"].astype(str)
    grouped["activity_period"] = grouped["activity_period"].astype(str)

    return _records(grouped.sort_values(["cohort_period", "cohort_lifetime"]))


def anomaly_detection(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    freq: str = "M",
    threshold: float = 1.96,
) -> dict[str, Any]:
    _require_columns(df, [date_column, metric_column])
    if not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    temp = df[[date_column, metric_column]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column])

    if temp.empty:
        return {"warning": "No valid dates."}

    grouped = (
        temp.groupby(temp[date_column].dt.to_period(freq).astype(str))[metric_column]
        .sum()
        .reset_index(name="metric_value")
        .sort_values(date_column)
    )

    if len(grouped) < 3:
        return {"warning": "Not enough data points for anomaly detection (min 3 periods required)."}

    # Rolling Z-score anomaly detection
    mean = grouped["metric_value"].mean()
    std = grouped["metric_value"].std()
    std = std if std != 0 else 1.0

    grouped["z_score"] = (grouped["metric_value"] - mean) / std
    anomalies = grouped[(grouped["z_score"].abs() > threshold)]

    grouped = grouped.replace({np.nan: None})

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "freq": freq,
        "mean": float(mean),
        "std": float(std),
        "anomalies_count": len(anomalies),
        "anomalies": _records(anomalies),
        "all_periods": _records(grouped),
    }


def forecast_next_period(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    periods: int = 3,
) -> dict[str, Any]:
    _require_columns(df, [date_column, metric_column])
    if not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    temp = df[[date_column, metric_column]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column])

    if temp.empty:
        return {"warning": "No valid dates."}

    grouped = (
        temp.groupby(temp[date_column].dt.to_period("M").astype(str))[metric_column]
        .sum()
        .reset_index(name="metric_value")
        .sort_values(date_column)
    )

    if len(grouped) < 3:
        return {"warning": "Not enough historical data points for forecast (min 3 months)."}

    # Baseline Exponential Smoothing (alpha=0.3)
    history = grouped["metric_value"].tolist()
    forecasts = []
    
    # Calculate simple exponentially smoothed value
    level = history[0]
    alpha = 0.3
    for val in history[1:]:
        level = alpha * val + (1 - alpha) * level

    # Naive project linear trend
    if len(history) >= 2:
        trend = (history[-1] - history[0]) / (len(history) - 1)
    else:
        trend = 0.0

    last_period = pd.Period(grouped[date_column].iloc[-1], freq="M")
    
    for i in range(1, periods + 1):
        next_period = str(last_period + i)
        # Combine ESM level with naive trend progression
        pred = max(level + trend * i, 0.0)
        forecasts.append({"period": next_period, "forecast_value": round(float(pred), 2)})

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "historical_periods": _records(grouped),
        "forecasts": forecasts,
    }


def explain_metric_change(
    df: pd.DataFrame,
    date_column: str,
    metric_column: str,
    dimension_column: str,
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    aggregation: str = "sum",
) -> dict[str, Any]:
    _require_columns(df, [date_column, metric_column, dimension_column])
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}.")
    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric_column]):
        raise ValueError(f"Metric column '{metric_column}' must be numeric.")

    temp = df[[date_column, metric_column, dimension_column]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")

    p_a_start = pd.to_datetime(period_a_start)
    p_a_end = pd.to_datetime(period_a_end)
    p_b_start = pd.to_datetime(period_b_start)
    p_b_end = pd.to_datetime(period_b_end)

    df_a = temp[(temp[date_column] >= p_a_start) & (temp[date_column] <= p_a_end)]
    df_b = temp[(temp[date_column] >= p_b_start) & (temp[date_column] <= p_b_end)]

    grouped_a = df_a.groupby(dimension_column, dropna=False)[metric_column].agg(aggregation).to_dict()
    grouped_b = df_b.groupby(dimension_column, dropna=False)[metric_column].agg(aggregation).to_dict()

    all_keys = set(list(grouped_a.keys()) + list(grouped_b.keys()))
    rows = []
    
    total_a = sum(float(v) for v in grouped_a.values() if pd.notna(v))
    total_b = sum(float(v) for v in grouped_b.values() if pd.notna(v))
    total_diff = total_a - total_b

    for key in all_keys:
        val_a = float(grouped_a.get(key, 0.0)) if pd.notna(grouped_a.get(key, 0.0)) else 0.0
        val_b = float(grouped_b.get(key, 0.0)) if pd.notna(grouped_b.get(key, 0.0)) else 0.0
        diff = val_a - val_b
        contribution = (diff / total_diff * 100) if total_diff != 0 else 0.0
        
        rows.append({
            "dimension_value": str(key),
            "value_period_a": val_a,
            "value_period_b": val_b,
            "absolute_change": diff,
            "contribution_to_change_percent": round(contribution, 2),
        })

    # Sort by absolute impact
    rows = sorted(rows, key=lambda x: abs(x["absolute_change"]), reverse=True)

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "dimension_column": dimension_column,
        "period_a_total": total_a,
        "period_b_total": total_b,
        "absolute_change": total_diff,
        "percentage_change": round((total_diff / total_b * 100), 2) if total_b != 0 else 0.0,
        "dimension_contributions": rows,
    }


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def _role_column(profile, role: str) -> str | None:
    match = profile.roles.get(role)
    return match.column if match else None


def _positive_rate(series: pd.Series | pd.DataFrame) -> float:
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    if series.empty:
        return 0.0
    return float(series.map(_is_positive).mean())


def _is_positive(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"yes", "true", "1", "1.0", "y", "accepted", "converted", "satisfied"}
