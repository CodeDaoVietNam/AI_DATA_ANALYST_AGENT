import pandas as pd

from app.services.feature_engineering import add_amazon_sales_features


def test_add_amazon_sales_features_status_flags_and_amount_per_item():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2022-04-30", "2022-05-01"]),
        "status": ["Cancelled", "Shipped - Delivered to Buyer"],
        "promotion_ids": [None, "promo"],
        "amount": [100.0, 200.0],
        "qty": [0, 2],
    })

    result = add_amazon_sales_features(df)

    assert bool(result.loc[0, "is_cancelled"]) is True
    assert bool(result.loc[1, "is_shipped"]) is True
    assert bool(result.loc[1, "is_delivered"]) is True
    assert bool(result.loc[0, "has_promotion"]) is False
    assert bool(result.loc[1, "has_promotion"]) is True
    assert result.loc[1, "amount_per_item"] == 100.0
    assert pd.isna(result.loc[0, "amount_per_item"])


def test_add_amazon_sales_features_time_features():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2022-04-30", "2022-05-01"]),
        "status": ["Cancelled", "Shipped"],
        "amount": [100.0, 200.0],
        "qty": [1, 2],
    })

    result = add_amazon_sales_features(df)

    assert result.loc[0, "order_year"] == 2022
    assert result.loc[0, "order_month"] == "2022-04"
    assert result.loc[1, "order_month"] == "2022-05"
    assert "order_day_name" in result.columns


def test_add_amazon_sales_features_handles_missing_optional_columns():
    df = pd.DataFrame({"status": ["Cancelled"]})

    result = add_amazon_sales_features(df)

    assert bool(result.loc[0, "is_cancelled"]) is True
    assert bool(result.loc[0, "has_promotion"]) is False
    assert pd.isna(result.loc[0, "revenue"])
    assert pd.isna(result.loc[0, "amount_per_item"])
