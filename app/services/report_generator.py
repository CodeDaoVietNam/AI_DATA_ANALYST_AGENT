from typing import Dict, Any


def generate_markdown_report(filename: str, summary: Dict[str, Any]) -> str:
    lines = []

    lines.append(f"# EDA Report: {filename}")
    lines.append("")
    lines.append("## 1. Dataset Overview")
    lines.append(f"- Rows: {summary['shape']['rows']}")
    lines.append(f"- Columns: {summary['shape']['columns']}")
    lines.append(f"- Duplicate rows: {summary['duplicate_rows']}")
    lines.append("")

    lines.append("## 2. Columns")
    for col, typ in summary["column_types"].items():
        lines.append(f"- `{col}`: {typ}")
    lines.append("")

    lines.append("## 3. Missing Values")
    for col, missing in summary["missing_values"].items():
        pct = summary["missing_percent"].get(col, 0)
        lines.append(f"- `{col}`: {missing} missing ({pct}%)")
    lines.append("")

    lines.append("## 4. Recommended Analysis")
    for rec in summary["recommendations"]:
        lines.append(f"- {rec}")
    lines.append("")

    lines.append("## 5. Notes")
    lines.append(
        "This report is generated from deterministic Pandas-based analysis. "
        "LLM-generated insights should be added only after tool results are available."
    )

    return "\n".join(lines)
