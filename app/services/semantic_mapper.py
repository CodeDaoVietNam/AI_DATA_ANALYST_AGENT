from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


SEMANTIC_ROLE_KEYWORDS: dict[str, list[str]] = {
    "revenue": ["amount", "sales", "revenue", "total", "price", "gross", "net_sales", "turnover"],
    "cost": ["cost", "expense", "spend", "cogs"],
    "profit": ["profit", "net_profit", "earnings"],
    "margin": ["margin", "profit_margin"],
    "discount": ["discount", "disc", "rebate"],
    "date": ["date", "order_date", "created_at", "invoice_date", "ship_date", "dt_customer", "crash_date"],
    "category": [
        "category",
        "product_category",
        "segment",
        "sub_category",
        "department",
        "job_role",
        "vehicle_type",
        "vehicle_type_code",
        "transit_mode",
        "mode",
        "route",
    ],
    "segment": ["segment", "customer_segment", "market_segment"],
    "quantity": ["qty", "quantity", "units", "unit_count", "volume", "count", "accident_count", "ridership", "trips"],
    "city": ["city", "ship_city", "town", "borough"],
    "state": ["state", "ship_state", "province", "region"],
    "country": ["country", "ship_country", "market"],
    "department": ["department", "division", "team"],
    "job_role": ["jobrole", "job_role", "role", "position"],
    "customer": ["customer", "customer_id", "client", "buyer", "id"],
    "campaign": ["campaign", "acceptedcmp", "promotion", "promo", "channel", "source"],
    "channel": ["channel", "source", "numwebpurchases", "numcatalogpurchases", "numstorepurchases"],
    "employee": ["employee", "employee_id", "employee_number", "employeenumber", "staff", "worker"],
    "salary": ["salary", "monthly_income", "monthlyincome", "income", "pay"],
    "target": ["target", "label", "attrition", "churn", "response", "converted"],
    "conversion": ["response", "converted", "acceptedcmp", "conversion"],
    "overtime": ["overtime", "over_time"],
    "tenure": ["yearsatcompany", "years_at_company", "tenure", "totalworkingyears"],
    "recency": ["recency"],
    "monetary": ["mnt", "monetary", "spend"],
    "frequency": ["num", "frequency", "purchases"],
}

NUMERIC_ROLES = {
    "revenue",
    "cost",
    "profit",
    "margin",
    "discount",
    "quantity",
    "salary",
    "tenure",
    "recency",
    "monetary",
    "frequency",
}

CATEGORICAL_ROLES = {
    "category",
    "segment",
    "city",
    "state",
    "country",
    "department",
    "job_role",
    "campaign",
    "channel",
    "overtime",
}


@dataclass(frozen=True)
class SemanticColumnCandidate:
    role: str
    column: str
    confidence: float
    confidence_label: str
    reason: str
    score_breakdown: dict[str, float] = field(default_factory=dict)
    source: str = "auto"


@dataclass(frozen=True)
class SemanticColumnMatch:
    role: str
    column: str
    confidence: float
    reason: str
    confidence_label: str = "high"
    source: str = "auto"


@dataclass(frozen=True)
class DatasetSemanticProfile:
    domain: str
    roles: dict[str, SemanticColumnMatch]
    unmatched_columns: list[str]
    warnings: list[str]
    candidates: dict[str, list[SemanticColumnCandidate]] = field(default_factory=dict)
    domain_confidence: float = 0.5
    domain_reasons: list[str] = field(default_factory=list)
    overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "domain_confidence": self.domain_confidence,
            "domain_reasons": self.domain_reasons,
            "roles": {role: asdict(match) for role, match in self.roles.items()},
            "candidates": {
                role: [asdict(candidate) for candidate in candidates]
                for role, candidates in self.candidates.items()
            },
            "unmatched_columns": self.unmatched_columns,
            "warnings": self.warnings,
            "overrides": self.overrides,
        }


def build_semantic_profile(df: pd.DataFrame, overrides: dict[str, Any] | None = None) -> DatasetSemanticProfile:
    normalized_overrides = _normalize_overrides(overrides)
    normalized_dictionary = _normalize_data_dictionary(normalized_overrides.get("data_dictionary"))
    normalized_columns = {_normalize(column): column for column in df.columns}
    role_candidates = {
        role: _candidate_matches(role, keywords, normalized_columns, df)
        for role, keywords in SEMANTIC_ROLE_KEYWORDS.items()
    }

    roles: dict[str, SemanticColumnMatch] = {}
    for role, candidates in role_candidates.items():
        if candidates:
            top = candidates[0]
            if top.confidence >= 0.45:
                roles[role] = SemanticColumnMatch(
                    role=role,
                    column=top.column,
                    confidence=top.confidence,
                    confidence_label=top.confidence_label,
                    reason=top.reason,
                    source="auto",
                )

    dictionary_roles = normalized_dictionary.get("roles", {})
    for role, column in dictionary_roles.items():
        if column in df.columns:
            roles[role] = SemanticColumnMatch(
                role=role,
                column=column,
                confidence=1.0,
                confidence_label="dictionary",
                reason="Data dictionary mapping",
                source="dictionary",
            )

    override_roles = normalized_overrides.get("roles", {})
    for role, column in override_roles.items():
        if column in df.columns:
            roles[role] = SemanticColumnMatch(
                role=role,
                column=column,
                confidence=1.0,
                confidence_label="override",
                reason="User semantic override",
                source="override",
            )

    detected_domain, domain_confidence, domain_reasons = _infer_domain(roles, normalized_columns)
    domain = str(normalized_overrides.get("domain") or normalized_dictionary.get("domain") or detected_domain)
    if normalized_dictionary.get("domain"):
        domain_confidence = 1.0
        domain_reasons = ["Data dictionary domain mapping", *domain_reasons]
    if normalized_overrides.get("domain"):
        domain_confidence = 1.0
        domain_reasons = ["User domain override", *domain_reasons]

    matched_columns = {match.column for match in roles.values()}
    unmatched_columns = [column for column in df.columns if column not in matched_columns]
    warnings = _warnings_for_profile(domain, roles)

    return DatasetSemanticProfile(
        domain=domain,
        roles=roles,
        unmatched_columns=unmatched_columns,
        warnings=warnings,
        candidates=role_candidates,
        domain_confidence=domain_confidence,
        domain_reasons=domain_reasons,
        overrides=normalized_overrides,
    )


def _candidate_matches(
    role: str,
    keywords: list[str],
    normalized_columns: dict[str, str],
    df: pd.DataFrame,
) -> list[SemanticColumnCandidate]:
    candidates: list[SemanticColumnCandidate] = []
    normalized_keywords = [_normalize(keyword) for keyword in keywords]
    for normalized_column, original_column in normalized_columns.items():
        score_parts: dict[str, float] = {}
        if normalized_column in normalized_keywords:
            score_parts["exact_name"] = 0.72
        elif any(keyword in normalized_column for keyword in normalized_keywords):
            score_parts["partial_name"] = 0.55
        elif any(_token_overlap(normalized_column, keyword) for keyword in normalized_keywords):
            score_parts["token_overlap"] = 0.38

        dtype_score = _dtype_score(role, df[original_column])
        if dtype_score:
            score_parts["dtype"] = dtype_score
        value_score = _value_pattern_score(role, df[original_column])
        if value_score:
            score_parts["value_pattern"] = value_score
        prior_score = _domain_prior_score(role, normalized_column)
        if prior_score:
            score_parts["domain_prior"] = prior_score

        score = min(max(sum(score_parts.values()), 0.0), 1.0)
        if score >= 0.3:
            candidates.append(SemanticColumnCandidate(
                role=role,
                column=original_column,
                confidence=round(score, 3),
                confidence_label=_confidence_label(score),
                reason=_reason(score_parts),
                score_breakdown={key: round(value, 3) for key, value in score_parts.items()},
            ))
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)[:5]


def _infer_domain(
    roles: dict[str, SemanticColumnMatch],
    normalized_columns: dict[str, str],
) -> tuple[str, float, list[str]]:
    known = _domain_from_known_schema(normalized_columns)
    if known:
        return known, 0.95, [f"Known {known} schema pattern detected."]

    role_names = set(roles)
    if {"campaign", "target"} <= role_names or {"campaign", "conversion"} <= role_names:
        return "marketing", 0.82, ["Campaign and response/conversion roles detected."]
    if {"department", "target"} <= role_names and ({"employee", "salary"} & role_names):
        return "hr", 0.82, ["Department and attrition/target roles detected."]
    scores = {
        "hr": _score_domain(role_names, {"salary", "target", "department"}, {"employee", "overtime", "job_role"}),
        "marketing": _score_domain(role_names, {"conversion", "customer"}, {"campaign", "salary", "recency", "monetary", "frequency"}),
        "finance": _score_domain(role_names, {"revenue", "cost", "profit"}, {"date", "margin"}),
        "retail": _score_domain(role_names, {"revenue", "quantity", "category"}, {"profit", "discount", "state", "segment"}),
        "ecommerce": _score_domain(role_names, {"revenue", "quantity", "category"}, {"city", "state", "customer"}),
        "logistics": _score_logistics_domain(role_names, normalized_columns),
    }
    domain, score = max(scores.items(), key=lambda item: item[1])
    if score < 0.55:
        return "generic", 0.5, ["No domain-specific role combination was strong enough."]
    return domain, round(score, 3), [f"Detected roles support {domain}: {sorted(role_names)}"]


def _domain_from_known_schema(normalized_columns: dict[str, str]) -> str | None:
    columns = set(normalized_columns)
    amazon_columns = {"order_id", "sku", "asin", "fulfilment", "courier_status", "amount"}
    if len(amazon_columns & columns) >= 4:
        return "ecommerce"
    if {"attrition", "employeenumber", "monthlyincome", "department"} <= columns:
        return "hr"
    if {"response", "dt_customer", "numwebpurchases"} <= columns or {"response", "acceptedcmp1"} <= columns:
        return "marketing"
    if {"sales", "profit", "quantity"} <= columns and ({"segment", "category"} & columns):
        return "retail"
    traffic_columns = {"crash_date", "crash_time", "borough", "collision_id", "vehicle_type_code_1"}
    if len(traffic_columns & columns) >= 3 or {"date", "city", "vehicle_type", "accident_count"} <= columns:
        return "logistics"
    if {"date", "transit_mode", "ridership"} <= columns:
        return "logistics"
    return None


def _score_domain(role_names: set[str], required: set[str], optional: set[str]) -> float:
    required_score = len(required & role_names) / max(len(required), 1)
    optional_score = len(optional & role_names) / max(len(optional), 1)
    return min(required_score * 0.78 + optional_score * 0.22, 1.0)


def _score_logistics_domain(role_names: set[str], normalized_columns: dict[str, str]) -> float:
    markers = {
        "accident",
        "crash",
        "collision",
        "vehicle",
        "borough",
        "traffic",
        "transit",
        "ridership",
        "route",
        "shipping",
        "delivery",
        "dispatch",
    }
    marker_hits = sum(
        1 for column in normalized_columns
        if any(marker in column for marker in markers)
    )
    if marker_hits < 2:
        return 0.0
    return _score_domain(role_names, {"date", "quantity"}, {"city", "state", "category"})


def _warnings_for_profile(domain: str, roles: dict[str, SemanticColumnMatch]) -> list[str]:
    warnings = []
    if "revenue" not in roles and domain in {"ecommerce", "retail", "marketing", "finance"}:
        warnings.append("No confident revenue/sales column was detected.")
    if "date" not in roles:
        warnings.append("No confident date column was detected.")
    if domain == "hr" and "target" not in roles:
        warnings.append("HR-like dataset detected, but no attrition/target column was detected.")
    if domain == "marketing" and not ({"target", "conversion"} & set(roles)):
        warnings.append("Marketing-like dataset detected, but no response/conversion column was detected.")
    return warnings


def _dtype_score(role: str, series: pd.Series) -> float:
    if role == "date":
        return 0.25 if _looks_date_like(series) else -0.15
    if role in NUMERIC_ROLES:
        return 0.18 if pd.api.types.is_numeric_dtype(series) else -0.2
    if role in CATEGORICAL_ROLES:
        if pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
            unique = series.nunique(dropna=True)
            if 1 <= unique <= max(50, len(series) * 0.5):
                return 0.14
        return 0.0
    return 0.0


def _value_pattern_score(role: str, series: pd.Series) -> float:
    sample = series.dropna().head(100)
    if sample.empty:
        return 0.0
    if role in {"target", "conversion", "overtime"}:
        unique = {str(value).strip().lower() for value in sample.unique()}
        positives = {"yes", "true", "1", "y", "accepted", "converted"}
        negatives = {"no", "false", "0", "n", "not accepted"}
        if unique and unique <= positives | negatives:
            return 0.18
    if role == "country" and sample.astype(str).str.len().between(2, 30).mean() > 0.8:
        return 0.05
    return 0.0


def _domain_prior_score(role: str, normalized_column: str) -> float:
    if role == "customer" and normalized_column in {"id", "customerid", "customer_id"}:
        return 0.08
    if role == "campaign" and normalized_column.startswith("acceptedcmp"):
        return 0.22
    if role == "monetary" and normalized_column.startswith("mnt"):
        return 0.22
    if role == "frequency" and normalized_column.startswith("num") and "purchase" in normalized_column:
        return 0.22
    return 0.0


def _looks_date_like(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(30)
    if sample.empty:
        return False
    dateish = sample.str.contains(
        r"(?:\d{1,4}[-/]\d{1,2}[-/]\d{1,4})|(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(?:[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})",
        regex=True,
        na=False,
    )
    if dateish.mean() < 0.5:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return bool(parsed.notna().mean() >= 0.6)


def _token_overlap(normalized_column: str, normalized_keyword: str) -> bool:
    column_tokens = set(normalized_column.split("_"))
    keyword_tokens = set(normalized_keyword.split("_"))
    return bool(column_tokens & keyword_tokens) and len(normalized_keyword) > 2


def _reason(score_parts: dict[str, float]) -> str:
    if not score_parts:
        return "Weak semantic evidence"
    labels = {
        "exact_name": "exact name match",
        "partial_name": "partial name match",
        "token_overlap": "token overlap",
        "dtype": "compatible dtype",
        "value_pattern": "value pattern",
        "domain_prior": "domain prior",
    }
    return ", ".join(labels[key] for key in score_parts if key in labels)


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _normalize_overrides(overrides: dict[str, Any] | None) -> dict[str, Any]:
    if not overrides:
        return {"domain": None, "roles": {}, "data_dictionary": None}
    roles = overrides.get("roles") if isinstance(overrides.get("roles"), dict) else {}
    clean_roles = {str(role): str(column) for role, column in roles.items() if column}
    return {"domain": overrides.get("domain"), "roles": clean_roles, "data_dictionary": overrides.get("data_dictionary")}


def _normalize_data_dictionary(dictionary: dict[str, Any] | None) -> dict[str, Any]:
    if not dictionary:
        return {"domain": None, "roles": {}}
    roles: dict[str, str] = {}
    fields = dictionary.get("fields") if isinstance(dictionary.get("fields"), list) else []
    for field in fields:
        if not isinstance(field, dict):
            continue
        role = field.get("semantic_role")
        column = field.get("column_name")
        if role and column:
            roles[str(role)] = str(column)
    return {"domain": dictionary.get("domain"), "roles": roles}


def _normalize(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized
