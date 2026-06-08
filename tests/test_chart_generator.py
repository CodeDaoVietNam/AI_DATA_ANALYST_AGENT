import json

import pytest
import pandas as pd

from app.services.chart_generator import generate_chart_spec


def sample_df():
    return pd.DataFrame({
        "Date": ["2024-01-01", "2024-02-01", "2024-02-15"],
        "Category": ["A", "A", "B"],
        "Revenue": [100, 200, 300],
        "Orders": [1, 2, 3],
    })


def test_generate_bar_chart_spec():
    chart = generate_chart_spec(sample_df(), "bar", "Category", "Revenue")

    assert "data" in chart
    assert "layout" in chart
    json.dumps(chart)


def test_generate_line_chart_requires_y():
    with pytest.raises(ValueError):
        generate_chart_spec(sample_df(), "line", "Date")


def test_generate_chart_validates_column():
    with pytest.raises(ValueError):
        generate_chart_spec(sample_df(), "bar", "Missing")
