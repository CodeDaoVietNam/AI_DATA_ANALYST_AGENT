from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.services.expression_engine import UnsafeExpressionError, evaluate_expression, validate_expression


ALLOWED_METRIC_FORMATS = {"number", "percent", "currency", "integer"}
ALLOWED_METRIC_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}
METRIC_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def normalize_metric_definition(definition: dict[str, Any]) -> dict[str, Any]:
    name = str(definition.get("name") or "").strip()
    label = str(definition.get("label") or name.replace("_", " ").title()).strip()
    required_roles = definition.get("required_roles") or []
    if isinstance(required_roles, str):
        required_roles = [role.strip() for role in required_roles.split(",") if role.strip()]
    return {
        "name": name,
        "label": label or name,
        "description": _clean_string(definition.get("description")),
        "expression": str(definition.get("expression") or "").strip(),
        "format": str(definition.get("format") or "number").strip().lower(),
        "aggregation": str(definition.get("aggregation") or "mean").strip().lower(),
        "required_roles": list(required_roles),
        "higher_is_better": bool(definition.get("higher_is_better", True)),
    }


def validate_metric_definition(definition: dict[str, Any], df: pd.DataFrame, profile) -> list[str]:
    metric = normalize_metric_definition(definition)
    warnings: list[str] = []
    if not METRIC_NAME_PATTERN.match(metric["name"]):
        raise ValueError("Metric name must start with a letter and contain only letters, numbers, and underscores.")
    if metric["format"] not in ALLOWED_METRIC_FORMATS:
        raise ValueError(f"Unsupported metric format: {metric['format']}.")
    if metric["aggregation"] not in ALLOWED_METRIC_AGGREGATIONS:
        raise ValueError(f"Unsupported metric aggregation: {metric['aggregation']}.")
    for role in metric["required_roles"]:
        if role not in getattr(profile, "roles", {}):
            raise ValueError(f"Required semantic role is missing: {role}")

    variables = _build_variable_context(df, profile)
    try:
        used_names = validate_expression(metric["expression"], variables)
    except UnsafeExpressionError as exc:
        raise ValueError(str(exc)) from exc
    if not used_names:
        warnings.append("Metric expression does not reference any dataset column or semantic role.")
    return warnings


def evaluate_metric(df: pd.DataFrame, profile, definition: dict[str, Any]) -> pd.Series | float | int:
    metric = normalize_metric_definition(definition)
    validate_metric_definition(metric, df, profile)
    variables = _build_variable_context(df, profile)
    result = evaluate_expression(metric["expression"], variables)
    if isinstance(result, pd.Series):
        return result.replace([np.inf, -np.inf], np.nan)
    if isinstance(result, (int, float)) and not np.isfinite(result):
        return np.nan
    return result


def evaluate_metric_summary(df: pd.DataFrame, profile, definition: dict[str, Any]) -> dict[str, Any]:
    metric = normalize_metric_definition(definition)
    result = evaluate_metric(df, profile, metric)
    if isinstance(result, pd.Series):
        value = _aggregate_series(result, metric["aggregation"])
        valid_count = int(result.count())
        missing_count = int(result.isna().sum())
        sample_values = [_json_safe(value) for value in result.head(10).tolist()]
        result_type = "series"
    else:
        value = result
        valid_count = 1 if pd.notna(result) else 0
        missing_count = 0 if pd.notna(result) else 1
        sample_values = [_json_safe(result)]
        result_type = "scalar"

    return {
        "name": metric["name"],
        "label": metric["label"],
        "description": metric["description"],
        "expression": metric["expression"],
        "format": metric["format"],
        "aggregation": metric["aggregation"],
        "value": _json_safe(value),
        "valid_count": valid_count,
        "missing_count": missing_count,
        "sample_values": sample_values,
        "result_type": result_type,
    }


def metric_breakdown(
    df: pd.DataFrame,
    profile,
    definition: dict[str, Any],
    *,
    by_role: str | None = None,
    by_column: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    metric = normalize_metric_definition(definition)
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500.")
    group_column = by_column or _role_column(profile, by_role or "")
    if not group_column:
        raise ValueError("A valid by_role or by_column is required.")
    if group_column not in df.columns:
        raise ValueError(f"Group column does not exist: {group_column}")

    result = evaluate_metric(df, profile, metric)
    temp = df[[group_column]].copy()
    temp[metric["name"]] = result if isinstance(result, pd.Series) else result
    grouped = (
        temp.groupby(group_column, dropna=False)[metric["name"]]
        .agg(metric["aggregation"])
        .reset_index(name=metric["name"])
        .sort_values(metric["name"], ascending=not metric.get("higher_is_better", True))
        .head(limit)
    )
    return _records(grouped)


def find_metric(metrics: list[dict[str, Any]], metric_name: str) -> dict[str, Any]:
    normalized = metric_name.strip().lower()
    for metric in metrics:
        candidate = normalize_metric_definition(metric)
        if candidate["name"].lower() == normalized or candidate["label"].lower() == normalized:
            return candidate
    raise ValueError(f"Custom metric not found: {metric_name}")


def _build_variable_context(df: pd.DataFrame, profile) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            variables[column] = df[column]
            alias = _sanitize_identifier(column)
            variables.setdefault(alias, df[column])
    for role, match in getattr(profile, "roles", {}).items():
        column = getattr(match, "column", None)
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            variables[role] = df[column]
    return variables


def _role_column(profile, role: str) -> str | None:
    if not role:
        return None
    match = getattr(profile, "roles", {}).get(role)
    return getattr(match, "column", None) if match else None


def _aggregate_series(series: pd.Series, aggregation: str) -> float | int:
    clean = pd.to_numeric(series, errors="coerce")
    if aggregation == "sum":
        return float(clean.sum(skipna=True))
    if aggregation == "mean":
        return float(clean.mean(skipna=True))
    if aggregation == "median":
        return float(clean.median(skipna=True))
    if aggregation == "min":
        return float(clean.min(skipna=True))
    if aggregation == "max":
        return float(clean.max(skipna=True))
    if aggregation == "count":
        return int(clean.count())
    raise ValueError(f"Unsupported metric aggregation: {aggregation}")


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in df.replace({np.nan: None}).to_dict(orient="records")
    ]


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if pd.isna(value):
        return None
    return value


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        return "column"
    if sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"
    return sanitized


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
