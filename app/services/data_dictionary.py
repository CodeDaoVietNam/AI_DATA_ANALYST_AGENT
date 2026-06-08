from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


ALLOWED_DOMAINS = {
    "ecommerce",
    "retail",
    "marketing",
    "hr",
    "finance",
    "logistics",
    "education",
    "survey",
    "product",
    "generic",
}

ALLOWED_DATA_TYPES = {"string", "number", "date", "boolean", "categorical"}
ALLOWED_AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median"}
ALLOWED_SEMANTIC_ROLES = {
    "revenue",
    "cost",
    "profit",
    "margin",
    "discount",
    "date",
    "category",
    "segment",
    "quantity",
    "city",
    "state",
    "country",
    "customer",
    "campaign",
    "channel",
    "employee",
    "department",
    "job_role",
    "salary",
    "target",
    "conversion",
    "overtime",
    "tenure",
    "recency",
    "monetary",
    "frequency",
}

FIELD_ALIASES = {
    "column": "column_name",
    "columnname": "column_name",
    "field": "column_name",
    "field_name": "column_name",
    "fieldname": "column_name",
    "business": "business_name",
    "businessname": "business_name",
    "name": "business_name",
    "role": "semantic_role",
    "semantic": "semantic_role",
    "semanticrole": "semantic_role",
    "type": "data_type",
    "datatype": "data_type",
    "agg": "aggregation",
    "is_sensitive": "sensitive",
    "allowed": "allowed_values",
    "values": "allowed_values",
}

FIELD_KEYS = {
    "column_name",
    "business_name",
    "description",
    "semantic_role",
    "data_type",
    "unit",
    "aggregation",
    "sensitive",
    "allowed_values",
}


def parse_data_dictionary_file(content: bytes, filename: str) -> dict[str, Any]:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".json":
        return parse_data_dictionary_json(content)
    if suffix == ".csv":
        return parse_data_dictionary_csv(content)
    raise ValueError("Data dictionary must be a .csv or .json file.")


def parse_data_dictionary_csv(content: bytes) -> dict[str, Any]:
    try:
        df = pd.read_csv(BytesIO(content), dtype=str).fillna("")
    except Exception as exc:
        raise ValueError(f"Cannot parse data dictionary CSV: {exc}") from exc
    domain = _first_domain_value(df)
    rows = []
    for raw in df.to_dict(orient="records"):
        rows.append(_normalize_field(raw))
    return normalize_data_dictionary({"domain": domain, "fields": rows})


def parse_data_dictionary_json(content: bytes) -> dict[str, Any]:
    try:
        raw = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Cannot parse data dictionary JSON: {exc}") from exc
    return normalize_data_dictionary(raw)


def normalize_data_dictionary(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {"domain": None, "fields": []}

    if isinstance(raw, list):
        raw = {"domain": None, "fields": raw}
    fields_raw = raw.get("fields")
    if fields_raw is None:
        fields_raw = raw.get("columns") or raw.get("schema") or []
    if not isinstance(fields_raw, list):
        raise ValueError("Data dictionary `fields` must be a list.")

    domain = _clean_optional_string(raw.get("domain"))
    fields = [_normalize_field(field) for field in fields_raw if isinstance(field, dict)]
    fields = [field for field in fields if field["column_name"]]
    return {"domain": domain, "fields": fields}


def validate_data_dictionary(dictionary: dict[str, Any], columns: list[str]) -> list[str]:
    normalized = normalize_data_dictionary(dictionary)
    warnings = []
    column_set = set(columns)
    seen = set()

    domain = normalized.get("domain")
    if domain and domain not in ALLOWED_DOMAINS:
        warnings.append(f"Unknown domain `{domain}`; it will still be saved as a user hint.")

    missing_columns = []
    duplicate_columns = []
    for field in normalized["fields"]:
        column_name = field["column_name"]
        if column_name not in column_set:
            missing_columns.append(column_name)
        if column_name in seen:
            duplicate_columns.append(column_name)
        seen.add(column_name)

        role = field.get("semantic_role")
        if role and role not in ALLOWED_SEMANTIC_ROLES:
            warnings.append(f"Unknown semantic_role `{role}` for column `{column_name}`.")
        data_type = field.get("data_type")
        if data_type and data_type not in ALLOWED_DATA_TYPES:
            warnings.append(f"Unknown data_type `{data_type}` for column `{column_name}`.")
        aggregation = field.get("aggregation")
        if aggregation and aggregation not in ALLOWED_AGGREGATIONS:
            warnings.append(f"Unknown aggregation `{aggregation}` for column `{column_name}`.")

    if missing_columns:
        raise ValueError(f"Data dictionary references missing columns: {sorted(set(missing_columns))}")
    if duplicate_columns:
        raise ValueError(f"Data dictionary contains duplicate columns: {sorted(set(duplicate_columns))}")
    return warnings


def dictionary_to_semantic_overrides(dictionary: dict[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_data_dictionary(dictionary)
    roles: dict[str, str] = {}
    for field in normalized["fields"]:
        role = field.get("semantic_role")
        column_name = field.get("column_name")
        if role and column_name:
            roles[role] = column_name
    return {"domain": normalized.get("domain"), "roles": roles}


def _normalize_field(raw: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for key, value in raw.items():
        canonical = _canonical_key(str(key))
        if canonical in FIELD_KEYS:
            mapped[canonical] = value

    return {
        "column_name": _clean_optional_string(mapped.get("column_name")) or "",
        "business_name": _clean_optional_string(mapped.get("business_name")),
        "description": _clean_optional_string(mapped.get("description")),
        "semantic_role": _clean_optional_string(mapped.get("semantic_role"), lower=True),
        "data_type": _clean_optional_string(mapped.get("data_type"), lower=True),
        "unit": _clean_optional_string(mapped.get("unit")),
        "aggregation": _clean_optional_string(mapped.get("aggregation"), lower=True),
        "sensitive": _parse_bool(mapped.get("sensitive")),
        "allowed_values": _parse_allowed_values(mapped.get("allowed_values")),
    }


def _canonical_key(key: str) -> str:
    normalized = key.strip().lower().replace(" ", "_").replace("-", "_")
    compact = normalized.replace("_", "")
    return FIELD_ALIASES.get(normalized) or FIELD_ALIASES.get(compact) or normalized


def _first_domain_value(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if _canonical_key(str(column)) != "domain":
            continue
        for value in df[column].tolist():
            text = _clean_optional_string(value, lower=True)
            if text:
                return text
    return None


def _clean_optional_string(value: Any, *, lower: bool = False) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.lower() if lower else text


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "sensitive"}


def _parse_allowed_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    separator = "|" if "|" in text else ","
    return [item.strip() for item in text.split(separator) if item.strip()]
