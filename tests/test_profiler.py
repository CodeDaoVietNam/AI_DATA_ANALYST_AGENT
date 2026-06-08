import pandas as pd
import json
from app.services.profiler import profile_dataframe


def test_profile_dataframe_basic():
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Revenue": [100, 200],
        "Category": ["A", "B"]
    })

    summary = profile_dataframe(df)

    assert summary["shape"]["rows"] == 2
    assert summary["shape"]["columns"] == 3
    assert "Revenue" in summary["column_types"]
    assert summary["missing_values"]["Revenue"] == 0


def test_profile_dataframe_infers_dates_without_text_warning():
    df = pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "Name": ["Alice", "Bob", "Charlie"],
        "Segment": ["A", "A", "B"],
        "Revenue": [100, 200, 300],
    })

    summary = profile_dataframe(df)

    assert summary["column_types"]["Order Date"] == "datetime"
    assert summary["column_types"]["Name"] == "categorical"
    assert summary["column_types"]["Segment"] == "categorical"


def test_profile_dataframe_is_json_safe_with_missing_categorical_values():
    df = pd.DataFrame({
        "Status": ["Shipped", None, "Cancelled"],
        "Revenue": [100.0, 200.0, 300.0],
    })

    summary = profile_dataframe(df)

    assert "<missing>" in summary["categorical_summary"]["Status"]["top_values"]
    json.dumps(summary, allow_nan=False)
