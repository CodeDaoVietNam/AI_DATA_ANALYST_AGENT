from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.run_eval import _numeric_checks, load_cases, load_manifest, run_eval


def test_u5_manifest_and_questions_have_required_counts():
    datasets = load_manifest(Path("evals/manifest.json"))
    cases = load_cases(Path("evals/questions"))

    assert len(datasets) == 20
    assert len(cases) == 100
    assert {dataset.domain for dataset in datasets} >= {
        "ecommerce",
        "retail",
        "finance",
        "marketing",
        "hr",
        "logistics",
        "education",
        "survey",
        "product",
        "generic",
    }


def test_numeric_checks_respect_tolerance():
    response = {
        "tool_calls": [
            {
                "tool_name": "semantic_breakdown",
                "result": [
                    {"category": "Technology", "revenue": 100.005},
                    {"category": "Furniture", "revenue": 80.0},
                ],
            }
        ]
    }

    check = _numeric_checks(response, [
        {"label": "Technology", "metric": "revenue", "expected": 100.0, "tolerance": 0.01}
    ])

    assert check["passed"] is True


def test_numeric_checks_read_nested_result_rows_and_numeric_labels():
    response = {
        "tool_calls": [
            {
                "tool_name": "semantic_target_summary",
                "result": {
                    "target_column": "Response",
                    "positive_rate": 0.4,
                    "by_group": [
                        {"AcceptedCmp1": 1, "positive_rate": 0.548611},
                        {"AcceptedCmp1": 0, "positive_rate": 0.25},
                    ],
                },
            }
        ]
    }

    check = _numeric_checks(response, [
        {"label": "1.0", "metric": "positive_rate", "expected": 0.548611, "tolerance": 0.000001}
    ])

    assert check["passed"] is True


def test_run_eval_generates_report_without_ollama(tmp_path):
    root = tmp_path
    dataset_path = root / "evals/datasets/retail/tiny_retail.csv"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(
        "Order Date,Sales,Profit,Category\n"
        "2024-01-01,100,20,A\n"
        "2024-01-02,200,30,B\n",
        encoding="utf-8",
    )

    manifest_items = [{
        "id": "tiny_retail",
        "domain": "retail",
        "source_name": "Tiny Retail",
        "source_url": "local:tiny",
        "local_path": "evals/datasets/retail/tiny_retail.csv",
        "format": "csv",
        "acquisition": "local",
        "max_rows": 1000,
        "required": True,
    }]
    for index in range(19):
        manifest_items.append({
            "id": f"optional_missing_{index}",
            "domain": "generic",
            "source_name": f"Optional Missing {index}",
            "source_url": "manual",
            "local_path": f"evals/datasets/generic/missing_{index}.csv",
            "format": "csv",
            "acquisition": "manual_download",
            "max_rows": 1000,
            "required": False,
        })

    manifest_path = root / "evals/manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"datasets": manifest_items}), encoding="utf-8")

    questions_dir = root / "evals/questions"
    questions_dir.mkdir(parents=True)
    (questions_dir / "retail.jsonl").write_text(
        json.dumps({
            "id": "tiny_001",
            "dataset": "retail/tiny_retail.csv",
            "question": "Doanh thu theo category là gì?",
            "expected_domain": "retail",
            "expected_intent": "breakdown",
            "expected_metric_role": "revenue",
            "expected_dimension_role": "category",
            "expected_tool": "semantic_breakdown",
            "numeric_checks": [],
            "answer_must_include": [],
            "answer_must_not_include": ["I guess", "maybe"],
        }) + "\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(
        root=str(root),
        manifest="evals/manifest.json",
        questions="evals/questions",
        out="evals/reports/latest.md",
        mode="fast",
        strict=False,
        enable_semantic_cache=False,
    )
    summary, results = run_eval(args)

    assert (root / "evals/reports/latest.md").exists()
    assert (root / "evals/reports/latest.json").exists()
    assert summary["total_cases"] == 1
    assert results[0]["status"] != "error"
