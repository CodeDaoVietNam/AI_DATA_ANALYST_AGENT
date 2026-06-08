from __future__ import annotations

from typing import Any


def insight_card(
    *,
    title: str,
    finding: str,
    evidence: str,
    why_it_matters: str,
    recommended_next_question: str,
    tone: str = "neutral",
    severity: str = "info",
    confidence: float = 0.75,
    related_chart_id: str | None = None,
    related_table_id: str | None = None,
) -> dict[str, Any]:
    value = finding
    return {
        "title": title,
        "value": value,
        "narrative": f"{finding} {why_it_matters}",
        "finding": finding,
        "evidence": evidence,
        "why_it_matters": why_it_matters,
        "recommended_next_question": recommended_next_question,
        "tone": tone,
        "severity": severity,
        "confidence": confidence,
        "related_chart_id": related_chart_id,
        "related_table_id": related_table_id,
    }


def top_metric_insight(
    *,
    title: str,
    rows: list[dict[str, Any]],
    label_key: str,
    metric_key: str,
    metric_label: str,
    next_question: str,
    why_it_matters: str,
    tone: str = "positive",
    related_chart_id: str | None = None,
    related_table_id: str | None = None,
    percent: bool = False,
) -> dict[str, Any] | None:
    if not rows or label_key not in rows[0] or metric_key not in rows[0]:
        return None
    top = rows[0]
    formatted_metric = _pct(top[metric_key]) if percent else _fmt(top[metric_key])
    label = str(top[label_key])
    return insight_card(
        title=title,
        finding=f"{label} leads on {metric_label}.",
        evidence=f"{metric_label}: {formatted_metric}",
        why_it_matters=why_it_matters,
        recommended_next_question=next_question,
        tone=tone,
        severity="info" if tone != "risk" else "warning",
        confidence=0.82,
        related_chart_id=related_chart_id,
        related_table_id=related_table_id,
    )


def risk_metric_insight(
    *,
    title: str,
    rows: list[dict[str, Any]],
    label_key: str,
    risk_key: str,
    next_question: str,
    why_it_matters: str,
    related_chart_id: str | None = None,
    related_table_id: str | None = None,
) -> dict[str, Any] | None:
    if not rows or label_key not in rows[0] or risk_key not in rows[0]:
        return None
    top = rows[0]
    return insight_card(
        title=title,
        finding=f"{top[label_key]} is the highest-risk group.",
        evidence=f"{risk_key}: {_pct(top[risk_key])}",
        why_it_matters=why_it_matters,
        recommended_next_question=next_question,
        tone="risk",
        severity="warning",
        confidence=0.78,
        related_chart_id=related_chart_id,
        related_table_id=related_table_id,
    )


def _fmt(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return "N/A" if value is None else str(value)


def _pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "N/A" if value is None else str(value)
