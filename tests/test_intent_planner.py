import pandas as pd

from app.services.intent_planner import compile_intent_to_plan, parse_universal_intent
from app.services.semantic_mapper import build_semantic_profile


def _retail_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "Sales": [100.0, 200.0, 300.0],
        "Profit": [10.0, 50.0, 30.0],
        "Category": ["A", "B", "A"],
        "Segment": ["Consumer", "Corporate", "Consumer"],
    })


def test_parse_custom_metric_breakdown_intent():
    df = _retail_df()
    profile = build_semantic_profile(df)
    custom_metrics = [{"name": "margin", "label": "Margin", "expression": "profit / revenue"}]

    intent = parse_universal_intent("margin theo category như thế nào?", df, profile, custom_metrics)

    assert intent.task == "breakdown"
    assert intent.metric == "margin"
    assert intent.metric_source == "custom_metric"
    assert intent.dimension == "category"
    assert intent.confidence >= 0.7


def test_compile_custom_metric_breakdown_plan():
    df = _retail_df()
    profile = build_semantic_profile(df)
    custom_metrics = [{"name": "margin", "label": "Margin", "expression": "profit / revenue"}]
    intent = parse_universal_intent("margin theo category như thế nào?", df, profile, custom_metrics)

    plan = compile_intent_to_plan(intent, df, profile, custom_metrics)

    assert plan is not None
    assert plan["strategy"] == "intent:breakdown"
    assert plan["steps"][0]["tool_name"] == "custom_metric_breakdown"
    assert plan["steps"][0]["arguments"]["metric_name"] == "margin"
    assert plan["intent"]["metric_source"] == "custom_metric"


def test_parse_semantic_revenue_breakdown_intent():
    df = _retail_df()
    profile = build_semantic_profile(df)

    intent = parse_universal_intent("doanh thu theo category", df, profile, [])
    plan = compile_intent_to_plan(intent, df, profile, [])

    assert intent.task == "breakdown"
    assert intent.metric == "revenue"
    assert intent.dimension == "category"
    assert plan is not None
    assert plan["steps"][0]["tool_name"] == "semantic_breakdown"


def test_parse_trend_intent():
    df = _retail_df()
    profile = build_semantic_profile(df)

    intent = parse_universal_intent("doanh thu theo tháng", df, profile, [])
    plan = compile_intent_to_plan(intent, df, profile, [])

    assert intent.task == "trend"
    assert intent.metric == "revenue"
    assert intent.time_grain == "month"
    assert plan is not None
    assert plan["steps"][0]["tool_name"] == "semantic_time_series"


def test_parse_data_quality_and_correlation_intents():
    df = _retail_df()
    profile = build_semantic_profile(df)

    missing = parse_universal_intent("cột nào thiếu dữ liệu?", df, profile, [])
    correlation = parse_universal_intent("tương quan giữa các cột numeric", df, profile, [])

    assert missing.task == "data_quality"
    assert correlation.task == "correlation"


def test_top_limit_is_carried_to_plan():
    df = _retail_df()
    profile = build_semantic_profile(df)

    intent = parse_universal_intent("top 5 category theo revenue", df, profile, [])
    plan = compile_intent_to_plan(intent, df, profile, [])

    assert intent.limit == 5
    assert plan is not None
    assert plan["steps"][0]["arguments"].get("limit") == 5
