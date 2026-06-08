from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

import app.services.agent_orchestrator as orchestrator_module
from app.services.agent_orchestrator import AgentOrchestrator, _looks_like_amazon_sales
from app.services.data_dictionary import parse_data_dictionary_file, validate_data_dictionary
from app.services.data_loader import load_tabular_file
from app.services.intent_planner import parse_universal_intent
from app.services.semantic_mapper import build_semantic_profile
from app.services.storage import dataset_store


THRESHOLDS = {
    "domain_accuracy": 0.80,
    "role_mapping_accuracy": 0.75,
    "intent_accuracy": 0.80,
    "tool_accuracy": 0.80,
    "numeric_accuracy": 0.90,
    "error_rate_max": 0.05,
}


class NoLLMProvider:
    def route(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("LLM disabled for eval deterministic mode.")

    def explain(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        raise RuntimeError("LLM disabled for eval deterministic mode.")

    def status(self) -> dict[str, Any]:
        return {"available": False, "error": "disabled_for_eval"}


class NoSemanticCache:
    def query_cache(self, dataset_id: str, question: str, threshold: float = 0.88) -> None:
        return None

    def add_to_cache(self, dataset_id: str, question: str, response: dict[str, Any]) -> None:
        return None


@dataclass
class EvalDataset:
    id: str
    domain: str
    source_name: str
    source_url: str
    local_path: str
    format: str
    acquisition: str
    max_rows: int = 10000
    required: bool = True
    data_dictionary: str | None = None
    source_path: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvalDataset":
        required = ["id", "domain", "source_name", "source_url", "local_path", "format", "acquisition"]
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise ValueError(f"Manifest dataset is missing required fields: {missing}")
        return cls(
            id=str(raw["id"]),
            domain=str(raw["domain"]),
            source_name=str(raw["source_name"]),
            source_url=str(raw["source_url"]),
            local_path=str(raw["local_path"]),
            data_dictionary=raw.get("data_dictionary"),
            format=str(raw["format"]),
            acquisition=str(raw["acquisition"]),
            max_rows=int(raw.get("max_rows") or 10000),
            required=bool(raw.get("required", True)),
            source_path=raw.get("source_path"),
            notes=raw.get("notes"),
        )


@dataclass
class EvalCase:
    id: str
    dataset: str
    question: str
    expected_domain: str | None = None
    expected_intent: str | None = None
    expected_metric_role: str | None = None
    expected_dimension_role: str | None = None
    expected_tool: str | None = None
    data_dictionary: str | None = None
    numeric_checks: list[dict[str, Any]] = field(default_factory=list)
    answer_must_include: list[str] = field(default_factory=list)
    answer_must_not_include: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvalCase":
        required = ["id", "dataset", "question"]
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise ValueError(f"Eval case is missing required fields: {missing}")
        return cls(
            id=str(raw["id"]),
            dataset=str(raw["dataset"]),
            question=str(raw["question"]),
            expected_domain=raw.get("expected_domain"),
            expected_intent=raw.get("expected_intent"),
            expected_metric_role=raw.get("expected_metric_role"),
            expected_dimension_role=raw.get("expected_dimension_role"),
            expected_tool=raw.get("expected_tool"),
            data_dictionary=raw.get("data_dictionary"),
            numeric_checks=list(raw.get("numeric_checks") or []),
            answer_must_include=list(raw.get("answer_must_include") or []),
            answer_must_not_include=list(raw.get("answer_must_not_include") or []),
        )


@dataclass
class PreparedDataset:
    manifest: EvalDataset
    df: pd.DataFrame
    dataset_id: str
    dictionary: dict[str, Any] | None


def load_manifest(path: Path) -> list[EvalDataset]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    datasets = raw.get("datasets") if isinstance(raw, dict) else raw
    if not isinstance(datasets, list):
        raise ValueError("Manifest must contain a `datasets` list.")
    parsed = [EvalDataset.from_dict(item) for item in datasets]
    if len(parsed) != 20:
        raise ValueError(f"Phase U5 manifest must contain exactly 20 datasets, found {len(parsed)}.")
    return parsed


def load_cases(path: Path) -> list[EvalCase]:
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    cases: list[EvalCase] = []
    for file in files:
        for line_number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                cases.append(EvalCase.from_dict(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"Invalid eval case in {file}:{line_number}: {exc}") from exc
    return cases


def dataset_key(path: str) -> str:
    marker = "evals/datasets/"
    return path.split(marker, 1)[-1] if marker in path else path


def build_dataset_index(datasets: list[EvalDataset]) -> dict[str, EvalDataset]:
    index: dict[str, EvalDataset] = {}
    for dataset in datasets:
        index[dataset.id] = dataset
        index[dataset.local_path] = dataset
        index[dataset_key(dataset.local_path)] = dataset
    return index


def load_dataframe(path: Path) -> pd.DataFrame:
    content = path.read_bytes()
    df = load_tabular_file(content, path.name)
    return df


def load_dictionary(path: Path | None, df: pd.DataFrame) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    dictionary = parse_data_dictionary_file(path.read_bytes(), path.name)
    validate_data_dictionary(dictionary, list(df.columns))
    return dictionary


def prepare_dataset(dataset: EvalDataset, root: Path, dictionary_override: str | None = None) -> PreparedDataset:
    path = root / dataset.local_path
    if not path.exists():
        raise FileNotFoundError(f"Dataset file is missing: {dataset.local_path}")
    df = load_dataframe(path)
    if dataset.max_rows and len(df) > dataset.max_rows:
        df = df.head(dataset.max_rows).copy()
    dictionary_path = root / (dictionary_override or dataset.data_dictionary or "") if (dictionary_override or dataset.data_dictionary) else None
    dictionary = load_dictionary(dictionary_path, df)
    dataset_id = dataset_store.save_dataframe(df, path.name)
    if dictionary:
        dataset_store.set_data_dictionary(dataset_id, dictionary)
    return PreparedDataset(manifest=dataset, df=df, dataset_id=dataset_id, dictionary=dictionary)


def evaluate_case(
    case: EvalCase,
    prepared: PreparedDataset,
    *,
    mode: str,
    disable_semantic_cache: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "id": case.id,
        "dataset": case.dataset,
        "question": case.question,
        "status": "passed",
        "checks": {},
        "errors": [],
        "latency_ms": None,
    }
    try:
        profile = build_semantic_profile(prepared.df, overrides={"data_dictionary": prepared.dictionary})
        intent = parse_universal_intent(
            case.question,
            prepared.df,
            profile,
            [],
            ecommerce_available=_looks_like_amazon_sales(prepared.df),
        )

        result["actual_domain"] = profile.domain
        result["actual_intent"] = intent.to_dict()

        provider = NoLLMProvider() if mode == "fast" else None
        orchestrator = AgentOrchestrator(provider=provider, store=dataset_store)
        if disable_semantic_cache:
            orchestrator_module.semantic_cache_service = NoSemanticCache()
        response = orchestrator.chat(prepared.dataset_id, case.question, mode=mode)
        result["agent_response"] = _compact_response(response)

        checks = result["checks"]
        checks["domain"] = _optional_equals(profile.domain, case.expected_domain)
        checks["metric_role"] = _role_present(profile, case.expected_metric_role)
        checks["dimension_role"] = _role_present(profile, case.expected_dimension_role)
        checks["intent"] = _optional_equals(intent.task, case.expected_intent)
        checks["tool"] = _tool_matches(response, case.expected_tool)
        checks["numeric"] = _numeric_checks(response, case.numeric_checks)
        checks["answer_constraints"] = _answer_constraints(response.get("answer", ""), case)

        failed = [name for name, check in checks.items() if check["expected"] and not check["passed"]]
        if failed:
            result["status"] = "failed"
            result["errors"].append(f"Failed checks: {', '.join(failed)}")
        if response.get("explanation_source") == "tool_error":
            result["status"] = "error"
            result["errors"].append("Agent returned tool_error.")
    except Exception as exc:
        result["status"] = "error"
        result["errors"].append(str(exc))
    finally:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return result


def summarize(results: list[dict[str, Any]], missing_required: list[str]) -> dict[str, Any]:
    total = len(results)
    skipped = [item for item in results if item["status"] == "skipped"]
    errors = [item for item in results if item["status"] == "error"]
    failed = [item for item in results if item["status"] == "failed"]
    passed = [item for item in results if item["status"] == "passed"]
    latencies = [float(item.get("latency_ms") or 0) for item in results if item.get("latency_ms") is not None]
    active_total = max(total - len(skipped), 0)

    check_metrics = {
        "domain_accuracy": _check_rate(results, "domain"),
        "role_mapping_accuracy": _combined_check_rate(results, ["metric_role", "dimension_role"]),
        "intent_accuracy": _check_rate(results, "intent"),
        "tool_accuracy": _check_rate(results, "tool"),
        "numeric_accuracy": _numeric_rate(results),
        "answer_constraint_pass_rate": _check_rate(results, "answer_constraints"),
        "fallback_rate": _fallback_rate(results),
        "cache_hit_rate": _cache_hit_rate(results),
        "error_rate": (len(errors) / active_total) if active_total else 0.0,
        "average_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
        "p95_latency_ms": _p95(latencies),
    }
    thresholds = {
        "domain_accuracy": check_metrics["domain_accuracy"] >= THRESHOLDS["domain_accuracy"],
        "role_mapping_accuracy": check_metrics["role_mapping_accuracy"] >= THRESHOLDS["role_mapping_accuracy"],
        "intent_accuracy": check_metrics["intent_accuracy"] >= THRESHOLDS["intent_accuracy"],
        "tool_accuracy": check_metrics["tool_accuracy"] >= THRESHOLDS["tool_accuracy"],
        "numeric_accuracy": check_metrics["numeric_accuracy"] >= THRESHOLDS["numeric_accuracy"],
        "error_rate": check_metrics["error_rate"] <= THRESHOLDS["error_rate_max"],
    }
    return {
        "total_cases": total,
        "passed_cases": len(passed),
        "failed_cases": len(failed),
        "error_cases": len(errors),
        "skipped_cases": len(skipped),
        "missing_required_datasets": missing_required,
        "domain_metrics": _domain_metrics(results),
        "metrics": check_metrics,
        "thresholds": thresholds,
        "overall_pass": all(thresholds.values()) and not missing_required,
    }


def write_reports(summary: dict[str, Any], results: list[dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    json_path = out.with_suffix(".json")
    json_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    out.write_text(render_markdown(summary, results, json_path), encoding="utf-8")


def render_markdown(summary: dict[str, Any], results: list[dict[str, Any]], json_path: Path) -> str:
    metrics = summary["metrics"]
    thresholds = summary["thresholds"]
    lines = [
        "# Phase U5 Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Passed: {summary['passed_cases']}",
        f"- Failed: {summary['failed_cases']}",
        f"- Errors: {summary['error_cases']}",
        f"- Skipped: {summary['skipped_cases']}",
        f"- Overall pass: {'yes' if summary['overall_pass'] else 'no'}",
        f"- JSON details: `{json_path}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Threshold Pass |",
        "|---|---:|---|",
    ]
    for key, value in metrics.items():
        threshold = thresholds.get(key)
        pass_text = "n/a" if threshold is None else ("pass" if threshold else "fail")
        lines.append(f"| {key} | {_format_metric(value)} | {pass_text} |")
    if summary.get("domain_metrics"):
        lines.extend([
            "",
            "## Per-Domain Summary",
            "",
            "| Domain | Total | Passed | Failed | Errors | Skipped | Intent | Tool | Numeric | Avg Latency |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for domain, item in sorted(summary["domain_metrics"].items()):
            lines.append(
                f"| {domain} | {item['total']} | {item['passed']} | {item['failed']} | "
                f"{item['errors']} | {item['skipped']} | {_format_metric(item['intent_accuracy'])} | "
                f"{_format_metric(item['tool_accuracy'])} | {_format_metric(item['numeric_accuracy'])} | "
                f"{_format_metric(item['average_latency_ms'])} |"
            )
    if summary["missing_required_datasets"]:
        lines.extend([
            "",
            "## Missing Required Datasets",
            "",
            *[f"- `{item}`" for item in summary["missing_required_datasets"]],
        ])

    failing = [item for item in results if item["status"] != "passed"]
    lines.extend(["", "## Non-Passed Cases", ""])
    if not failing:
        lines.append("No non-passed cases.")
    else:
        lines.extend(["| Case | Dataset | Status | Errors |", "|---|---|---|---|"])
        for item in failing[:100]:
            errors = "; ".join(item.get("errors") or [])
            lines.append(f"| {item['id']} | `{item['dataset']}` | {item['status']} | {errors} |")
    lines.extend([
        "",
        "## Recommended Next Fixes",
        "",
        "- Improve semantic mapper for domains with repeated role-mapping failures.",
        "- Add or correct data dictionaries for datasets with low-confidence role mapping.",
        "- Add deterministic planner rules for frequent intent/tool mismatches.",
        "- Convert manual external datasets into capped local snapshots before strict gating.",
    ])
    return "\n".join(lines) + "\n"


def run_eval(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = Path(args.root).resolve()
    datasets = load_manifest(root / args.manifest)
    cases = load_cases(root / args.questions)
    index = build_dataset_index(datasets)
    missing_required = [
        dataset.local_path
        for dataset in datasets
        if dataset.required and not (root / dataset.local_path).exists()
    ]

    prepared_cache: dict[str, PreparedDataset] = {}
    results: list[dict[str, Any]] = []
    for case in cases:
        dataset = index.get(case.dataset)
        if not dataset:
            results.append(_skipped_case(case, f"Dataset not found in manifest: {case.dataset}"))
            continue
        if not (root / dataset.local_path).exists():
            results.append(_skipped_case(case, f"Dataset file missing: {dataset.local_path}"))
            continue
        cache_key = f"{dataset.id}|{case.data_dictionary or dataset.data_dictionary or ''}"
        try:
            if cache_key not in prepared_cache:
                prepared_cache[cache_key] = prepare_dataset(dataset, root, case.data_dictionary)
            results.append(evaluate_case(
                case,
                prepared_cache[cache_key],
                mode=args.mode,
                disable_semantic_cache=not args.enable_semantic_cache,
            ))
        except Exception as exc:
            results.append(_error_case(case, str(exc)))

    summary = summarize(results, missing_required if args.strict else [])
    write_reports(summary, results, root / args.out)
    return summary, results


def _skipped_case(case: EvalCase, reason: str) -> dict[str, Any]:
    return {
        "id": case.id,
        "dataset": case.dataset,
        "question": case.question,
        "status": "skipped",
        "checks": {},
        "errors": [reason],
        "latency_ms": 0,
    }


def _error_case(case: EvalCase, reason: str) -> dict[str, Any]:
    item = _skipped_case(case, reason)
    item["status"] = "error"
    return item


def _optional_equals(actual: Any, expected: Any) -> dict[str, Any]:
    if expected is None or expected == "":
        return {"expected": False, "passed": True, "actual": actual, "expected_value": expected}
    return {"expected": True, "passed": actual == expected, "actual": actual, "expected_value": expected}


def _role_present(profile: Any, expected_role: str | None) -> dict[str, Any]:
    if not expected_role:
        return {"expected": False, "passed": True, "actual": None, "expected_value": expected_role}
    roles = getattr(profile, "roles", {})
    actual = roles.get(expected_role).column if expected_role in roles else None
    return {"expected": True, "passed": actual is not None, "actual": actual, "expected_value": expected_role}


def _tool_matches(response: dict[str, Any], expected_tool: str | None) -> dict[str, Any]:
    calls = response.get("tool_calls") or []
    actual_tools = [call.get("tool_name") for call in calls if isinstance(call, dict)]
    if not actual_tools and response.get("tool_call"):
        actual_tools = [response["tool_call"].get("tool_name")]
    if not expected_tool:
        return {"expected": False, "passed": True, "actual": actual_tools, "expected_value": expected_tool}
    return {"expected": True, "passed": expected_tool in actual_tools, "actual": actual_tools, "expected_value": expected_tool}


def _numeric_checks(response: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    if not checks:
        return {"expected": False, "passed": True, "items": []}
    rows = _result_rows(response)
    results = []
    for check in checks:
        label = check.get("label")
        metric = check.get("metric")
        expected = float(check.get("expected"))
        tolerance = float(check.get("tolerance", 0.0))
        actual = _find_numeric_value(rows, label, metric)
        passed = actual is not None and math.isclose(float(actual), expected, rel_tol=tolerance, abs_tol=tolerance)
        results.append({"label": label, "metric": metric, "expected": expected, "actual": actual, "tolerance": tolerance, "passed": passed})
    return {"expected": True, "passed": all(item["passed"] for item in results), "items": results}


def _answer_constraints(answer: str, case: EvalCase) -> dict[str, Any]:
    has_constraints = bool(case.answer_must_include or case.answer_must_not_include)
    normalized = answer.lower()
    missing = [text for text in case.answer_must_include if text.lower() not in normalized]
    forbidden = [text for text in case.answer_must_not_include if text.lower() in normalized]
    return {
        "expected": has_constraints,
        "passed": not missing and not forbidden,
        "missing": missing,
        "forbidden": forbidden,
    }


def _result_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[Any] = []
    for call in response.get("tool_calls") or []:
        if isinstance(call, dict):
            results.append(call.get("result"))
    if response.get("tool_call"):
        results.append(response["tool_call"].get("result"))
    rows: list[dict[str, Any]] = []
    for result in results:
        rows.extend(_rows_from_result(result))
    return rows


def _rows_from_result(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        rows: list[dict[str, Any]] = []
        scalar_row = {
            key: value
            for key, value in result.items()
            if not isinstance(value, (list, dict))
        }
        for key, value in result.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if not isinstance(nested_value, (list, dict)):
                        scalar_row[f"{key}.{nested_key}"] = nested_value
                        scalar_row[str(nested_key)] = nested_value
        if scalar_row:
            rows.append(scalar_row)
        for key in ("items", "rows", "data", "by_group", "trend_records", "top_contributors", "bottom_contributors", "contributors", "correlations", "outlier_sample"):
            if isinstance(result.get(key), list):
                rows.extend(item for item in result[key] if isinstance(item, dict))
        if isinstance(result.get("summary"), dict):
            rows.extend(_rows_from_result(result["summary"]))
        return rows
    return []


def _find_numeric_value(rows: list[dict[str, Any]], label: Any, metric: str | None) -> float | None:
    for row in rows:
        if label is not None and not any(_label_matches(value, label) for value in row.values()):
            continue
        if metric and metric in row and _is_number(row[metric]):
            return float(row[metric])
        if metric:
            for key, value in row.items():
                if str(key).lower() == str(metric).lower() and _is_number(value):
                    return float(value)
    return None


def _label_matches(value: Any, expected: Any) -> bool:
    if str(value).strip().lower() == str(expected).strip().lower():
        return True
    actual_number = _coerce_number(value)
    expected_number = _coerce_number(expected)
    return actual_number is not None and expected_number is not None and math.isclose(actual_number, expected_number, rel_tol=1e-9, abs_tol=1e-9)


def _coerce_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _is_number(value: Any) -> bool:
    try:
        number = float(value)
        return math.isfinite(number)
    except Exception:
        return False


def _compact_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": response.get("answer"),
        "tool_call": response.get("tool_call", {}),
        "tool_calls": [
            {key: call.get(key) for key in ("tool_name", "arguments", "error", "execution_ms", "purpose")}
            for call in response.get("tool_calls", [])
            if isinstance(call, dict)
        ],
        "agent_plan": response.get("agent_plan"),
        "explanation_source": response.get("explanation_source"),
        "latency": response.get("latency"),
        "cache": response.get("cache"),
        "warnings": response.get("warnings", []),
    }


def _check_rate(results: list[dict[str, Any]], check_name: str) -> float:
    checks = [item.get("checks", {}).get(check_name) for item in results]
    expected = [item for item in checks if item and item.get("expected")]
    if not expected:
        return 1.0
    return sum(1 for item in expected if item.get("passed")) / len(expected)


def _combined_check_rate(results: list[dict[str, Any]], check_names: list[str]) -> float:
    items = []
    for result in results:
        checks = result.get("checks", {})
        for name in check_names:
            check = checks.get(name)
            if check and check.get("expected"):
                items.append(check)
    if not items:
        return 1.0
    return sum(1 for item in items if item.get("passed")) / len(items)


def _numeric_rate(results: list[dict[str, Any]]) -> float:
    items = []
    for result in results:
        numeric = result.get("checks", {}).get("numeric")
        if numeric and numeric.get("expected"):
            items.extend(numeric.get("items") or [])
    if not items:
        return 1.0
    return sum(1 for item in items if item.get("passed")) / len(items)


def _fallback_rate(results: list[dict[str, Any]]) -> float:
    expected = [item for item in results if item.get("agent_response")]
    if not expected:
        return 0.0
    count = sum(1 for item in expected if item["agent_response"].get("explanation_source") == "deterministic_fallback")
    return count / len(expected)


def _cache_hit_rate(results: list[dict[str, Any]]) -> float:
    expected = [item for item in results if item.get("agent_response")]
    if not expected:
        return 0.0
    hits = 0
    total = 0
    for item in expected:
        cache = item["agent_response"].get("cache") or {}
        if cache.get("semantic_profile"):
            total += 1
            hits += 1 if cache.get("semantic_profile") == "hit" else 0
        for tool in cache.get("tool_results") or []:
            total += 1
            hits += 1 if tool.get("cache") == "hit" else 0
    return hits / total if total else 0.0


def _domain_metrics(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        domain = str(item.get("dataset") or "generic").split("/", 1)[0] or "generic"
        grouped.setdefault(domain, []).append(item)

    summary: dict[str, dict[str, Any]] = {}
    for domain, items in grouped.items():
        latencies = [float(item.get("latency_ms") or 0) for item in items if item.get("latency_ms") is not None]
        summary[domain] = {
            "total": len(items),
            "passed": sum(1 for item in items if item["status"] == "passed"),
            "failed": sum(1 for item in items if item["status"] == "failed"),
            "errors": sum(1 for item in items if item["status"] == "error"),
            "skipped": sum(1 for item in items if item["status"] == "skipped"),
            "intent_accuracy": _check_rate(items, "intent"),
            "tool_accuracy": _check_rate(items, "tool"),
            "numeric_accuracy": _numeric_rate(items),
            "average_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
        }
    return summary


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, math.ceil(len(sorted_values) * 0.95) - 1)
    return round(sorted_values[index], 1)


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        if 0 <= value <= 1:
            return f"{value:.1%}"
        return f"{value:.1f}"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase U5 dataset intelligence evaluation.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--manifest", default="evals/manifest.json")
    parser.add_argument("--questions", default="evals/questions")
    parser.add_argument("--out", default="evals/reports/latest.md")
    parser.add_argument("--mode", choices=["fast", "balanced", "deep"], default="fast")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--enable-semantic-cache", action="store_true")
    args = parser.parse_args(argv)

    summary, _ = run_eval(args)
    print(f"Eval report written to {args.out}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.strict and not summary["overall_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
