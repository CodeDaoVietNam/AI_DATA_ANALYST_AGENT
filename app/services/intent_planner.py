from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


TASKS = {
    "overview",
    "data_quality",
    "correlation",
    "chart",
    "trend",
    "breakdown",
    "target_summary",
    "compare",
    "top_bottom",
    "outlier",
    "anomaly",
    "forecast",
    "pareto",
    "metric_change",
    "ecommerce_risk",
    "unknown",
}

METRIC_ROLE_KEYWORDS = {
    "revenue": ["revenue", "doanh thu", "sales", "amount", "total sales", "price", "gia", "giá", "valuation", "value"],
    "profit": ["profit", "loi nhuan", "lợi nhuận", "margin"],
    "cost": ["cost", "chi phi", "chi phí"],
    "quantity": ["quantity", "qty", "so luong", "số lượng", "units", "population", "complaint", "complaints", "ridership", "accident", "accidents", "injured", "thuong", "thương", "mpg", "fuel economy", "flight distance", "absences"],
    "salary": ["salary", "income", "luong", "lương", "thu nhap", "thu nhập"],
    "target": ["target", "attrition", "conversion", "response", "satisfaction", "grade", "final grade", "diem", "điểm"],
    "conversion": ["conversion", "response", "converted"],
    "monetary": ["balance", "monetary"],
}

DIMENSION_ROLE_KEYWORDS = {
    "category": ["category", "danh muc", "danh mục", "nganh hang", "ngành hàng", "product group", "product", "manufacturer", "transit mode", "vehicle type", "class", "ticker", "symbol"],
    "segment": ["segment", "phan khuc", "phân khúc", "customer type"],
    "state": ["state", "tinh", "tỉnh", "bang", "khu vuc", "khu vực"],
    "city": ["city", "thanh pho", "thành phố"],
    "country": ["country", "quoc gia", "quốc gia"],
    "department": ["department", "phong ban", "phòng ban", "school"],
    "job_role": ["job role", "jobrole", "chuc danh", "chức danh"],
    "campaign": ["campaign", "chien dich", "chiến dịch"],
    "channel": ["channel", "kenh", "kênh"],
    "customer": ["customer", "khach hang", "khách hàng"],
    "frequency": ["frequency", "study time", "studytime"],
    "overtime": ["overtime", "over time"],
    "target": ["target", "satisfaction", "attrition", "conversion", "response"],
    "date": ["date", "time", "ngay", "ngày", "thang", "tháng", "month"],
}


@dataclass
class IntentFilter:
    field: str
    operator: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntentComparison:
    type: str
    baseline: str | None = None
    target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UniversalAnalysisIntent:
    task: str = "unknown"
    metric: str | None = None
    metric_source: str | None = None
    dimension: str | None = None
    time_grain: str | None = None
    filters: list[IntentFilter] = field(default_factory=list)
    comparison: IntentComparison | None = None
    chart_type: str | None = None
    limit: int | None = None
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "metric": self.metric,
            "metric_source": self.metric_source,
            "dimension": self.dimension,
            "time_grain": self.time_grain,
            "filters": [item.to_dict() for item in self.filters],
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "chart_type": self.chart_type,
            "limit": self.limit,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
        }


def parse_universal_intent(
    question: str,
    df: pd.DataFrame,
    profile,
    custom_metrics: list[dict[str, Any]] | None = None,
    *,
    ecommerce_available: bool = False,
) -> UniversalAnalysisIntent:
    text = _normalize(question)
    custom_metrics = custom_metrics or []
    reasons: list[str] = []

    metric, metric_source = _detect_custom_metric(text, custom_metrics)
    if metric:
        reasons.append(f"Detected custom metric `{metric}`.")
    if not metric:
        metric, metric_source = _detect_semantic_metric(text, profile, df)
        if metric:
            reasons.append(f"Detected semantic/column metric `{metric}`.")
    if not metric and _has_any(text, ["duplicate", "duplicates", "trung lap", "trùng lặp", "trung dong"]):
        metric, metric_source = "duplicates", "system"
        reasons.append("Detected duplicate-row data quality check.")
    if not metric and _has_any(text, ["missing", "null", "nan", "thieu", "thiếu"]):
        metric, metric_source = "missing", "system"
        reasons.append("Detected missing-value data quality check.")

    dimension = _detect_dimension(text, profile, df)
    if dimension:
        reasons.append(f"Detected dimension `{dimension}`.")

    task = _detect_task(text, metric, dimension, ecommerce_available)
    if task != "unknown":
        reasons.append(f"Detected task `{task}`.")

    time_grain = _detect_time_grain(text)
    if time_grain:
        reasons.append(f"Detected time grain `{time_grain}`.")
        if task in {"breakdown", "unknown"} and dimension is None:
            task = "trend"
            dimension = "date"

    chart_type = _detect_chart_type(text, task)
    limit = _extract_limit(text)
    comparison = _detect_comparison(text)
    confidence = _confidence(task, metric, dimension, reasons)

    return UniversalAnalysisIntent(
        task=task,
        metric=metric,
        metric_source=metric_source,
        dimension=dimension,
        time_grain=time_grain,
        filters=[],
        comparison=comparison,
        chart_type=chart_type,
        limit=limit,
        confidence=confidence,
        reasons=reasons,
    )


def compile_intent_to_plan(
    intent: UniversalAnalysisIntent,
    df: pd.DataFrame,
    profile,
    custom_metrics: list[dict[str, Any]] | None = None,
    *,
    ecommerce_available: bool = False,
    min_confidence: float = 0.55,
) -> dict[str, Any] | None:
    if intent.confidence < min_confidence or intent.task == "unknown":
        return None
    custom_metrics = custom_metrics or []
    step = _compile_single_step(intent, df, profile, custom_metrics, ecommerce_available=ecommerce_available)
    if not step:
        return None
    return {
        "plan_id": _stable_plan_id(intent),
        "strategy": f"intent:{intent.task}",
        "max_steps": 3,
        "intent": intent.to_dict(),
        "steps": [step],
    }


def _compile_single_step(
    intent: UniversalAnalysisIntent,
    df: pd.DataFrame,
    profile,
    custom_metrics: list[dict[str, Any]],
    *,
    ecommerce_available: bool,
) -> dict[str, Any] | None:
    if intent.task == "overview":
        return {"tool_name": "get_sales_overview" if ecommerce_available else "get_dataset_overview", "arguments": {}, "purpose": "Dataset overview from universal intent."}
    if intent.task == "data_quality":
        return {"tool_name": "get_duplicate_rows" if intent.metric == "duplicates" else "get_missing_values", "arguments": {}, "purpose": "Data quality check from universal intent."}
    if intent.task == "correlation":
        return {"tool_name": "correlation_analysis", "arguments": {}, "purpose": "Correlation analysis from universal intent."}
    if intent.task == "target_summary":
        return {"tool_name": "semantic_target_summary", "arguments": {"by_role": intent.dimension}, "purpose": "Target/conversion summary from universal intent."}

    if intent.metric_source == "custom_metric":
        if intent.task in {"breakdown", "top_bottom"} and intent.dimension:
            return {
                "tool_name": "custom_metric_breakdown",
                "arguments": {"metric_name": intent.metric, "by_role": intent.dimension, "limit": intent.limit or 20},
                "purpose": "Custom metric breakdown from universal intent.",
            }
        return {
            "tool_name": "evaluate_custom_metric",
            "arguments": {"metric_name": intent.metric},
            "purpose": "Custom metric evaluation from universal intent.",
        }

    if intent.task == "trend":
        if _role_column(profile, "date") and _metric_column(intent, profile, df):
            return {"tool_name": "semantic_time_series", "arguments": {"metric_role": intent.metric}, "purpose": "Semantic time series from universal intent."}
        date_col = _role_column(profile, "date") or _first_matching_column(df, ["date", "time"])
        metric_col = _metric_column(intent, profile, df)
        if date_col and metric_col:
            return {
                "tool_name": "trend_analysis",
                "arguments": {"date_column": date_col, "metric_column": metric_col, "freq": _freq(intent.time_grain), "aggregation": "sum"},
                "purpose": "Column trend analysis from universal intent.",
            }

    if intent.task in {"breakdown", "top_bottom"} and intent.dimension and intent.metric:
        if intent.metric_source == "semantic_role" and intent.dimension in getattr(profile, "roles", {}):
            return {
                "tool_name": "semantic_breakdown",
                "arguments": {"by_role": intent.dimension, "metric_role": intent.metric, "limit": intent.limit or 20},
                "purpose": "Semantic breakdown from universal intent.",
            }
        group_col = _role_column(profile, intent.dimension) or _column_by_name(df, intent.dimension)
        metric_col = _metric_column(intent, profile, df)
        if group_col and metric_col:
            if intent.task == "top_bottom":
                return {
                    "tool_name": "top_bottom_contributors",
                    "arguments": {"group_column": group_col, "metric_column": metric_col, "n": intent.limit or 5},
                    "purpose": "Top/bottom contributors from universal intent.",
                }
            return {
                "tool_name": "groupby_aggregate",
                "arguments": {"group_by": group_col, "metric": metric_col, "aggregation": "sum", "limit": intent.limit or 50},
                "purpose": "Column groupby aggregate from universal intent.",
            }

    if intent.task == "chart":
        x = _role_column(profile, intent.dimension or "") or _column_by_name(df, intent.dimension or "") or _fallback_x(df)
        y = _metric_column(intent, profile, df)
        if x:
            return {
                "tool_name": "generate_chart_spec",
                "arguments": {"chart_type": intent.chart_type or "bar", "x": x, "y": y},
                "purpose": "Chart generation from universal intent.",
            }

    if intent.task == "outlier":
        metric_col = _metric_column(intent, profile, df) or _role_column(profile, "quantity") or _role_column(profile, "revenue") or _role_column(profile, "profit") or _first_numeric_column(df)
        if metric_col:
            return {"tool_name": "detect_outliers", "arguments": {"metric_column": metric_col}, "purpose": "Outlier detection from universal intent."}
    if intent.task == "anomaly":
        date_col = _role_column(profile, "date") or _first_matching_column(df, ["date", "time"])
        metric_col = _metric_column(intent, profile, df) or _role_column(profile, "quantity") or _role_column(profile, "revenue") or _role_column(profile, "profit") or _first_numeric_column(df)
        if date_col and metric_col:
            return {"tool_name": "anomaly_detection", "arguments": {"date_column": date_col, "metric_column": metric_col, "freq": _freq(intent.time_grain)}, "purpose": "Anomaly detection from universal intent."}
    if intent.task == "forecast":
        date_col = _role_column(profile, "date") or _first_matching_column(df, ["date", "time"])
        metric_col = _metric_column(intent, profile, df) or _first_numeric_column(df)
        if date_col and metric_col:
            return {"tool_name": "forecast_next_period", "arguments": {"date_column": date_col, "metric_column": metric_col, "periods": intent.limit or 3}, "purpose": "Forecast from universal intent."}
    if intent.task == "pareto":
        group_col = _role_column(profile, intent.dimension or "category") or _fallback_x(df)
        metric_col = _metric_column(intent, profile, df) or _first_numeric_column(df)
        if group_col and metric_col:
            return {"tool_name": "pareto_analysis", "arguments": {"category_column": group_col, "metric_column": metric_col}, "purpose": "Pareto analysis from universal intent."}
    return None


def _detect_task(text: str, metric: str | None, dimension: str | None, ecommerce_available: bool) -> str:
    if _has_any(text, ["overview", "tong quan", "tổng quan", "summary", "mo ta", "mô tả"]):
        return "overview"
    if _has_any(text, ["missing", "null", "nan", "thieu", "thiếu"]):
        return "data_quality"
    if _has_any(text, ["duplicate", "trung lap", "trùng lặp", "trung dong"]):
        return "data_quality"
    if _has_any(text, ["correlation", "tuong quan", "tương quan"]):
        return "correlation"
    if _has_any(text, ["chart", "plot", "visual", "bieu do", "biểu đồ", "ve ", "vẽ "]):
        return "chart"
    if ecommerce_available and _has_any(text, ["cancel", "huy", "huỷ", "risk", "rủi ro", "rui ro"]):
        return "ecommerce_risk"
    if _has_any(text, ["forecast", "du bao", "dự báo", "next period"]):
        return "forecast"
    if _has_any(text, ["anomaly", "bat thuong", "bất thường"]):
        return "anomaly"
    if _has_any(text, ["outlier", "ngoai lai", "ngoại lai"]):
        return "outlier"
    if _has_any(text, ["pareto", "80/20", "80 20"]):
        return "pareto"
    if _has_any(text, ["trend", "xu huong", "xu hướng", "theo thang", "theo tháng", "monthly", "month"]):
        return "trend"
    if _has_any(text, ["top", "cao nhat", "cao nhất", "nhieu nhat", "nhiều nhất", "most", "thap nhat", "thấp nhất", "bottom"]) or ("nhieu" in text and "nhat" in text):
        return "top_bottom" if dimension else "breakdown"
    if _has_any(text, ["attrition", "conversion", "response", "target", "satisfaction"]) and (not metric or metric in {"target", "conversion"}):
        return "target_summary"
    if metric and dimension:
        return "breakdown"
    if metric:
        return "breakdown"
    return "unknown"


def _detect_custom_metric(text: str, custom_metrics: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    normalized_text = text.replace("_", " ")
    for metric in custom_metrics:
        for value in [metric.get("name"), metric.get("label")]:
            if not value:
                continue
            candidate = _normalize(str(value)).replace("_", " ")
            if candidate and candidate in normalized_text:
                return str(metric.get("name")), "custom_metric"
    return None, None


def _detect_semantic_metric(text: str, profile, df: pd.DataFrame) -> tuple[str | None, str | None]:
    for role, keywords in METRIC_ROLE_KEYWORDS.items():
        if _has_any(text, keywords):
            if role in getattr(profile, "roles", {}):
                return role, "semantic_role"
            column = _first_matching_column(df, keywords)
            if column:
                return column, "column"
    for column in df.columns:
        normalized_column = _normalize(str(column))
        if normalized_column and normalized_column in text and pd.api.types.is_numeric_dtype(df[column]):
            return str(column), "column"
    numeric = _first_numeric_column(df)
    if numeric and _has_any(text, ["metric", "chi so", "chỉ số", "value", "gia tri", "giá trị"]):
        return numeric, "column"
    return None, None


def _detect_dimension(text: str, profile, df: pd.DataFrame) -> str | None:
    for role, keywords in DIMENSION_ROLE_KEYWORDS.items():
        if _has_any(text, keywords):
            if role in getattr(profile, "roles", {}):
                return role
            if _first_matching_column(df, keywords):
                return role
    if _has_any(text, ["theo", "by"]):
        for column in df.columns:
            normalized = _normalize(str(column))
            if normalized and normalized in text:
                return str(column)
    return None


def _detect_time_grain(text: str) -> str | None:
    if _has_any(text, ["day", "ngay", "ngày", "daily"]):
        return "day"
    if _has_any(text, ["month", "thang", "tháng", "monthly"]):
        return "month"
    if _has_any(text, ["quarter", "quy", "quý"]):
        return "quarter"
    if _has_any(text, ["year", "nam", "năm", "yearly"]):
        return "year"
    return None


def _detect_chart_type(text: str, task: str) -> str | None:
    if task != "chart":
        return None
    if _has_any(text, ["line", "duong", "đường", "trend"]):
        return "line"
    if _has_any(text, ["scatter"]):
        return "scatter"
    if _has_any(text, ["histogram"]):
        return "histogram"
    if _has_any(text, ["box"]):
        return "box"
    return "bar"


def _detect_comparison(text: str) -> IntentComparison | None:
    if _has_any(text, ["compare", "so sanh", "so sánh", "vs", "versus"]):
        return IntentComparison(type="compare")
    return None


def _extract_limit(text: str) -> int | None:
    match = re.search(r"\btop\s*(\d+)|\b(\d+)\s*(category|segment|state|city|sku|nhom|nhóm)", text)
    if not match:
        return None
    value = next(group for group in match.groups() if group and group.isdigit())
    return max(1, min(int(value), 100))


def _confidence(task: str, metric: str | None, dimension: str | None, reasons: list[str]) -> float:
    if task == "unknown":
        return 0.0
    score = 0.35
    if metric:
        score += 0.25
    if dimension:
        score += 0.2
    if len(reasons) >= 2:
        score += 0.15
    if task in {"overview", "data_quality", "correlation"}:
        score = max(score, 0.78)
    if task in {"outlier", "anomaly"}:
        score = max(score, 0.6)
    return min(score, 0.95)


def _metric_column(intent: UniversalAnalysisIntent, profile, df: pd.DataFrame) -> str | None:
    if not intent.metric:
        return None
    if intent.metric_source == "semantic_role":
        return _role_column(profile, intent.metric)
    return _column_by_name(df, intent.metric)


def _role_column(profile, role: str) -> str | None:
    match = getattr(profile, "roles", {}).get(role)
    return getattr(match, "column", None) if match else None


def _column_by_name(df: pd.DataFrame, name: str | None) -> str | None:
    if not name:
        return None
    normalized = _normalize(name)
    for column in df.columns:
        if _normalize(str(column)) == normalized:
            return str(column)
    return None


def _first_matching_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    for column in df.columns:
        normalized = _normalize(str(column))
        if any(_normalize(keyword) in normalized for keyword in keywords):
            return str(column)
    return None


def _first_numeric_column(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            return str(column)
    return None


def _fallback_x(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            return str(column)
    return next(iter(df.columns), None)


def _freq(time_grain: str | None) -> str:
    return {"day": "D", "month": "M", "quarter": "Q", "year": "Y"}.get(time_grain or "month", "M")


def _stable_plan_id(intent: UniversalAnalysisIntent) -> str:
    return f"intent-{abs(hash(str(intent.to_dict()))) % 10_000_000}"


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(_normalize(keyword) in text for keyword in keywords)


def _normalize(value: str) -> str:
    replacements = {
        "đ": "d", "Đ": "d",
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a", "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a", "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o", "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    text = str(value).lower()
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
