from __future__ import annotations

from typing import Any


def compose_answer_card(
    *,
    question: str,
    tool_name: str,
    arguments: dict[str, Any] | None,
    result: Any,
    result_summary: dict[str, Any] | None,
    semantic_profile: Any | None = None,
    warnings: list[str] | None = None,
    result_quality: Any | None = None,
    answer_source: str = "deterministic_composer",
) -> dict[str, Any]:
    """Create a product-grade, JSON-safe answer card from deterministic tool output."""
    arguments = arguments or {}
    result_summary = result_summary or {}
    warnings = warnings or []
    if _is_weak_quality(result_quality):
        return _insufficient_result_card(
            question=question,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            result_summary=result_summary,
            result_quality=result_quality,
            warnings=warnings,
            answer_source=answer_source,
        )
    rows = _extract_rows(result)
    top_item = result_summary.get("top_item") or (rows[0] if rows else None)
    label = _best_label(top_item) if isinstance(top_item, dict) else None
    metric, metric_value = _best_metric(top_item if isinstance(top_item, dict) else result if isinstance(result, dict) else {})
    domain = getattr(semantic_profile, "domain", None) or "generic"

    headline = _headline(tool_name, label, metric, metric_value, result, domain)
    summary = _summary(tool_name, label, metric, metric_value, rows, result)
    evidence = _evidence(tool_name, result, result_summary, top_item, rows)
    data_warnings = _data_warnings(tool_name, result, rows, warnings)
    takeaways = _takeaways(tool_name, label, metric, metric_value, rows, data_warnings)

    return {
        "headline": headline,
        "summary": summary,
        "key_takeaways": takeaways,
        "evidence": evidence,
        "why_it_matters": _why_it_matters(tool_name, domain),
        "recommended_next_questions": _recommended_questions(tool_name, label, metric, domain, question),
        "confidence": _confidence(rows, result, data_warnings),
        "answer_source": answer_source,
        "data_warnings": data_warnings,
        "calculation_notes": _calculation_notes(tool_name, arguments, rows, result),
    }


def answer_card_to_text(card: dict[str, Any]) -> str:
    """Render answer_card into a legacy markdown-ish text answer."""
    lines = [str(card.get("headline") or "Mình đã hoàn tất phân tích."), ""]
    summary = card.get("summary")
    if summary:
        lines.extend([str(summary), ""])

    evidence = card.get("evidence") or []
    if evidence:
        lines.append("Bằng chứng:")
        for item in evidence[:5]:
            label = item.get("label", "Chỉ số")
            value = item.get("value", "Không có dữ liệu")
            description = item.get("description")
            suffix = f" - {description}" if description else ""
            lines.append(f"- {label}: {value}{suffix}")
        lines.append("")

    why = card.get("why_it_matters")
    if why:
        lines.extend(["Vì sao quan trọng:", str(why), ""])

    warnings = card.get("data_warnings") or []
    if warnings:
        lines.append("Cảnh báo dữ liệu:")
        for warning in warnings[:3]:
            lines.append(f"- {warning}")
        lines.append("")

    questions = card.get("recommended_next_questions") or []
    if questions:
        lines.extend(["Nên hỏi tiếp:", f"- {questions[0]}"])

    return "\n".join(lines).strip()


def merge_llm_answer_card(base_card: dict[str, Any], llm_card: dict[str, Any]) -> dict[str, Any]:
    """Allow LLM to polish words while preserving deterministic evidence and warnings."""
    merged = dict(base_card)
    for key in ["headline", "summary", "why_it_matters"]:
        value = llm_card.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()[:900]
    questions = llm_card.get("recommended_next_questions")
    if isinstance(questions, list):
        cleaned = [str(item).strip() for item in questions if str(item).strip()]
        if cleaned:
            merged["recommended_next_questions"] = cleaned[:5]
    takeaways = llm_card.get("key_takeaways")
    if isinstance(takeaways, list):
        cleaned_takeaways = []
        for item in takeaways[:5]:
            if isinstance(item, dict) and item.get("text"):
                cleaned_takeaways.append({
                    "label": str(item.get("label") or "Insight")[:80],
                    "text": str(item["text"])[:500],
                    "tone": _safe_tone(item.get("tone")),
                })
        if cleaned_takeaways:
            merged["key_takeaways"] = cleaned_takeaways
    merged["answer_source"] = "llm_structured"
    merged["evidence"] = base_card.get("evidence", [])
    merged["data_warnings"] = base_card.get("data_warnings", [])
    merged["calculation_notes"] = base_card.get("calculation_notes", [])
    return merged


def _insufficient_result_card(
    *,
    question: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
    result_summary: dict[str, Any],
    result_quality: Any,
    warnings: list[str],
    answer_source: str,
) -> dict[str, Any]:
    quality = _quality_dict(result_quality)
    quality_warnings = [str(item) for item in quality.get("warnings", []) if item]
    row_count = quality.get("row_count", result_summary.get("row_count"))
    reason = quality.get("reason") or "Tool result chưa có cấu trúc đủ rõ để tạo kết luận."
    data_warnings = list(dict.fromkeys([
        *warnings,
        *quality_warnings,
        "Tool result không có metric, bảng hoặc nhóm nổi bật đủ rõ để kết luận chắc chắn.",
    ]))
    evidence = [
        {
            "label": "Công cụ đã chạy",
            "value": _humanize_tool_name(tool_name),
            "description": "Backend đã thực thi công cụ deterministic, nhưng output chưa đủ rõ để tạo insight.",
        },
        {
            "label": "Trạng thái kết quả",
            "value": "Chưa đủ dữ liệu để kết luận",
            "description": str(reason),
        },
    ]
    if row_count is not None:
        evidence.append({
            "label": "Số dòng kết quả",
            "value": _format_value(row_count),
            "description": "Số dòng usable mà tool trả về.",
        })
    if isinstance(result, dict) and result.get("result_type"):
        evidence.append({
            "label": "Kiểu output",
            "value": str(result.get("result_type")),
            "description": "Schema output từ công cụ phân tích.",
        })

    return {
        "headline": "Mình đã chạy phân tích, nhưng chưa đủ dữ liệu rõ để kết luận.",
        "summary": f"Công cụ `{_humanize_tool_name(tool_name)}` đã hoàn tất, nhưng kết quả không có metric/top item/bảng đủ rõ. Mình sẽ không suy diễn insight khi evidence còn yếu.",
        "key_takeaways": [
            {
                "label": "Chưa đủ evidence",
                "text": "Không có metric hoặc nhóm nổi bật đáng tin, nên hệ thống không nên gọi đây là kết luận kinh doanh.",
                "tone": "warning",
            },
            {
                "label": "Cách hỏi lại",
                "text": "Hãy nêu rõ metric và dimension, ví dụ: doanh thu theo category, margin theo segment, hoặc missing values theo cột.",
                "tone": "neutral",
            },
        ],
        "evidence": evidence[:6],
        "why_it_matters": "Nếu không có evidence rõ, hệ thống cần nói thật về giới hạn thay vì tạo kết luận giả. Đây là lớp bảo vệ trust cho Copilot.",
        "recommended_next_questions": _insufficient_next_questions(tool_name, question, arguments),
        "confidence": "low",
        "answer_source": answer_source,
        "data_warnings": data_warnings[:6],
        "calculation_notes": [
            f"Kết quả được tính bằng công cụ deterministic `{_humanize_tool_name(tool_name)}`.",
            f"Tham số công cụ: {arguments}." if arguments else "Công cụ không nhận tham số đặc biệt.",
            "Nếu dùng Python sandbox, code nên set biến `result` thành DataFrame/list/dict/scalar để UI render được.",
        ],
    }


def compose_tool_error_card(tool_name: str, arguments: dict[str, Any], error: str) -> dict[str, Any]:
    card = {
        "headline": "Mình chưa chạy được phân tích này.",
        "summary": f"Công cụ `{_humanize_tool_name(tool_name)}` gặp lỗi: {error}",
        "key_takeaways": [
            {"label": "Lỗi công cụ", "text": "Câu hỏi đã được nhận nhưng bước tính toán chưa hoàn tất.", "tone": "risk"},
            {"label": "Hành động tiếp theo", "text": "Bạn có thể hỏi lại rõ metric/dimension hơn hoặc kiểm tra semantic mapping.", "tone": "neutral"},
        ],
        "evidence": [
            {"label": "Công cụ phân tích", "value": _humanize_tool_name(tool_name), "description": "Công cụ được chọn trước khi lỗi xảy ra."},
        ],
        "why_it_matters": "Khi công cụ không chạy được, hệ thống không nên bịa số liệu. Cần sửa input/mapping hoặc chọn fallback an toàn.",
        "recommended_next_questions": ["Hãy tổng quan dataset này trước.", "Dataset này đang có những cột semantic nào?"],
        "confidence": "low",
        "answer_source": "tool_error",
        "data_warnings": [error],
        "calculation_notes": [f"Tham số công cụ: {arguments}"],
    }
    return card


def _headline(tool_name: str, label: str | None, metric: str | None, metric_value: Any, result: Any, domain: str) -> str:
    label_text = label or "nhóm đứng đầu"
    metric_text = _humanize(metric or "metric")
    if tool_name == "multi_step":
        return "Mình đã tổng hợp nhiều góc phân tích để trả lời câu hỏi này."
    if "missing" in tool_name:
        return "Chất lượng dữ liệu có một số điểm cần kiểm tra trước khi tin hoàn toàn vào insight."
    if "duplicate" in tool_name:
        return "Mình đã kiểm tra dòng trùng lặp để đánh giá độ sạch của dataset."
    if "chart" in tool_name:
        return "Biểu đồ đã được tạo từ các cột phù hợp trong dataset."
    if any(token in tool_name for token in ["cancellation", "attrition", "risk", "target"]):
        return f"{label_text} là nhóm cần chú ý về rủi ro."
    if "overview" in tool_name:
        return f"Dataset {domain} đã được tóm tắt ở mức tổng quan."
    if isinstance(result, dict) and not _extract_rows(result):
        if not metric or not _is_present_metric(metric_value):
            return "Mình đã chạy phân tích, nhưng chưa đủ dữ liệu rõ để kết luận."
        return f"Kết quả nổi bật nhất là {_humanize(metric or 'metric')} = {_format_value(metric_value)}."
    return f"{label_text} đang dẫn đầu theo {metric_text}."


def _summary(tool_name: str, label: str | None, metric: str | None, metric_value: Any, rows: list[dict[str, Any]], result: Any) -> str:
    if rows and label:
        return f"Công cụ `{_humanize_tool_name(tool_name)}` trả về {len(rows)} dòng kết quả; dòng nổi bật nhất là `{label}` với {_humanize(metric or 'metric')} = {_format_value(metric_value)}."
    if isinstance(result, dict):
        metric_name, value = _best_metric(result)
        if not metric_name or not _is_present_metric(value):
            return f"Công cụ `{_humanize_tool_name(tool_name)}` đã chạy xong, nhưng output chưa có chỉ số nổi bật đủ rõ để kết luận."
        return f"Công cụ `{_humanize_tool_name(tool_name)}` đã chạy xong; chỉ số nổi bật là {_humanize(metric_name or 'metric')} = {_format_value(value)}."
    return f"Công cụ `{_humanize_tool_name(tool_name)}` đã chạy xong và trả về kết quả có thể dùng để phân tích tiếp."


def _evidence(tool_name: str, result: Any, summary: dict[str, Any], top_item: Any, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    if isinstance(top_item, dict):
        label = _best_label(top_item)
        metric, value = _best_metric(top_item)
        evidence.append({"label": "Nhóm nổi bật", "value": label, "description": "Dòng đầu tiên hoặc nhóm nổi bật nhất trong kết quả công cụ."})
        if metric:
            evidence.append({"label": _humanize(metric), "value": _format_value(value), "description": "Chỉ số chính trong kết quả."})
        for key in ["orders", "qty", "rows", "cancel_rate", "attrition_rate", "positive_rate", "margin", "revenue_share"]:
            if key in top_item and key != metric:
                evidence.append({"label": _humanize(key), "value": _format_value(top_item.get(key)), "description": None})
    elif isinstance(result, dict):
        preferred = [
            "rows", "columns", "unique_orders", "total_revenue", "total_qty", "cancel_rate",
            "duplicate_rows", "missing_amount_rows", "overall_cancel_rate", "margin", "response_rate",
        ]
        for key in preferred:
            if key in result:
                evidence.append({"label": _humanize(key), "value": _format_value(result.get(key)), "description": None})
    if summary.get("row_count") is not None:
        evidence.append({"label": "Số dòng kết quả", "value": _format_value(summary.get("row_count")), "description": "Số dòng trong kết quả mà công cụ trả về."})
    if not evidence:
        evidence.append({"label": "Công cụ phân tích", "value": _humanize_tool_name(tool_name), "description": "Công cụ đã chạy thành công."})
    return evidence[:6]


def _takeaways(tool_name: str, label: str | None, metric: str | None, metric_value: Any, rows: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, str]]:
    takeaways = []
    if label:
        takeaways.append({
            "label": "Điểm nổi bật",
            "text": f"`{label}` là nhóm đáng chú ý nhất theo {_humanize(metric or 'metric')} ({_format_value(metric_value)}).",
            "tone": "positive",
        })
    if any(token in tool_name for token in ["risk", "cancel", "attrition", "target"]):
        takeaways.append({
            "label": "Rủi ro",
            "text": "Các nhóm có rate cao cần đọc cùng sample size để tránh kết luận quá sớm.",
            "tone": "risk",
        })
    if len(rows) > 1:
        takeaways.append({
            "label": "So sánh nhóm",
            "text": f"Kết quả có {len(rows)} nhóm/dòng, nên xem thêm nhóm đứng thứ hai và thứ ba trước khi ra quyết định.",
            "tone": "neutral",
        })
    if warnings:
        takeaways.append({
            "label": "Cảnh báo dữ liệu",
            "text": warnings[0],
            "tone": "warning",
        })
    return takeaways[:4] or [{"label": "Kết quả", "text": "Công cụ đã chạy thành công và có thể dùng cho bước phân tích tiếp theo.", "tone": "neutral"}]


def _why_it_matters(tool_name: str, domain: str) -> str:
    text = tool_name.lower()
    if any(token in text for token in ["cancel", "attrition", "risk", "target"]):
        return "Nhóm có rủi ro cao thường là nơi cần ưu tiên kiểm tra nguyên nhân, vì tác động của nó có thể làm sai lệch doanh thu, vận hành hoặc giữ chân nhân sự."
    if any(token in text for token in ["margin", "profit", "loss"]):
        return "Doanh thu cao chưa đủ; profit và margin cho biết nhóm nào thật sự tạo giá trị kinh doanh."
    if any(token in text for token in ["missing", "duplicate", "quality"]):
        return "Chất lượng dữ liệu quyết định độ tin cậy của dashboard, metric và mọi câu trả lời AI phía sau."
    if "chart" in text or "trend" in text or "time" in text or "month" in text:
        return "Xu hướng giúp phân biệt tăng trưởng thật với biến động ngắn hạn, từ đó chọn đúng thời điểm hoặc phân khúc để đào sâu."
    if domain == "marketing":
        return "Insight này giúp ưu tiên campaign, channel hoặc nhóm khách hàng có khả năng phản hồi tốt hơn."
    if domain == "hr":
        return "Insight này giúp xác định nhóm nhân sự cần quan tâm trước khi attrition hoặc chi phí nhân sự tăng cao."
    return "Insight này giúp bạn biết nên đào sâu vào nhóm nào trước thay vì đọc toàn bộ bảng dữ liệu thủ công."


def _recommended_questions(tool_name: str, label: str | None, metric: str | None, domain: str, question: str) -> list[str]:
    label_text = label or "nhóm này"
    if "cancel" in tool_name or "risk" in tool_name:
        return [f"Vì sao {label_text} có rủi ro cao?", f"{label_text} có revenue/profit như thế nào?", "Rủi ro này thay đổi theo thời gian không?"]
    if "attrition" in tool_name:
        return [f"{label_text} có liên quan đến overtime hoặc income band không?", "Department nào cần ưu tiên giữ chân nhân viên?", "Attrition thay đổi theo tenure như thế nào?"]
    if "missing" in tool_name:
        return ["Các cột missing nhiều ảnh hưởng metric chính ra sao?", "Có nên loại bỏ hay impute các cột này không?", "Dataset có duplicate hoặc outlier không?"]
    if "chart" in tool_name:
        return ["Insight nổi bật nhất từ biểu đồ này là gì?", "Có outlier hoặc anomaly trong biểu đồ không?", "Breakdown này thay đổi theo thời gian không?"]
    if domain == "retail":
        return [f"{label_text} có profit/margin tốt không?", f"{label_text} có bị ảnh hưởng bởi discount không?", "State hoặc segment nào kéo metric xuống?"]
    if domain == "marketing":
        return [f"{label_text} có response rate tốt không?", "Campaign nào hiệu quả nhất theo segment?", "Nhóm khách hàng nào nên ưu tiên tiếp cận?"]
    return [f"{label_text} thay đổi theo thời gian như thế nào?", f"{label_text} có rủi ro hoặc data quality issue không?", f"Breakdown {_humanize(metric or 'metric')} theo nhóm khác thì sao?"]


def _calculation_notes(tool_name: str, arguments: dict[str, Any], rows: list[dict[str, Any]], result: Any) -> list[str]:
    notes = [f"Kết quả được tính bằng công cụ deterministic `{_humanize_tool_name(tool_name)}`."]
    if arguments:
        notes.append(f"Tham số công cụ: {arguments}.")
    columns = list(rows[0].keys())[:8] if rows else list(result.keys())[:8] if isinstance(result, dict) else []
    if columns:
        notes.append(f"Các cột/field xuất hiện trong kết quả: {', '.join(map(str, columns))}.")
    if any(key in tool_name for key in ["breakdown", "category", "state", "city", "size", "sku"]):
        notes.append("Các nhóm được tổng hợp từ dữ liệu sau bước làm sạch/semantic mapping; không tự ý xóa duplicate order nếu dataset ở cấp line-item.")
    return notes


def _data_warnings(tool_name: str, result: Any, rows: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    output = [str(warning) for warning in warnings if warning]
    text = str(result).lower()
    if "missing" in text or "nan" in text or "none" in text:
        output.append("Kết quả có thể chịu ảnh hưởng bởi giá trị thiếu hoặc NaN trong dữ liệu.")
    for row in rows[:10]:
        if any(key in row for key in ["cancel_rate", "attrition_rate", "positive_rate"]) and any((row.get(key) in (None, "")) for key in ["orders", "rows"] if key in row):
            output.append("Một số rate cần đọc cùng sample size để tránh kết luận quá chắc.")
            break
    return list(dict.fromkeys(output))[:5]


def _confidence(rows: list[dict[str, Any]], result: Any, warnings: list[str]) -> str:
    if warnings:
        return "medium" if rows or result else "low"
    if rows and len(rows) >= 3:
        return "high"
    if isinstance(result, dict) and result:
        return "high"
    return "medium"


def _extract_rows(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [row for row in result if isinstance(row, dict)]
    if isinstance(result, dict):
        for key in ["items", "rows", "result"]:
            value = result.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if "tool_results" in result and isinstance(result["tool_results"], list):
            rows = []
            for item in result["tool_results"]:
                if isinstance(item, dict):
                    rows.extend(_extract_rows(item.get("result")))
            return rows
    return []


def _best_label(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    for key in ["sku", "category", "segment", "Segment", "size", "ship_state", "ship_city", "state", "city", "country", "order_month", "department", "job_role", "jobrole", "campaign", "channel", "fulfilment", "courier_status"]:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    for value in row.values():
        if isinstance(value, str) and value:
            return value
    return None


def _best_metric(row: dict[str, Any] | None) -> tuple[str | None, Any]:
    if not row:
        return None, None
    preferred = [
        "revenue", "sales", "profit", "margin", "amount", "total_revenue", "qty", "orders",
        "cancel_rate", "attrition_rate", "positive_rate", "response_rate", "missing_percent", "duplicate_rows",
    ]
    for key in preferred:
        if key in row and isinstance(row.get(key), (int, float)) and _is_present_metric(row.get(key)):
            return key, row.get(key)
    for key, value in row.items():
        if isinstance(value, (int, float)) and _is_present_metric(value):
            return key, value
    return None, None


def _is_present_metric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == value
    return False


def _is_weak_quality(result_quality: Any | None) -> bool:
    if result_quality is None:
        return False
    quality = _quality_dict(result_quality)
    status = quality.get("status")
    if status in {"empty", "insufficient", "tool_error"}:
        return True
    if status == "partial" and not (quality.get("has_metric") and quality.get("has_label")):
        return True
    return False


def _quality_dict(result_quality: Any) -> dict[str, Any]:
    if isinstance(result_quality, dict):
        return result_quality
    if hasattr(result_quality, "to_dict"):
        return result_quality.to_dict()
    return {
        key: getattr(result_quality, key)
        for key in [
            "status", "reason", "has_rows", "row_count", "has_metric", "metric_name",
            "metric_value", "has_label", "label", "render_mode", "warnings",
        ]
        if hasattr(result_quality, key)
    }


def _insufficient_next_questions(tool_name: str, question: str, arguments: dict[str, Any]) -> list[str]:
    if tool_name == "python_code_interpreter":
        return [
            "Hãy tổng quan dataset này trước.",
            "Metric chính bạn muốn phân tích là gì?",
            "Bạn muốn breakdown theo cột nào?",
        ]
    if "chart" in tool_name:
        return [
            "Hãy vẽ biểu đồ với một cột category và một cột numeric cụ thể.",
            "Cột nào có thể dùng làm metric chính?",
            "Hãy tổng quan dataset này trước.",
        ]
    return [
        "Hãy tổng quan dataset này trước.",
        "Cột nào thiếu dữ liệu nhiều nhất?",
        "Metric chính bạn muốn phân tích là gì?",
    ]


def _format_value(value: Any) -> str:
    if value is None:
        return "Không có dữ liệu"
    if isinstance(value, bool):
        return "Có" if value else "Không"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (abs(value) <= 1) and value != 0:
            return f"{value:.2%}"
        if abs(value) >= 1_000_000:
            return f"{value:,.0f}"
        if abs(value) >= 1_000:
            return f"{value:,.0f}"
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _humanize(value: str) -> str:
    normalized = value.replace(" ", "_").replace("-", "_").strip().lower()
    labels = {
        "metric": "chỉ số",
        "rows": "số dòng",
        "columns": "số cột",
        "unique_orders": "số đơn hàng duy nhất",
        "total_revenue": "tổng doanh thu",
        "revenue": "doanh thu",
        "sales": "doanh số",
        "profit": "lợi nhuận",
        "margin": "biên lợi nhuận",
        "amount": "giá trị",
        "total_qty": "tổng số lượng",
        "qty": "số lượng",
        "quantity": "số lượng",
        "orders": "số đơn hàng",
        "cancel_rate": "tỷ lệ hủy",
        "overall_cancel_rate": "tỷ lệ hủy tổng thể",
        "attrition_rate": "tỷ lệ nghỉ việc",
        "positive_rate": "tỷ lệ phản hồi",
        "response_rate": "tỷ lệ phản hồi",
        "missing_percent": "tỷ lệ thiếu dữ liệu",
        "missing_amount_rows": "số dòng thiếu amount",
        "duplicate_rows": "số dòng trùng lặp",
        "revenue_share": "tỷ trọng doanh thu",
        "tool_steps": "số bước phân tích",
        "chart_traces": "số lớp biểu đồ",
        "category": "nhóm sản phẩm",
        "segment": "phân khúc",
        "state": "bang/khu vực",
        "city": "thành phố",
        "country": "quốc gia",
        "department": "phòng ban",
        "job_role": "vai trò công việc",
        "campaign": "chiến dịch",
        "channel": "kênh",
        "sku": "SKU",
        "size": "kích cỡ",
        "order_month": "tháng đặt hàng",
        "fulfilment": "hình thức fulfilment",
        "courier_status": "trạng thái vận chuyển",
    }
    return labels.get(normalized, normalized.replace("_", " "))


def _humanize_tool_name(tool_name: str) -> str:
    labels = {
        "multi_step": "phân tích nhiều bước",
        "get_dataset_overview": "tổng quan dataset",
        "get_missing_values": "kiểm tra dữ liệu thiếu",
        "get_duplicate_rows": "kiểm tra dòng trùng lặp",
        "groupby_aggregate": "tổng hợp theo nhóm",
        "correlation_analysis": "phân tích tương quan",
        "semantic_overview": "tổng quan semantic",
        "semantic_kpis": "KPI semantic",
        "semantic_time_series": "xu hướng theo thời gian",
        "semantic_breakdown": "breakdown theo nhóm",
        "semantic_target_summary": "tóm tắt target/conversion",
        "get_sales_overview": "tổng quan bán hàng",
        "revenue_by_month": "doanh thu theo tháng",
        "revenue_by_category": "doanh thu theo category",
        "top_states_by_revenue": "top khu vực theo doanh thu",
        "top_skus_by_revenue": "top SKU theo doanh thu",
        "category_cancellation_summary": "rủi ro hủy theo category",
        "generate_chart_spec": "tạo biểu đồ",
        "python_code_interpreter": "công cụ Python sandbox",
    }
    return labels.get(tool_name, tool_name.replace("_", " "))


def _safe_tone(value: Any) -> str:
    return value if value in {"positive", "neutral", "warning", "risk"} else "neutral"
