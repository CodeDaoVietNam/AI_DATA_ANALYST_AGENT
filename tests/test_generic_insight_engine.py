import pandas as pd

from app.services.generic_insight_engine import (
    detect_correlation_insights,
    detect_data_quality_insights,
    detect_outlier_insights,
    detect_top_contributor_insights,
    detect_trend_insights,
    generate_generic_insights,
)
from app.services.semantic_mapper import build_semantic_profile


def test_missing_value_insight_when_null_percent_high():
    df = pd.DataFrame({"A": [1, None, None], "B": ["x", "y", "z"]})

    insights = detect_data_quality_insights(df)

    assert any(item["type"] == "data_quality" and item["severity"] == "warning" for item in insights)


def test_top_contributor_insight_uses_semantic_metric_and_dimension():
    df = pd.DataFrame({
        "Sales": [100.0, 200.0, 50.0],
        "Category": ["A", "B", "A"],
    })
    profile = build_semantic_profile(df)

    insights = detect_top_contributor_insights(df, profile, [])

    assert insights
    assert insights[0]["type"] == "top_contributor"
    assert "`B`" in insights[0]["finding"]


def test_trend_insight_detects_growth():
    df = pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "Sales": [100.0, 150.0, 300.0],
        "Category": ["A", "A", "A"],
    })
    profile = build_semantic_profile(df)

    insights = detect_trend_insights(df, profile, [])

    assert insights
    assert insights[0]["type"] == "trend"
    assert "increased" in insights[0]["finding"]


def test_outlier_insight_detects_iqr_outlier():
    df = pd.DataFrame({"value": [1, 2, 2, 2, 3, 100]})

    insights = detect_outlier_insights(df)

    assert insights
    assert insights[0]["type"] == "outlier"


def test_correlation_insight_detects_strong_relationship():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8], "c": [8, 7, 6, 5]})

    insights = detect_correlation_insights(df)

    assert insights
    assert insights[0]["type"] == "correlation"


def test_generic_insight_engine_does_not_crash_on_all_text_or_small_dataset():
    text_df = pd.DataFrame({"name": ["a", "b"], "kind": ["x", "y"]})
    tiny_df = pd.DataFrame({"only": ["x"]})

    assert isinstance(generate_generic_insights(text_df, build_semantic_profile(text_df)), list)
    assert isinstance(generate_generic_insights(tiny_df, build_semantic_profile(tiny_df)), list)
