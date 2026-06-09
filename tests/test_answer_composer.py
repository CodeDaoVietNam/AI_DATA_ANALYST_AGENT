from __future__ import annotations

from app.services.answer_composer import answer_card_to_text, compose_answer_card, compose_tool_error_card, merge_llm_answer_card
from app.services.result_quality import assess_result_quality


def test_compose_answer_card_for_breakdown_result():
    result = [
        {"category": "Set", "revenue": 392041.0, "orders": 120, "cancel_rate": 0.12},
        {"category": "Kurta", "revenue": 120000.0, "orders": 80, "cancel_rate": 0.05},
    ]

    card = compose_answer_card(
        question="Category nào doanh thu cao nhất?",
        tool_name="revenue_by_category",
        arguments={},
        result=result,
        result_summary={
            "row_count": 2,
            "top_item": result[0],
            "primary_metric": "revenue",
            "primary_metric_value": 392041.0,
            "has_chart": False,
            "result_type": "list",
        },
    )

    assert "Set" in card["headline"]
    assert card["evidence"]
    assert card["recommended_next_questions"]
    assert card["answer_source"] == "deterministic_composer"


def test_answer_card_to_text_is_readable_vietnamese():
    card = compose_answer_card(
        question="Tổng quan dataset?",
        tool_name="get_dataset_overview",
        arguments={},
        result={"rows": 100, "columns": 8, "duplicate_rows": 2},
        result_summary={"row_count": None, "top_item": None, "primary_metric": "rows", "primary_metric_value": 100, "has_chart": False, "result_type": "dict"},
    )

    text = answer_card_to_text(card)

    assert "Bằng chứng" in text
    assert "Vì sao quan trọng" in text
    assert "Nên hỏi tiếp" in text


def test_merge_llm_answer_card_preserves_evidence():
    base = compose_answer_card(
        question="SKU nào cao nhất?",
        tool_name="top_skus_by_revenue",
        arguments={},
        result=[{"sku": "SKU-A", "revenue": 1000.0}],
        result_summary={"row_count": 1, "top_item": {"sku": "SKU-A", "revenue": 1000.0}, "primary_metric": "revenue", "primary_metric_value": 1000.0, "has_chart": False, "result_type": "list"},
    )
    llm = {
        "headline": "SKU-A là SKU nổi bật nhất về doanh thu.",
        "summary": "SKU-A đang dẫn đầu rõ rệt.",
        "evidence": [{"label": "Fake", "value": "999999"}],
        "why_it_matters": "SKU dẫn đầu ảnh hưởng trực tiếp đến doanh thu.",
        "recommended_next_questions": ["SKU-A có cancel rate cao không?"],
    }

    merged = merge_llm_answer_card(base, llm)

    assert merged["headline"] == "SKU-A là SKU nổi bật nhất về doanh thu."
    assert merged["evidence"] == base["evidence"]
    assert merged["answer_source"] == "llm_structured"


def test_tool_error_card_contains_error_warning():
    card = compose_tool_error_card("semantic_breakdown", {"by_role": "category"}, "Missing required role")

    assert card["answer_source"] == "tool_error"
    assert card["data_warnings"] == ["Missing required role"]
    assert "chưa chạy được" in card["headline"].lower()


def test_compose_answer_card_for_insufficient_result_does_not_fake_metric():
    result = {"success": True, "result_type": "empty", "result": None, "warnings": ["No result"]}
    summary = {
        "row_count": 0,
        "top_item": None,
        "primary_metric": None,
        "primary_metric_value": None,
        "has_chart": False,
        "result_type": "python_empty",
    }
    quality = assess_result_quality(
        tool_name="python_code_interpreter",
        result=result,
        result_summary=summary,
    )

    card = compose_answer_card(
        question="Phân tích thử bằng Python",
        tool_name="python_code_interpreter",
        arguments={"code": "x = 1"},
        result=result,
        result_summary=summary,
        result_quality=quality,
    )
    text = answer_card_to_text(card)

    assert card["confidence"] == "low"
    assert "chưa đủ dữ liệu" in card["headline"].lower()
    assert "chỉ số = Không có dữ liệu" not in text
    assert "metric = None" not in text
