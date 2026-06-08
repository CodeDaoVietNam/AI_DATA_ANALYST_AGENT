import pytest
import pandas as pd

from app.tools.ecommerce_tools import (
    b2b_summary,
    cancellation_summary,
    category_cancellation_summary,
    courier_summary,
    fulfilment_summary,
    get_data_quality_summary,
    get_sales_overview,
    promotion_summary,
    revenue_by_category,
    revenue_by_month,
    revenue_by_size,
    state_cancellation_summary,
    top_cities_by_revenue,
    top_skus_by_revenue,
    top_states_by_revenue,
)


def sample_sales_df():
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "date": pd.to_datetime(["2022-04-01", "2022-04-02", "2022-05-01", "2022-05-02"]),
        "order_month": ["2022-04", "2022-04", "2022-05", "2022-05"],
        "category": ["Set", "Set", "Kurta", "Kurta"],
        "sku": ["s1", "s2", "k1", "k1"],
        "size": ["M", "L", "M", "M"],
        "ship_state": ["A", "A", "B", "B"],
        "ship_city": ["Alpha", "Alpha", "Beta", "Beta"],
        "fulfilment": ["Amazon", "Merchant", "Amazon", "Merchant"],
        "courier_status": ["Shipped", None, "Cancelled", "Shipped"],
        "has_promotion": [True, False, False, True],
        "b2b": [False, False, False, True],
        "qty": [1, 2, 1, 1],
        "amount": [100.0, 200.0, None, 400.0],
        "revenue": [100.0, 200.0, None, 400.0],
        "is_cancelled": [False, True, False, False],
    })


def test_get_sales_overview():
    overview = get_sales_overview(sample_sales_df())

    assert overview["total_revenue"] == 700.0
    assert overview["missing_amount_rows"] == 1
    assert overview["unique_orders"] == 4
    assert overview["cancel_rate"] == 0.25
    assert overview["date_min"] == "2022-04-01"
    assert overview["date_max"] == "2022-05-02"


def test_get_data_quality_summary():
    quality = get_data_quality_summary(sample_sales_df())

    assert quality["duplicate_rows"] == 0
    assert quality["duplicate_order_id_rows"] == 0
    assert quality["missing_values"]["amount"] == 1
    assert quality["warnings"]


def test_revenue_by_month():
    result = revenue_by_month(sample_sales_df())

    by_month = {item["order_month"]: item for item in result}

    assert by_month["2022-04"]["revenue"] == 300.0
    assert by_month["2022-04"]["orders"] == 2
    assert by_month["2022-05"]["revenue"] == 400.0


def test_revenue_by_category():
    result = revenue_by_category(sample_sales_df())

    by_category = {item["category"]: item for item in result}

    assert by_category["Set"]["revenue"] == 300.0
    assert by_category["Kurta"]["revenue"] == 400.0
    assert by_category["Kurta"]["orders"] == 2


def test_top_states_by_revenue():
    result = top_states_by_revenue(sample_sales_df(), n=1)

    assert len(result) == 1
    assert result[0]["ship_state"] == "B"
    assert result[0]["revenue"] == 400.0


def test_top_states_by_revenue_validates_n():
    with pytest.raises(ValueError):
        top_states_by_revenue(sample_sales_df(), n=0)


def test_cancellation_summary():
    result = cancellation_summary(sample_sales_df())

    assert result["overall_cancel_rate"] == 0.25
    assert result["cancelled_rows"] == 1
    assert result["cancelled_orders"] == 1
    assert result["by_category"]
    assert result["by_fulfilment"]


def test_top_skus_by_revenue():
    result = top_skus_by_revenue(sample_sales_df(), n=2)

    assert result[0]["sku"] == "k1"
    assert result[0]["revenue"] == 400.0
    assert "category" in result[0]

    with pytest.raises(ValueError):
        top_skus_by_revenue(sample_sales_df(), n=0)


def test_revenue_by_size():
    result = revenue_by_size(sample_sales_df())
    by_size = {item["size"]: item for item in result}

    assert by_size["M"]["revenue"] == 500.0
    assert by_size["L"]["revenue"] == 200.0


def test_category_cancellation_summary():
    result = category_cancellation_summary(sample_sales_df())
    by_category = {item["category"]: item for item in result}

    assert by_category["Set"]["cancelled_rows"] == 1
    assert by_category["Set"]["cancel_rate"] == 0.5


def test_fulfilment_summary():
    result = fulfilment_summary(sample_sales_df())
    by_fulfilment = {item["fulfilment"]: item for item in result}

    assert by_fulfilment["Merchant"]["revenue"] == 600.0
    assert by_fulfilment["Amazon"]["orders"] == 2


def test_courier_summary_json_safe_missing_status():
    result = courier_summary(sample_sales_df())
    by_status = {item["courier_status"]: item for item in result}

    assert by_status[None]["rows"] == 1


def test_promotion_summary():
    result = promotion_summary(sample_sales_df())

    assert result["warning"]
    assert len(result["items"]) == 2


def test_b2b_summary():
    result = b2b_summary(sample_sales_df())

    assert result["warning"] is None
    assert len(result["items"]) == 2


def test_top_cities_by_revenue():
    result = top_cities_by_revenue(sample_sales_df(), n=1)

    assert result[0]["ship_city"] == "Beta"
    assert result[0]["revenue"] == 400.0


def test_state_cancellation_summary():
    result = state_cancellation_summary(sample_sales_df(), min_orders=2, n=1)

    assert len(result) == 1
    assert result[0]["ship_state"] == "A"
    assert result[0]["cancel_rate"] == 0.5
