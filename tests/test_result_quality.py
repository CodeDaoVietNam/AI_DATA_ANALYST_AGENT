from __future__ import annotations

from app.services.result_quality import assess_result_quality


def test_empty_result_quality():
    quality = assess_result_quality(
        tool_name="python_code_interpreter",
        result=None,
        result_summary={"row_count": None, "primary_metric": None, "primary_metric_value": None},
    )

    assert quality.status == "empty"
    assert quality.render_mode == "insufficient_result"
    assert quality.has_metric is False


def test_dict_without_metric_is_insufficient():
    quality = assess_result_quality(
        tool_name="python_code_interpreter",
        result={"message": "done"},
        result_summary={"row_count": None, "primary_metric": None, "primary_metric_value": None},
    )

    assert quality.status == "insufficient"
    assert quality.has_metric is False


def test_list_rows_with_label_and_metric_is_strong():
    quality = assess_result_quality(
        tool_name="semantic_breakdown",
        result=[{"category": "Set", "revenue": 100.0}],
        result_summary={
            "row_count": 1,
            "top_item": {"category": "Set", "revenue": 100.0},
            "primary_metric": "revenue",
            "primary_metric_value": 100.0,
        },
    )

    assert quality.status == "strong"
    assert quality.label == "Set"
    assert quality.metric_name == "revenue"


def test_python_interpreter_empty_payload_is_empty():
    quality = assess_result_quality(
        tool_name="python_code_interpreter",
        result={"success": True, "result_type": "empty", "result": None, "warnings": ["No result"]},
        result_summary={"row_count": 0, "primary_metric": None, "primary_metric_value": None},
    )

    assert quality.status == "empty"
    assert quality.warnings
