import math

import pandas as pd
import pytest

from app.services.metric_builder import (
    evaluate_metric,
    evaluate_metric_summary,
    metric_breakdown,
    validate_metric_definition,
)
from app.services.semantic_mapper import build_semantic_profile


def test_metric_profit_divided_by_revenue_uses_roles():
    df = pd.DataFrame({
        "Sales": [100.0, 200.0],
        "Profit": [10.0, 50.0],
        "Category": ["A", "B"],
    })
    profile = build_semantic_profile(df)
    metric = {
        "name": "margin",
        "label": "Margin",
        "expression": "profit / revenue",
        "format": "percent",
        "aggregation": "mean",
        "required_roles": ["profit", "revenue"],
    }

    summary = evaluate_metric_summary(df, profile, metric)

    assert summary["value"] == pytest.approx(0.175)
    assert summary["format"] == "percent"


def test_metric_divide_by_zero_returns_controlled_nan():
    df = pd.DataFrame({"revenue": [100.0, 0.0], "profit": [10.0, 5.0]})
    profile = build_semantic_profile(df)
    metric = {"name": "margin", "expression": "profit / revenue", "aggregation": "mean"}

    result = evaluate_metric(df, profile, metric)

    assert result.iloc[0] == pytest.approx(0.1)
    assert math.isnan(result.iloc[1])


def test_metric_expression_can_use_column_names():
    df = pd.DataFrame({"Sales": [100.0, 200.0], "Visits": [10.0, 20.0]})
    profile = build_semantic_profile(df)
    metric = {"name": "sales_per_visit", "expression": "Sales / Visits", "aggregation": "mean"}

    summary = evaluate_metric_summary(df, profile, metric)

    assert summary["value"] == pytest.approx(10.0)


def test_metric_rejects_unsafe_expression():
    df = pd.DataFrame({"Sales": [100.0], "Profit": [10.0]})
    profile = build_semantic_profile(df)
    metric = {"name": "bad", "expression": "__import__('os').system('echo nope')"}

    with pytest.raises(ValueError):
        validate_metric_definition(metric, df, profile)


def test_metric_breakdown_by_role():
    df = pd.DataFrame({
        "Sales": [100.0, 200.0, 300.0],
        "Profit": [10.0, 40.0, 30.0],
        "Category": ["A", "A", "B"],
    })
    profile = build_semantic_profile(df)
    metric = {"name": "margin", "expression": "profit / revenue", "format": "percent", "aggregation": "mean"}

    rows = metric_breakdown(df, profile, metric, by_role="category")

    assert rows[0]["Category"] == "A"
    assert rows[0]["margin"] == pytest.approx(0.15)
