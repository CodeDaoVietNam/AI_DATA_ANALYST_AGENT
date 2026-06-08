from typing import Dict, Any, List
import pandas as pd
import numpy as np


DATE_LIKE_COLUMN_HINTS = ("date", "time", "day", "month", "year", "created", "updated")
COMMON_DATE_FORMATS = ("%Y-%m-%d", "%m-%d-%y", "%m/%d/%y", "%m-%d-%Y", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y")


def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    column_types = {}

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_numeric_dtype(series):
            column_types[col] = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            column_types[col] = "datetime"
        else:
            if is_datetime_like_column(col, series):
                column_types[col] = "datetime"
            elif is_categorical_like(series):
                column_types[col] = "categorical"
            else:
                column_types[col] = "text"

    return column_types


def is_datetime_like_column(column: str, series: pd.Series) -> bool:
    if not _has_date_like_name(column):
        return False

    sample = series.dropna().astype(str).str.strip()
    if sample.empty:
        return False

    sample = sample.head(100)
    if not sample.str.contains(r"[-/]", regex=True).mean() > 0.8:
        return False

    for date_format in COMMON_DATE_FORMATS:
        parsed = pd.to_datetime(sample, format=date_format, errors="coerce")
        if parsed.notna().mean() > 0.8:
            return True

    return False


def is_categorical_like(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False

    unique_count = non_null.nunique(dropna=True)
    unique_ratio = unique_count / max(len(non_null), 1)
    return unique_count <= 50 or unique_ratio <= 0.3


def _has_date_like_name(column: str) -> bool:
    lowered = column.lower()
    return any(hint in lowered for hint in DATE_LIKE_COLUMN_HINTS)


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    column_types = infer_column_types(df)

    numeric_cols = [col for col, typ in column_types.items() if typ == "numeric"]
    categorical_cols = [col for col, typ in column_types.items() if typ == "categorical"]

    numeric_summary = {}
    if numeric_cols:
        numeric_summary = (
            df[numeric_cols]
            .describe()
            .replace({np.nan: None})
            .to_dict()
        )

    categorical_summary = {}
    for col in categorical_cols:
        categorical_summary[col] = {
            "unique_values": int(df[col].nunique(dropna=True)),
            "top_values": json_safe_value_counts(df[col])
        }

    recommendations = recommend_analysis(df, column_types)

    return {
        "shape": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1])
        },
        "columns": list(df.columns),
        "column_types": column_types,
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "missing_percent": (df.isna().mean() * 100).round(2).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "recommendations": recommendations
    }


def json_safe_value_counts(series: pd.Series, limit: int = 5) -> Dict[str, int]:
    counts = series.value_counts(dropna=False).head(limit)
    result = {}
    for value, count in counts.items():
        if pd.isna(value):
            key = "<missing>"
        else:
            key = str(value)
        result[key] = int(count)
    return result


def recommend_analysis(df: pd.DataFrame, column_types: Dict[str, str]) -> List[str]:
    numeric_cols = [c for c, t in column_types.items() if t == "numeric"]
    categorical_cols = [c for c, t in column_types.items() if t == "categorical"]
    datetime_cols = [c for c, t in column_types.items() if t == "datetime"]

    recs = []

    if datetime_cols and numeric_cols:
        recs.append(f"Analyze trend over time using {datetime_cols[0]} and {numeric_cols[0]}.")

    if categorical_cols and numeric_cols:
        recs.append(f"Compare {numeric_cols[0]} by {categorical_cols[0]} using a bar chart.")

    if len(numeric_cols) >= 2:
        recs.append("Check correlation between numeric columns.")

    high_missing = [
        col for col in df.columns
        if df[col].isna().mean() > 0.2
    ]
    if high_missing:
        recs.append(f"Review high-missing columns: {', '.join(high_missing)}.")

    if not recs:
        recs.append("Start with general dataset summary and missing-value analysis.")

    return recs
