import json
from typing import Dict, Any, Optional

import pandas as pd
import plotly.express as px


def generate_chart_spec(df: pd.DataFrame, chart_type: str, x: str, y: Optional[str] = None) -> Dict[str, Any]:
    validate_column(df, x)
    if y:
        validate_column(df, y)

    if chart_type == "bar":
        if y is None:
            data = df[x].value_counts().head(20).reset_index()
            data.columns = [x, "count"]
            fig = px.bar(data, x=x, y="count", title=f"Count of {x}")
        else:
            data = df.groupby(x, dropna=False)[y].sum().sort_values(ascending=False).head(20).reset_index()
            fig = px.bar(data, x=x, y=y, title=f"{y} by {x}")

    elif chart_type == "line":
        if y is None:
            raise ValueError("Line chart requires y column.")
        temp = df.copy()
        temp[x] = pd.to_datetime(temp[x], errors="coerce")
        temp = temp.dropna(subset=[x])
        data = temp.groupby(temp[x].dt.to_period("M").astype(str))[y].sum().reset_index()
        data.columns = [x, y]
        fig = px.line(data, x=x, y=y, markers=True, title=f"{y} trend by {x}")

    elif chart_type == "scatter":
        if y is None:
            raise ValueError("Scatter chart requires y column.")
        fig = px.scatter(df, x=x, y=y, title=f"{x} vs {y}")

    elif chart_type == "histogram":
        fig = px.histogram(df, x=x, title=f"Distribution of {x}")

    elif chart_type == "box":
        fig = px.box(df, y=x, title=f"Boxplot of {x}")

    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    return json.loads(fig.to_json())


def validate_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")
