from __future__ import annotations

import pandas as pd

from app.services.data_cleaner import clean_amazon_sales_data
from app.services.feature_engineering import add_amazon_sales_features


def prepare_amazon_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = clean_amazon_sales_data(df)
    return add_amazon_sales_features(cleaned)
