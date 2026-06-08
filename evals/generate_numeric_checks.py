from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.data_dictionary import parse_data_dictionary_file, validate_data_dictionary
from app.services.data_loader import load_tabular_file
from app.services.dataset_pipeline import prepare_amazon_sales_dataframe
from app.services.semantic_mapper import build_semantic_profile
from evals.run_eval import EvalDataset, build_dataset_index, dataset_key, load_manifest


def load_df(path: Path, max_rows: int) -> pd.DataFrame:
    df = load_tabular_file(path.read_bytes(), path.name)
    return df.head(max_rows).copy() if max_rows and len(df) > max_rows else df


def load_dictionary(path: Path | None, df: pd.DataFrame) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    dictionary = parse_data_dictionary_file(path.read_bytes(), path.name)
    validate_data_dictionary(dictionary, list(df.columns))
    return dictionary


def role_column(profile: Any, role: str | None) -> str | None:
    if not role:
        return None
    match = getattr(profile, "roles", {}).get(role)
    return getattr(match, "column", None) if match else None


def number(value: Any) -> float | None:
    try:
        result = float(value)
    except Exception:
        return None
    return result if math.isfinite(result) else None


def clean_label(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def metric_check(label: Any, metric: str, expected: Any, tolerance: float = 0.01) -> dict[str, Any] | None:
    value = number(expected)
    if value is None:
        return None
    return {
        "label": clean_label(label),
        "metric": metric,
        "expected": round(value, 6),
        "tolerance": tolerance,
    }


def semantic_breakdown_check(df: pd.DataFrame, profile: Any, by_role: str | None, metric_role: str | None) -> dict[str, Any] | None:
    by_col = role_column(profile, by_role)
    metric_col = role_column(profile, metric_role)
    if not by_col or not metric_col or not pd.api.types.is_numeric_dtype(df[metric_col]):
        return None
    grouped = (
        df.groupby(by_col, dropna=False)[metric_col]
        .sum()
        .reset_index(name=metric_col)
        .sort_values(metric_col, ascending=False)
    )
    if grouped.empty:
        return None
    row = grouped.iloc[0]
    return metric_check(row[by_col], metric_col, row[metric_col])


def time_series_check(df: pd.DataFrame, profile: Any, metric_role: str | None) -> dict[str, Any] | None:
    date_col = role_column(profile, "date")
    metric_col = role_column(profile, metric_role) or role_column(profile, "revenue") or role_column(profile, "profit") or role_column(profile, "quantity")
    if not date_col or not metric_col or not pd.api.types.is_numeric_dtype(df[metric_col]):
        return None
    temp = df[[date_col, metric_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])
    if temp.empty:
        return None
    grouped = (
        temp.groupby(temp[date_col].dt.to_period("M").astype(str))[metric_col]
        .sum()
        .reset_index(name=metric_col)
        .sort_values("period" if "period" in temp.columns else date_col)
    )
    grouped = grouped.rename(columns={date_col: "period"})
    if grouped.empty:
        return None
    row = grouped.iloc[0]
    return metric_check(row["period"], metric_col, row[metric_col])


def positive(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    text = str(value).strip().lower()
    return text in {"yes", "true", "1", "1.0", "y", "accepted", "converted", "satisfied"}


def target_summary_check(df: pd.DataFrame, profile: Any, by_role: str | None) -> dict[str, Any] | None:
    target_col = role_column(profile, "target") or role_column(profile, "conversion")
    by_col = role_column(profile, by_role)
    if not target_col:
        return None
    temp = df[[target_col]].copy()
    temp["_target_positive"] = temp[target_col].map(positive)
    if by_col and by_col != target_col:
        temp[by_col] = df[by_col]
        grouped = (
            temp.groupby(by_col, dropna=False)
            .agg(rows=(target_col, "count"), positive_rate=("_target_positive", "mean"))
            .reset_index()
            .sort_values("positive_rate", ascending=False)
        )
        if not grouped.empty:
            row = grouped.iloc[0]
            return metric_check(row[by_col], "positive_rate", row["positive_rate"], tolerance=0.000001)
    return metric_check(None, "positive_rate", temp["_target_positive"].mean(), tolerance=0.000001)


def outlier_check(df: pd.DataFrame, profile: Any, metric_role: str | None) -> dict[str, Any] | None:
    metric_col = role_column(profile, metric_role) or role_column(profile, "quantity") or role_column(profile, "revenue")
    if not metric_col or not pd.api.types.is_numeric_dtype(df[metric_col]):
        return None
    clean = df[metric_col].dropna()
    if clean.empty:
        return metric_check(None, "outliers_count", 0, tolerance=0)
    q1 = clean.quantile(0.25)
    q3 = clean.quantile(0.75)
    iqr = q3 - q1
    count = int(((df[metric_col] < q1 - 1.5 * iqr) | (df[metric_col] > q3 + 1.5 * iqr)).sum())
    return metric_check(None, "outliers_count", count, tolerance=0)


def overview_check(df: pd.DataFrame, profile: Any, dataset_id: str) -> dict[str, Any] | None:
    if dataset_id == "ecommerce_amazon_sales":
        prepared = prepare_amazon_sales_dataframe(df)
        return metric_check(None, "total_revenue", prepared["revenue"].sum(skipna=True))
    return metric_check(None, "rows", len(df), tolerance=0)


def quality_check(df: pd.DataFrame, expected_tool: str | None) -> dict[str, Any] | None:
    if expected_tool == "get_duplicate_rows":
        return metric_check(None, "duplicate_rows", int(df.duplicated().sum()), tolerance=0)
    return None


def numeric_checks_for_case(case: dict[str, Any], dataset: EvalDataset, df: pd.DataFrame, profile: Any) -> list[dict[str, Any]]:
    expected_tool = case.get("expected_tool")
    expected_intent = case.get("expected_intent")
    metric_role = case.get("expected_metric_role") or None
    dimension_role = case.get("expected_dimension_role") or None

    check: dict[str, Any] | None = None
    if expected_tool in {"semantic_breakdown", "groupby_aggregate", "top_bottom_contributors"}:
        check = semantic_breakdown_check(df, profile, dimension_role, metric_role)
    elif expected_tool in {"semantic_time_series", "trend_analysis"}:
        check = time_series_check(df, profile, metric_role)
    elif expected_tool == "semantic_target_summary":
        check = target_summary_check(df, profile, dimension_role)
    elif expected_tool == "detect_outliers" or expected_intent == "outlier":
        check = outlier_check(df, profile, metric_role)
    elif expected_tool in {"get_dataset_overview", "get_sales_overview"}:
        check = overview_check(df, profile, dataset.id)
    elif expected_tool == "top_skus_by_revenue":
        prepared = prepare_amazon_sales_dataframe(df)
        grouped = prepared.groupby("sku", dropna=False)["revenue"].sum().reset_index(name="revenue").sort_values("revenue", ascending=False)
        if not grouped.empty:
            check = metric_check(grouped.iloc[0]["sku"], "revenue", grouped.iloc[0]["revenue"])
    elif expected_intent == "data_quality":
        check = quality_check(df, expected_tool)

    return [check] if check else []


def update_question_file(path: Path, datasets: dict[str, EvalDataset], root: Path) -> int:
    updated = 0
    lines = []
    prepared: dict[str, tuple[pd.DataFrame, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            lines.append(line)
            continue
        case = json.loads(line)
        dataset = datasets.get(case["dataset"])
        if not dataset:
            lines.append(json.dumps(case, ensure_ascii=False))
            continue
        if dataset.id not in prepared:
            df = load_df(root / dataset.local_path, dataset.max_rows)
            dictionary_path = root / dataset.data_dictionary if dataset.data_dictionary else None
            dictionary = load_dictionary(dictionary_path, df)
            profile = build_semantic_profile(df, overrides={"data_dictionary": dictionary})
            prepared[dataset.id] = (df, profile)
        df, profile = prepared[dataset.id]
        checks = numeric_checks_for_case(case, dataset, df, profile)
        if checks:
            case["numeric_checks"] = checks
            updated += 1
        lines.append(json.dumps(case, ensure_ascii=False, separators=(",", ":")))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic numeric checks for Phase U5 eval cases.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="evals/manifest.json")
    parser.add_argument("--questions", default="evals/questions")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    datasets = build_dataset_index(load_manifest(root / args.manifest))
    total = 0
    for path in sorted((root / args.questions).glob("*.jsonl")):
        count = update_question_file(path, datasets, root)
        total += count
        print(f"{path}: {count} numeric checks")
    print(f"Updated {total} numeric checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
