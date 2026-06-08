from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.services.metric_builder import evaluate_metric, normalize_metric_definition


def generate_generic_insights(
    df: pd.DataFrame,
    profile,
    metrics: list[dict[str, Any]] | None = None,
    max_insights: int = 10,
) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    metrics = metrics or []
    detectors = [
        detect_data_quality_insights(df),
        detect_top_contributor_insights(df, profile, metrics),
        detect_trend_insights(df, profile, metrics),
        detect_outlier_insights(df),
        detect_segment_insights(df, profile, metrics),
        detect_correlation_insights(df),
        detect_pareto_insights(df, profile, metrics),
        detect_target_insights(df, profile),
    ]
    for group in detectors:
        insights.extend(group)
        if len(insights) >= max_insights:
            break
    return insights[:max_insights]


def detect_data_quality_insights(df: pd.DataFrame) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    row_count = max(int(len(df)), 1)
    missing_pct = df.isna().mean().sort_values(ascending=False)
    high_missing = [(column, pct) for column, pct in missing_pct.items() if pct >= 0.2]
    if high_missing:
        column, pct = high_missing[0]
        insights.append(_insight(
            "data_quality",
            "High Missing Values",
            f"`{column}` has a high missing-value rate.",
            f"Missing percent = {pct * 100:.2f}%.",
            "Metrics using this field may be biased or incomplete.",
            f"Cột `{column}` thiếu dữ liệu do nguyên nhân gì?",
            severity="warning",
            tone="risk",
            confidence=0.9,
            dimension=str(column),
            related_table_id="generic_missing",
        ))

    duplicates = int(df.duplicated().sum())
    if duplicates:
        insights.append(_insight(
            "data_quality",
            "Duplicate Rows Detected",
            f"Dataset contains {duplicates} exact duplicate rows.",
            f"Duplicate rate = {duplicates / row_count * 100:.2f}%.",
            "Duplicates can inflate totals and distort group comparisons.",
            "Các dòng trùng này có nên được loại bỏ trước khi phân tích không?",
            severity="warning",
            tone="risk",
            confidence=0.86,
            related_table_id="generic_missing",
        ))

    constant_columns = [
        column for column in df.columns
        if df[column].nunique(dropna=True) <= 1 and len(df[column].dropna()) > 0
    ]
    if constant_columns:
        sample = constant_columns[:5]
        insights.append(_insight(
            "data_quality",
            "Constant Columns",
            f"{len(constant_columns)} columns have a single repeated value.",
            f"Examples: {', '.join(map(str, sample))}.",
            "Constant fields rarely help segmentation or modeling and may be metadata noise.",
            "Có nên loại các cột constant khỏi dashboard không?",
            severity="info",
            tone="neutral",
            confidence=0.8,
        ))
    return insights


def detect_top_contributor_insights(df: pd.DataFrame, profile, metrics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    metric_name, series = _preferred_metric_series(df, profile, metrics)
    dimension_name, dimension = _preferred_dimension_series(df, profile)
    if metric_name is None or series is None or dimension_name is None or dimension is None:
        return []
    if series.dropna().empty:
        return []

    temp = pd.DataFrame({"dimension": dimension, "metric": pd.to_numeric(series, errors="coerce")}).dropna(subset=["metric"])
    if temp.empty:
        return []
    grouped = temp.groupby("dimension", dropna=False)["metric"].sum().sort_values(ascending=False)
    if grouped.empty:
        return []
    top_label = str(grouped.index[0])
    top_value = float(grouped.iloc[0])
    total = float(grouped.sum())
    share = top_value / total if total else None
    return [_insight(
        "top_contributor",
        f"Top {metric_name} Contributor",
        f"`{top_label}` contributes the most {metric_name}.",
        f"{metric_name} = {_fmt(top_value)}" + (f", share = {share * 100:.2f}%." if share is not None else "."),
        "Top contributors show where business value or operational volume is concentrated.",
        f"{metric_name} của `{top_label}` có bền vững theo thời gian không?",
        tone="positive",
        severity="info",
        confidence=0.84,
        metric=metric_name,
        dimension=dimension_name,
        related_chart_id=f"chart_{metric_name}_by_{dimension_name}",
        related_table_id=f"table_{metric_name}_by_{dimension_name}",
    )]


def detect_trend_insights(df: pd.DataFrame, profile, metrics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    date_column = _role_column(profile, "date") or _first_date_like_column(df)
    metric_name, series = _preferred_metric_series(df, profile, metrics)
    if not date_column or metric_name is None or series is None:
        return []
    temp = pd.DataFrame({
        "date": pd.to_datetime(df[date_column], errors="coerce"),
        "metric": pd.to_numeric(series, errors="coerce"),
    }).dropna()
    if temp.empty:
        return []
    grouped = temp.groupby(temp["date"].dt.to_period("M").astype(str))["metric"].sum().sort_index()
    if len(grouped) < 2:
        return []
    first = float(grouped.iloc[0])
    last = float(grouped.iloc[-1])
    change = last - first
    pct = change / abs(first) if first else None
    direction = "increased" if change >= 0 else "declined"
    return [_insight(
        "trend",
        f"{metric_name.title()} Trend",
        f"{metric_name} {direction} from the first to the latest period.",
        f"First period = {_fmt(first)}, latest period = {_fmt(last)}" + (f", change = {pct * 100:.2f}%." if pct is not None else "."),
        "Trend direction helps separate one-time spikes from sustained movement.",
        f"Yếu tố nào đóng góp nhiều nhất vào biến động {metric_name} này?",
        tone="positive" if change >= 0 else "risk",
        severity="info" if change >= 0 else "warning",
        confidence=0.78,
        metric=metric_name,
        dimension="date",
        related_chart_id="semantic_trend_chart",
        related_table_id="semantic_trend",
    )]


def detect_outlier_insights(df: pd.DataFrame) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    for column in _numeric_columns(df)[:5]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = int(((series < lower) | (series > upper)).sum())
        if outliers:
            insights.append(_insight(
                "outlier",
                f"Outliers in {column}",
                f"`{column}` contains {outliers} IQR outliers.",
                f"Bounds: {_fmt(lower)} to {_fmt(upper)}.",
                "Outliers may represent true exceptional cases or data quality issues.",
                f"Các outlier của `{column}` thuộc nhóm nào?",
                severity="warning",
                tone="risk",
                confidence=0.76,
                metric=str(column),
            ))
            break
    return insights


def detect_segment_insights(df: pd.DataFrame, profile, metrics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    metric_name, series = _preferred_metric_series(df, profile, metrics)
    dimension_name, dimension = _preferred_dimension_series(df, profile)
    if metric_name is None or series is None or dimension_name is None or dimension is None:
        return []
    temp = pd.DataFrame({"dimension": dimension, "metric": pd.to_numeric(series, errors="coerce")}).dropna(subset=["metric"])
    grouped = temp.groupby("dimension", dropna=False)["metric"].mean().sort_values(ascending=False)
    if len(grouped) < 2:
        return []
    top_label = str(grouped.index[0])
    bottom_label = str(grouped.index[-1])
    top_value = float(grouped.iloc[0])
    bottom_value = float(grouped.iloc[-1])
    gap = top_value - bottom_value
    if gap == 0:
        return []
    return [_insight(
        "segment_difference",
        f"{metric_name.title()} Segment Gap",
        f"`{top_label}` is above `{bottom_label}` on average {metric_name}.",
        f"Top mean = {_fmt(top_value)}, bottom mean = {_fmt(bottom_value)}, gap = {_fmt(gap)}.",
        "Large segment gaps point to where strategy, operations, or customer behavior differs.",
        f"Vì sao `{top_label}` khác `{bottom_label}` về {metric_name}?",
        tone="neutral",
        severity="info",
        confidence=0.75,
        metric=metric_name,
        dimension=dimension_name,
    )]


def detect_correlation_insights(df: pd.DataFrame) -> list[dict[str, Any]]:
    numeric = _numeric_columns(df)
    if len(numeric) < 2:
        return []
    corr = df[numeric].corr(numeric_only=True)
    best: tuple[str, str, float] | None = None
    for left in numeric:
        for right in numeric:
            if left >= right:
                continue
            value = corr.loc[left, right]
            if pd.isna(value):
                continue
            if best is None or abs(value) > abs(best[2]):
                best = (left, right, float(value))
    if best is None or abs(best[2]) < 0.5:
        return []
    left, right, value = best
    direction = "positive" if value > 0 else "negative"
    return [_insight(
        "correlation",
        "Strongest Numeric Correlation",
        f"`{left}` and `{right}` have the strongest {direction} correlation.",
        f"Correlation coefficient = {value:.3f}. Correlation is not causation.",
        "Correlation highlights relationships worth investigating, but it does not prove cause and effect.",
        f"Mối tương quan giữa `{left}` và `{right}` có khác nhau theo segment không?",
        tone="neutral",
        severity="info",
        confidence=0.72,
        metric=left,
        dimension=right,
        related_table_id="generic_correlation",
        related_chart_id="generic_correlation_chart",
    )]


def detect_pareto_insights(df: pd.DataFrame, profile, metrics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    metric_name, series = _preferred_metric_series(df, profile, metrics)
    dimension_name, dimension = _preferred_dimension_series(df, profile)
    if metric_name is None or series is None or dimension_name is None or dimension is None:
        return []
    temp = pd.DataFrame({"dimension": dimension, "metric": pd.to_numeric(series, errors="coerce")}).dropna(subset=["metric"])
    grouped = temp.groupby("dimension", dropna=False)["metric"].sum().sort_values(ascending=False)
    if len(grouped) < 3 or grouped.sum() == 0:
        return []
    cumulative = grouped.cumsum() / grouped.sum()
    contributors = int((cumulative <= 0.8).sum()) or 1
    share = contributors / len(grouped)
    return [_insight(
        "pareto",
        f"{metric_name.title()} Concentration",
        f"Top {contributors} of {len(grouped)} groups contribute around 80% of {metric_name}.",
        f"Contributor share = {share * 100:.2f}%.",
        "Concentration reveals whether performance depends on a small number of groups.",
        f"Top contributors của {metric_name} có rủi ro hoặc margin thấp không?",
        tone="neutral",
        severity="info",
        confidence=0.74,
        metric=metric_name,
        dimension=dimension_name,
    )]


def detect_target_insights(df: pd.DataFrame, profile) -> list[dict[str, Any]]:
    target_column = _role_column(profile, "target") or _role_column(profile, "conversion")
    dimension_name, dimension = _preferred_dimension_series(df, profile)
    if not target_column or dimension_name is None or dimension is None:
        return []
    temp = pd.DataFrame({"dimension": dimension, "target": df[target_column]}).copy()
    temp["_positive"] = temp["target"].map(_is_positive)
    grouped = temp.groupby("dimension", dropna=False).agg(rows=("target", "count"), positive_rate=("_positive", "mean")).reset_index()
    grouped = grouped[grouped["rows"] >= 1].sort_values("positive_rate", ascending=False)
    if grouped.empty:
        return []
    top = grouped.iloc[0]
    return [_insight(
        "target_conversion",
        "Highest Positive Target Segment",
        f"`{top['dimension']}` has the highest positive target rate.",
        f"Positive rate = {float(top['positive_rate']) * 100:.2f}%, rows = {int(top['rows'])}.",
        "High target-rate segments can reveal risk, conversion opportunity, or behavioral drivers.",
        f"Nhóm `{top['dimension']}` có đặc điểm gì khác các nhóm còn lại?",
        tone="positive",
        severity="info",
        confidence=0.78,
        metric=str(target_column),
        dimension=dimension_name,
    )]


def _preferred_metric_series(df: pd.DataFrame, profile, metrics: list[dict[str, Any]] | None) -> tuple[str | None, pd.Series | None]:
    for metric in metrics or []:
        definition = normalize_metric_definition(metric)
        try:
            result = evaluate_metric(df, profile, definition)
        except Exception:
            continue
        if isinstance(result, pd.Series):
            return definition["name"], pd.to_numeric(result, errors="coerce")
    for role in ["revenue", "profit", "quantity", "salary", "cost"]:
        column = _role_column(profile, role)
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            return role, pd.to_numeric(df[column], errors="coerce")
    numeric = _numeric_columns(df)
    if numeric:
        return str(numeric[0]), pd.to_numeric(df[numeric[0]], errors="coerce")
    return None, None


def _preferred_dimension_series(df: pd.DataFrame, profile) -> tuple[str | None, pd.Series | None]:
    for role in ["category", "segment", "state", "country", "department", "job_role", "campaign", "channel"]:
        column = _role_column(profile, role)
        if column in df.columns:
            return role, df[column]
    categorical = [
        column for column in df.columns
        if not pd.api.types.is_numeric_dtype(df[column]) and df[column].nunique(dropna=True) > 1
    ]
    if categorical:
        return str(categorical[0]), df[categorical[0]]
    return None, None


def _role_column(profile, role: str) -> str | None:
    match = getattr(profile, "roles", {}).get(role)
    return getattr(match, "column", None) if match else None


def _first_date_like_column(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            return str(column)
        if "date" in str(column).lower() or "time" in str(column).lower():
            parsed = pd.to_datetime(df[column].dropna().head(20), errors="coerce")
            if not parsed.empty and parsed.notna().mean() >= 0.7:
                return str(column)
    return None


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(column) for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]


def _is_positive(value: Any) -> bool:
    if isinstance(value, (int, float, bool)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"yes", "true", "1", "y", "positive", "converted", "responded"}


def _insight(
    insight_type: str,
    title: str,
    finding: str,
    evidence: str,
    why_it_matters: str,
    recommended_next_question: str,
    *,
    severity: str = "info",
    tone: str = "neutral",
    confidence: float = 0.75,
    metric: str | None = None,
    dimension: str | None = None,
    related_chart_id: str | None = None,
    related_table_id: str | None = None,
) -> dict[str, Any]:
    stable = f"{insight_type}_{abs(hash((title, metric, dimension))) % 100000}"
    return {
        "id": stable,
        "type": insight_type,
        "title": title,
        "value": finding,
        "narrative": f"{finding} {why_it_matters}",
        "finding": finding,
        "evidence": evidence,
        "why_it_matters": why_it_matters,
        "recommended_next_question": recommended_next_question,
        "severity": severity,
        "tone": tone,
        "confidence": confidence,
        "metric": metric,
        "dimension": dimension,
        "related_chart_id": related_chart_id,
        "related_table_id": related_table_id,
    }


def _fmt(value: Any) -> str:
    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"{float(value):,.2f}"
    return "N/A" if value is None else str(value)
