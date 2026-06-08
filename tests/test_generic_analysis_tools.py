import pytest
import pandas as pd

from app.tools.generic_analysis_tools import (
    correlation_analysis,
    get_dataset_overview,
    get_duplicate_rows,
    get_missing_values,
    groupby_aggregate,
)


def sample_df():
    return pd.DataFrame({
        "Category": ["A", "A", "B", "B", "B"],
        "Revenue": [10, 20, 30, 40, None],
        "Orders": [1, 2, 3, 4, 5],
        "Text": ["x", "y", "z", "z", "z"],
    })


def test_get_dataset_overview():
    overview = get_dataset_overview(sample_df())

    assert overview["rows"] == 5
    assert overview["columns"] == 4
    assert "Revenue" in overview["numeric_columns"]


def test_get_missing_values_and_duplicates():
    df = sample_df()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)

    missing = get_missing_values(df)
    duplicates = get_duplicate_rows(df)

    assert missing["missing_values"]["Revenue"] == 1
    assert "Revenue" in missing["columns_with_missing"]
    assert duplicates["duplicate_rows"] == 1


def test_groupby_aggregate_sum_mean_count():
    df = sample_df()

    summed = groupby_aggregate(df, "Category", "Revenue", "sum")
    counted = groupby_aggregate(df, "Category", "Revenue", "count")
    meaned = groupby_aggregate(df, "Category", "Orders", "mean")

    assert {row["Category"]: row["sum_Revenue"] for row in summed} == {"B": 70.0, "A": 30.0}
    assert {row["Category"]: row["count_Revenue"] for row in counted} == {"B": 2, "A": 2}
    assert {row["Category"]: row["mean_Orders"] for row in meaned}["B"] == 4.0


def test_groupby_aggregate_validation():
    with pytest.raises(ValueError):
        groupby_aggregate(sample_df(), "Missing", "Revenue", "sum")

    with pytest.raises(ValueError):
        groupby_aggregate(sample_df(), "Category", "Revenue", "invalid")

    with pytest.raises(ValueError):
        groupby_aggregate(sample_df(), "Category", "Text", "sum")


def test_correlation_analysis_numeric_columns_only():
    result = correlation_analysis(sample_df())

    assert set(result["columns"]) == {"Revenue", "Orders"}
    assert result["correlations"]


from app.tools.generic_analysis_tools import (
    compare_segments,
    detect_outliers,
    trend_analysis,
    period_over_period_change,
    top_bottom_contributors,
    pareto_analysis,
    cohort_summary,
    anomaly_detection,
    forecast_next_period,
    explain_metric_change,
)

def test_compare_segments():
    df = pd.DataFrame({
        "Group": ["A", "A", "B", "B"],
        "Val": [10, 20, 30, 40],
    })
    res = compare_segments(df, "Group", "A", "B", "Val", "mean")
    assert res["value_a"] == 15.0
    assert res["value_b"] == 35.0
    assert res["percentage_difference"] == -57.14

def test_detect_outliers():
    df = pd.DataFrame({
        "Val": [1, 2, 3, 4, 100],  # 100 should be detected
    })
    res = detect_outliers(df, "Val", "iqr")
    assert res["outliers_count"] == 1
    assert res["outlier_sample"][0]["Val"] == 100

def test_trend_analysis():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01", "2026-03-01"],
        "Val": [100, 110, 121],
    })
    res = trend_analysis(df, "Date", "Val", "M", "sum")
    assert len(res["trend_records"]) == 3
    assert res["average_growth_rate"] == 10.0

def test_period_over_period_change():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-15"],
        "Val": [10, 20, 30, 40],
    })
    res = period_over_period_change(df, "Date", "Val", "2026-02-01", "2026-02-28", "2026-01-01", "2026-01-31", "sum")
    assert res["period_a"]["value"] == 70.0
    assert res["period_b"]["value"] == 30.0
    assert res["percentage_difference"] == 133.33

def test_top_bottom_contributors():
    df = pd.DataFrame({
        "Category": ["Apple", "Banana", "Cherry"],
        "Sales": [100, 50, 10],
    })
    res = top_bottom_contributors(df, "Category", "Sales", 2)
    assert res["top_contributors"][0]["Category"] == "Apple"
    assert res["bottom_contributors"][0]["Category"] == "Cherry"

def test_pareto_analysis():
    df = pd.DataFrame({
        "Category": ["A", "B", "C", "D", "E"],
        "Sales": [80, 10, 5, 3, 2],  # Total = 100, 'A' contributes 80%
    })
    res = pareto_analysis(df, "Category", "Sales")
    assert res["contributors_count"] == 1
    assert res["contributors"][0]["Category"] == "A"

def test_cohort_summary():
    df = pd.DataFrame({
        "CohortDate": ["2026-01-01", "2026-01-01", "2026-02-01"],
        "ActivityDate": ["2026-01-15", "2026-02-15", "2026-02-15"],
        "UserId": ["U1", "U1", "U2"],
    })
    res = cohort_summary(df, "CohortDate", "ActivityDate", "UserId")
    assert len(res) > 0

def test_anomaly_detection():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"],
        "Val": [10, 11, 12, 100, 10],  # 100 is anomaly
    })
    res = anomaly_detection(df, "Date", "Val", "M", threshold=1.0)
    assert res["anomalies_count"] == 1

def test_forecast_next_period():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01", "2026-03-01"],
        "Val": [100, 110, 120],
    })
    res = forecast_next_period(df, "Date", "Val", 2)
    assert len(res["forecasts"]) == 2

def test_explain_metric_change():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01"],
        "Val": [100, 150],
        "Dim": ["X", "X"],
    })
    res = explain_metric_change(df, "Date", "Val", "Dim", "2026-02-01", "2026-02-28", "2026-01-01", "2026-01-31", "sum")
    assert res["absolute_change"] == 50.0

