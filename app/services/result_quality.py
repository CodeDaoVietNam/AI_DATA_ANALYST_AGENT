from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ResultQualityStatus = Literal["strong", "partial", "empty", "insufficient", "tool_error"]


@dataclass(frozen=True)
class ResultQuality:
    status: ResultQualityStatus
    reason: str
    has_rows: bool
    row_count: int | None
    has_metric: bool
    metric_name: str | None
    metric_value: Any | None
    has_label: bool
    label: str | None
    render_mode: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_result_quality(
    *,
    tool_name: str,
    result: Any,
    result_summary: dict[str, Any] | None,
) -> ResultQuality:
    """Classify tool output before it is turned into a user-facing answer."""
    result_summary = result_summary or {}

    if _is_tool_error(result):
        return ResultQuality(
            status="tool_error",
            reason="Tool returned an error payload.",
            has_rows=False,
            row_count=None,
            has_metric=False,
            metric_name=None,
            metric_value=None,
            has_label=False,
            label=None,
            render_mode="tool_error",
            warnings=["Công cụ phân tích gặp lỗi nên không có kết quả đáng tin để diễn giải."],
        )

    rows = _extract_rows(result)
    row_count = _row_count(result, rows, result_summary)
    top_item = result_summary.get("top_item") if isinstance(result_summary.get("top_item"), dict) else (rows[0] if rows else None)
    metric_name, metric_value = _best_metric(top_item if isinstance(top_item, dict) else None)
    if metric_name is None:
        metric_name = result_summary.get("primary_metric")
        metric_value = result_summary.get("primary_metric_value")
    if metric_name is None and isinstance(result, dict):
        metric_name, metric_value = _best_metric(result.get("metrics") if isinstance(result.get("metrics"), dict) else result)
    label = _best_label(top_item if isinstance(top_item, dict) else None)

    has_rows = bool(rows)
    has_metric = bool(metric_name) and _is_useful_metric_value(metric_value)
    has_label = bool(label)

    if _is_empty_result(result, rows):
        return ResultQuality(
            status="empty",
            reason="Tool finished but returned no usable output.",
            has_rows=False,
            row_count=row_count,
            has_metric=False,
            metric_name=None,
            metric_value=None,
            has_label=False,
            label=None,
            render_mode="insufficient_result",
            warnings=["Công cụ đã chạy nhưng không trả về bảng, metric hoặc text đủ rõ."],
        )

    if has_rows and has_metric and has_label:
        return ResultQuality(
            status="strong",
            reason="Result contains rows, a label, and a numeric metric.",
            has_rows=True,
            row_count=row_count,
            has_metric=True,
            metric_name=str(metric_name),
            metric_value=metric_value,
            has_label=True,
            label=label,
            render_mode="answer_card",
            warnings=[],
        )

    if has_rows:
        return ResultQuality(
            status="partial",
            reason="Result has rows but is missing either a clear label or numeric metric.",
            has_rows=True,
            row_count=row_count,
            has_metric=has_metric,
            metric_name=str(metric_name) if metric_name else None,
            metric_value=metric_value if has_metric else None,
            has_label=has_label,
            label=label,
            render_mode="answer_card",
            warnings=["Kết quả có bảng nhưng thiếu metric hoặc nhãn nổi bật đủ rõ; cần đọc như tín hiệu sơ bộ."],
        )

    if isinstance(result, dict):
        status: ResultQualityStatus = "partial" if has_metric else "insufficient"
        return ResultQuality(
            status=status,
            reason="Result is a dictionary without a clear table/top item.",
            has_rows=False,
            row_count=row_count,
            has_metric=has_metric,
            metric_name=str(metric_name) if has_metric else None,
            metric_value=metric_value if has_metric else None,
            has_label=False,
            label=None,
            render_mode="answer_card" if status == "partial" else "insufficient_result",
            warnings=[] if status == "partial" else ["Kết quả dạng dict nhưng chưa có metric đủ rõ để kết luận."],
        )

    return ResultQuality(
        status="insufficient",
        reason=f"Tool result type `{type(result).__name__}` is not structured enough for a grounded insight.",
        has_rows=False,
        row_count=row_count,
        has_metric=False,
        metric_name=None,
        metric_value=None,
        has_label=False,
        label=None,
        render_mode="insufficient_result",
        warnings=["Tool result chưa có cấu trúc đủ rõ để tạo kết luận đáng tin."],
    )


def _is_tool_error(result: Any) -> bool:
    return isinstance(result, dict) and (result.get("success") is False or bool(result.get("error")))


def _is_empty_result(result: Any, rows: list[dict[str, Any]]) -> bool:
    if result is None:
        return True
    if isinstance(result, list):
        return len(result) == 0
    if isinstance(result, str):
        return not result.strip()
    if isinstance(result, dict):
        if result.get("result_type") == "empty":
            return True
        if not result:
            return True
        nested_result = result.get("result")
        looks_like_tool_wrapper = any(key in result for key in ["success", "result_type", "stdout", "metrics"])
        if looks_like_tool_wrapper and nested_result is None and result.get("stdout", "") == "" and not rows and not result.get("metrics"):
            return True
        if isinstance(nested_result, str) and not nested_result.strip() and not result.get("metrics"):
            return True
    return False


def _row_count(result: Any, rows: list[dict[str, Any]], summary: dict[str, Any]) -> int | None:
    if isinstance(summary.get("row_count"), int):
        return summary["row_count"]
    if isinstance(result, dict) and isinstance(result.get("row_count"), int):
        return result["row_count"]
    if rows:
        return len(rows)
    return None


def _extract_rows(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [row for row in result if isinstance(row, dict)]
    if isinstance(result, dict):
        for key in ["items", "rows", "result"]:
            value = result.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if "tool_results" in result and isinstance(result["tool_results"], list):
            rows: list[dict[str, Any]] = []
            for item in result["tool_results"]:
                if isinstance(item, dict):
                    rows.extend(_extract_rows(item.get("result")))
            return rows
    return []


def _best_label(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    preferred = [
        "sku", "category", "segment", "Segment", "size", "ship_state", "ship_city",
        "state", "city", "country", "order_month", "department", "job_role",
        "jobrole", "campaign", "channel", "label", "name",
    ]
    for key in preferred:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    for value in row.values():
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _best_metric(row: dict[str, Any] | None) -> tuple[str | None, Any]:
    if not row:
        return None, None
    preferred = [
        "value", "revenue", "sales", "profit", "margin", "amount", "total_revenue",
        "qty", "quantity", "orders", "rows", "count", "cancel_rate",
        "attrition_rate", "positive_rate", "response_rate", "missing_percent",
        "duplicate_rows",
    ]
    for key in preferred:
        value = row.get(key)
        if _is_useful_metric_value(value):
            return key, value
    for key, value in row.items():
        if _is_useful_metric_value(value):
            return key, value
    return None, None


def _is_useful_metric_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == value
    return False
