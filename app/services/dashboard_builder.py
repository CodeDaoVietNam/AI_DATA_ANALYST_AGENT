from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.chart_generator import generate_chart_spec
from app.services.dashboard_insight_engine import insight_card, risk_metric_insight, top_metric_insight
from app.services.data_cleaner import clean_amazon_sales_data
from app.services.feature_engineering import add_amazon_sales_features
from app.services.generic_insight_engine import generate_generic_insights
from app.services.metric_builder import evaluate_metric_summary, metric_breakdown
from app.services.semantic_mapper import DatasetSemanticProfile, build_semantic_profile
from app.services.storage import dataset_store
from app.tools.domain_analysis_tools import (
    generic_numeric_distributions,
    generic_top_categorical_values,
    hr_attrition_by_role,
    hr_high_risk_segments,
    hr_income_band_attrition,
    hr_tenure_risk,
    marketing_campaign_acceptance,
    marketing_income_band_response,
    marketing_purchase_channel_summary,
    marketing_response_by_segment,
    marketing_rfm_summary,
    retail_discount_effect,
    retail_interaction,
    retail_loss_analysis,
    retail_margin_summary,
    retail_top_opportunities,
)
from app.tools.ecommerce_tools import (
    category_cancellation_summary,
    get_sales_overview,
    revenue_by_category,
    revenue_by_month,
    top_states_by_revenue,
)
from app.tools.generic_analysis_tools import (
    correlation_analysis,
    get_duplicate_rows,
    get_missing_values,
    semantic_breakdown,
    semantic_kpis,
    semantic_target_summary,
    semantic_time_series,
)


def build_dashboard(
    dataset_id: str,
    df: pd.DataFrame,
    profile: DatasetSemanticProfile | None = None,
) -> dict[str, Any]:
    semantic_profile = profile or build_semantic_profile(df)
    custom_metrics = _load_custom_metrics(dataset_id)
    if semantic_profile.domain == "ecommerce":
        dashboard = _ecommerce_dashboard(dataset_id, df, semantic_profile)
    elif semantic_profile.domain == "retail":
        dashboard = _retail_dashboard(dataset_id, df, semantic_profile)
    elif semantic_profile.domain == "marketing":
        dashboard = _marketing_dashboard(dataset_id, df, semantic_profile)
    elif semantic_profile.domain == "hr":
        dashboard = _hr_dashboard(dataset_id, df, semantic_profile)
    elif semantic_profile.domain == "finance":
        dashboard = _finance_dashboard(dataset_id, df, semantic_profile)
    else:
        dashboard = _generic_dashboard(dataset_id, df, semantic_profile)
    _apply_custom_metrics(dashboard, df, semantic_profile, custom_metrics)
    _apply_generic_insights(dashboard, df, semantic_profile, custom_metrics)
    return dashboard


def _base(dataset_id: str, profile: DatasetSemanticProfile) -> dict[str, Any]:
    return {
        "contract_version": 2,
        "dataset_id": dataset_id,
        "domain": profile.domain,
        "semantic_profile": profile.to_dict(),
        "kpi_cards": [],
        "insight_cards": [],
        "charts": [],
        "tables": [],
        "warnings": list(profile.warnings),
    }


def _ecommerce_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    prepared = add_amazon_sales_features(clean_amazon_sales_data(df))
    overview = get_sales_overview(prepared)
    category_rows = revenue_by_category(prepared)
    month_rows = revenue_by_month(prepared)
    state_rows = top_states_by_revenue(prepared, n=10)
    category_risk = category_cancellation_summary(prepared)

    dashboard["kpi_cards"] = [
        _card("Revenue", _fmt(overview["total_revenue"]), "Available amount sum"),
        _card("Orders", _fmt(overview["unique_orders"]), "Unique order count"),
        _card("Cancel Rate", _pct(overview["cancel_rate"]), "Cancelled row rate", "warning"),
        _card("Quantity", _fmt(overview["total_qty"]), "Total units"),
    ]
    _add_table(dashboard, "ecom_category", "Revenue by Category", "Top categories by revenue.", category_rows)
    _add_table(dashboard, "ecom_state", "Top States", "Top shipping states by revenue.", state_rows)
    _add_table(dashboard, "ecom_category_risk", "Category Cancellation Risk", "Cancellation rate by category.", category_risk)
    _chart_from_rows(dashboard, "ecom_month_chart", "Revenue by Month", "Monthly ecommerce revenue.", month_rows, "order_month", "revenue", "line")
    _chart_from_rows(dashboard, "ecom_category_chart", "Revenue by Category", "Category revenue distribution.", category_rows[:10], "category", "revenue")
    _append_insight(dashboard, top_metric_insight(
        title="Category Revenue Leader",
        rows=category_rows,
        label_key="category",
        metric_key="revenue",
        metric_label="revenue",
        why_it_matters="This category is the first place to inspect for merchandising and inventory decisions.",
        next_question="Category nào revenue cao nhưng cancel rate cũng cao?",
        related_chart_id="ecom_category_chart",
        related_table_id="ecom_category",
    ))
    _append_insight(dashboard, risk_metric_insight(
        title="Cancellation Risk",
        rows=category_risk,
        label_key="category",
        risk_key="cancel_rate",
        why_it_matters="High cancellation can erase revenue quality and signal fulfilment or product expectation issues.",
        next_question="Vì sao category này có cancellation risk cao?",
        related_table_id="ecom_category_risk",
    ))
    return dashboard


def _retail_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    kpis = semantic_kpis(df, profile)
    margin = retail_margin_summary(df, profile)
    losses = retail_loss_analysis(df, profile, by_role="category")
    discounts = retail_discount_effect(df, profile)
    interactions = retail_interaction(df, profile)
    opportunities = retail_top_opportunities(df, profile)

    dashboard["kpi_cards"] = _business_kpis(kpis)
    if "margin" in margin:
        dashboard["kpi_cards"].append(_card("Margin", _pct(margin["margin"]), "Profit divided by revenue", "positive" if (margin["margin"] or 0) >= 0 else "warning"))
    _semantic_sections(dashboard, df, profile, category_roles=["category", "state", "segment"])
    _add_table(dashboard, "retail_losses", "Loss-Making Groups", "Groups where total profit is below zero.", losses)
    _add_table(dashboard, "retail_discount", "Discount Effect", "Revenue/profit by discount band.", discounts.get("items", []))
    if discounts.get("warning"):
        dashboard["warnings"].append(discounts["warning"])
    _add_table(dashboard, "retail_interaction", "Segment-State-Category Interaction", "Cross-section view for retail performance.", interactions)
    _add_table(dashboard, "retail_opportunity", "High Revenue / Low Margin Opportunities", "Large revenue groups with weak margin.", opportunities)
    _append_insight(dashboard, insight_card(
        title="Margin Health",
        finding=f"Overall margin is {_pct(margin.get('margin'))}.",
        evidence=f"Revenue {_fmt(margin.get('total_revenue'))}, profit {_fmt(margin.get('total_profit'))}.",
        why_it_matters="Margin reveals whether sales volume is translating into profit.",
        recommended_next_question="Segment nào margin thấp dù sales cao?",
        tone="positive" if (margin.get("margin") or 0) >= 0 else "risk",
        severity="info" if (margin.get("margin") or 0) >= 0 else "warning",
        related_table_id="retail_opportunity",
    ))
    if opportunities:
        _append_insight(dashboard, top_metric_insight(
            title="Margin Opportunity",
            rows=opportunities,
            label_key=_first_group_key(opportunities),
            metric_key="revenue",
            metric_label="revenue with low margin",
            why_it_matters="These groups deserve pricing, discount, or cost review before scaling further.",
            next_question="Giải thích nhóm high revenue low margin này theo state và segment.",
            tone="risk",
            related_table_id="retail_opportunity",
        ))
    return dashboard


def _finance_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    kpis = semantic_kpis(df, profile)
    dashboard["kpi_cards"] = _business_kpis(kpis)
    _semantic_sections(dashboard, df, profile, category_roles=["category", "state"])
    return dashboard


def _marketing_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    kpis = semantic_kpis(df, profile)
    target = semantic_target_summary(df, profile, by_role="campaign")
    country_response = marketing_response_by_segment(df, profile, by_role="country")
    campaign_acceptance = marketing_campaign_acceptance(df, profile)
    rfm = marketing_rfm_summary(df, profile)
    income_response = marketing_income_band_response(df, profile)
    channels = marketing_purchase_channel_summary(df)

    dashboard["kpi_cards"] = [
        _card("Customers", _fmt(df.shape[0]), "Rows in dataset"),
        _card("Response Rate", _pct(target.get("positive_rate")), "Positive response/conversion", "positive"),
    ]
    if "salary" in kpis:
        dashboard["kpi_cards"].append(_card("Income Total", _fmt(kpis["salary"]), "Sum of income-like field"))
    _add_table(dashboard, "mkt_campaign_response", "Response by Campaign", "Target/conversion rate by campaign role.", target.get("by_group", []))
    _add_table(dashboard, "mkt_country_response", "Response by Country/Segment", "Conversion by detected customer group.", country_response.get("items", []))
    _add_table(dashboard, "mkt_campaign_acceptance", "Campaign Acceptance", "Acceptance rate across campaign columns.", campaign_acceptance)
    _add_table(dashboard, "mkt_income_response", "Income Band Response", "Response rate by income band.", income_response.get("items", []))
    _add_table(dashboard, "mkt_channels", "Purchase Channel Summary", "Purchases by web/catalog/store/deals.", channels)
    if rfm.get("items"):
        _add_table(dashboard, "mkt_rfm", "RFM-Like Segments", "Monetary and frequency behavior by band.", rfm.get("items", []))
    
    # Default visual charts for Marketing
    _chart_from_rows(
        dashboard, 
        "mkt_campaign_chart", 
        "Response by Campaign", 
        "Acceptance rate across marketing campaigns.", 
        target.get("by_group", []), 
        target.get("group_column", "Campaign"), 
        "positive_rate", 
        "bar"
    )
    _chart_from_rows(
        dashboard, 
        "mkt_channels_chart", 
        "Dominant Purchase Channels", 
        "Total purchases by channels (Web, Catalog, Store, Deals).", 
        channels, 
        "channel", 
        "total_purchases", 
        "pie"
    )
    _chart_from_rows(
        dashboard, 
        "mkt_income_chart", 
        "Response Rate by Income Band", 
        "Response rate based on customer income level.", 
        income_response.get("items", []), 
        "income_band", 
        "positive_rate", 
        "bar"
    )

    _append_insight(dashboard, risk_metric_insight(
        title="Best Response Segment",
        rows=target.get("by_group", []),
        label_key=_first_group_key(target.get("by_group", [])),
        risk_key="positive_rate",
        why_it_matters="High response segments are the best starting point for campaign targeting and budget allocation.",
        next_question="Campaign nào response tốt nhất và nhóm khách hàng nào nên ưu tiên?",
        related_table_id="mkt_campaign_response",
        related_chart_id="mkt_campaign_chart",
    ))
    if channels:
        _append_insight(dashboard, top_metric_insight(
            title="Dominant Purchase Channel",
            rows=channels,
            label_key="channel",
            metric_key="total_purchases",
            metric_label="total purchases",
            why_it_matters="Channel concentration helps prioritize acquisition and retention work.",
            next_question="Channel mua hàng nào có tương quan với response cao?",
            related_table_id="mkt_channels",
            related_chart_id="mkt_channels_chart",
        ))
    return dashboard


def _hr_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    kpis = semantic_kpis(df, profile)
    department = hr_attrition_by_role(df, profile, by_role="department", min_rows=1)
    job_role = hr_attrition_by_role(df, profile, by_role="job_role", min_rows=1)
    overtime = hr_attrition_by_role(df, profile, by_role="overtime", min_rows=1)
    income_band = hr_income_band_attrition(df, profile)
    tenure = hr_tenure_risk(df, profile)
    high_risk = hr_high_risk_segments(df, profile, min_rows=1)

    dashboard["kpi_cards"] = [
        _card("Employees", _fmt(df.shape[0]), "Rows in dataset"),
        _card("Attrition Rate", _pct(kpis.get("target_rate")), "Positive attrition/target rate", "warning"),
    ]
    if "salary" in kpis:
        dashboard["kpi_cards"].append(_card("Income Total", _fmt(kpis["salary"]), "Sum of salary/income role"))
    _add_table(dashboard, "hr_department", "Attrition by Department", "Target rate by department.", department.get("items", []))
    _add_table(dashboard, "hr_job_role", "Attrition by Job Role", "Target rate by job role.", job_role.get("items", []))
    _add_table(dashboard, "hr_overtime", "Attrition by Overtime", "Target rate by overtime.", overtime.get("items", []))
    _add_table(dashboard, "hr_income", "Income Band Attrition", "Attrition by salary/income band.", income_band.get("items", []))
    _add_table(dashboard, "hr_tenure", "Tenure Risk", "Attrition by tenure band.", tenure.get("items", []))
    _add_table(dashboard, "hr_high_risk", "High-Risk Segments", "Combined department/job/overtime segments.", high_risk)

    # Default visual charts for HR Attrition
    _chart_from_rows(
        dashboard, 
        "hr_dept_chart", 
        "Attrition Rate by Department", 
        "Attrition rate comparison across business units.", 
        department.get("items", []), 
        department.get("group_column", "Department"), 
        "positive_rate", 
        "bar"
    )
    _chart_from_rows(
        dashboard, 
        "hr_income_chart", 
        "Attrition by Income Band", 
        "Monthly salary band attrition rate.", 
        income_band.get("items", []), 
        "income_band", 
        "attrition_rate", 
        "bar"
    )
    _chart_from_rows(
        dashboard, 
        "hr_overtime_chart", 
        "Attrition by Overtime Status", 
        "Attrition rates for employees who work overtime vs those who do not.", 
        overtime.get("items", []), 
        overtime.get("group_column", "OverTime"), 
        "positive_rate", 
        "bar"
    )

    _append_insight(dashboard, risk_metric_insight(
        title="Highest Attrition Group",
        rows=department.get("items", []),
        label_key=_first_group_key(department.get("items", [])),
        risk_key="positive_rate",
        why_it_matters="This is the first group to inspect for retention risk.",
        next_question="Nhóm nhân viên nào attrition risk cao nhất và vì sao?",
        related_table_id="hr_department",
        related_chart_id="hr_dept_chart",
    ))
    if high_risk:
        _append_insight(dashboard, risk_metric_insight(
            title="Combined Risk Segment",
            rows=high_risk,
            label_key=_first_group_key(high_risk),
            risk_key="attrition_rate",
            why_it_matters="Combined segments usually reveal sharper operational risk than single-column summaries.",
            next_question="Phân tích high-risk segment này theo income và tenure.",
            related_table_id="hr_high_risk",
        ))
    return dashboard


def _generic_dashboard(dataset_id: str, df: pd.DataFrame, profile: DatasetSemanticProfile) -> dict[str, Any]:
    dashboard = _base(dataset_id, profile)
    missing = get_missing_values(df)
    duplicates = get_duplicate_rows(df)
    numeric = generic_numeric_distributions(df)
    categorical = generic_top_categorical_values(df)
    correlations = correlation_analysis(df)
    dashboard["kpi_cards"] = [
        _card("Rows", _fmt(df.shape[0]), "Dataset rows"),
        _card("Columns", _fmt(df.shape[1]), "Dataset columns"),
        _card("Duplicate Rows", _fmt(duplicates["duplicate_rows"]), "Exact duplicate rows"),
        _card("Missing Columns", _fmt(len(missing["columns_with_missing"])), "Columns with missing values"),
    ]
    _add_table(
        dashboard,
        "generic_missing",
        "Missing Values",
        "Missing count and percent by column.",
        [{"column": col, "missing": missing["missing_values"][col], "missing_percent": missing["missing_percent"][col]} for col in missing["missing_values"]],
    )
    _add_table(dashboard, "generic_numeric", "Numeric Distributions", "Basic numeric stats by column.", numeric)
    _add_table(dashboard, "generic_categorical", "Top Categorical Values", "Frequent values for low-cardinality text columns.", categorical)
    _add_table(dashboard, "generic_correlation", "Correlation Highlights", "Pairwise numeric correlations.", correlations.get("correlations", []))

    # Default visual charts for Generic data
    missing_items = [{"column": col, "missing": missing["missing_values"][col], "missing_percent": missing["missing_percent"][col]} for col in missing["missing_values"] if missing["missing_values"][col] > 0]
    if missing_items:
        _chart_from_rows(
            dashboard,
            "generic_missing_chart",
            "Missing Values by Column",
            "Percentage of missing data across columns.",
            missing_items,
            "column",
            "missing_percent",
            "bar"
        )
    corr_items = [item for item in correlations.get("correlations", []) if item["column_a"] != item["column_b"] and item["correlation"] is not None]
    if corr_items:
        _chart_from_rows(
            dashboard,
            "generic_correlation_chart",
            "Pairwise Correlations",
            "Key linear relationship strengths between numeric features.",
            corr_items[:15],
            "column_a",
            "correlation",
            "bar"
        )

    _append_insight(dashboard, insight_card(
        title="Data Quality Starting Point",
        finding=f"{len(missing['columns_with_missing'])} columns contain missing values.",
        evidence=f"Duplicate rows: {duplicates['duplicate_rows']}.",
        why_it_matters="Quality issues shape which metrics are trustworthy before deeper modeling.",
        recommended_next_question="Cột nào thiếu dữ liệu nhiều nhất và ảnh hưởng ra sao?",
        tone="risk" if missing["columns_with_missing"] else "positive",
        severity="warning" if missing["columns_with_missing"] else "info",
        related_table_id="generic_missing",
        related_chart_id="generic_missing_chart" if missing_items else None,
    ))
    return dashboard


def _load_custom_metrics(dataset_id: str) -> list[dict[str, Any]]:
    try:
        return dataset_store.get_custom_metrics(dataset_id)
    except Exception:
        return []


def _apply_custom_metrics(
    dashboard: dict[str, Any],
    df: pd.DataFrame,
    profile: DatasetSemanticProfile,
    custom_metrics: list[dict[str, Any]],
) -> None:
    if not custom_metrics:
        return
    summaries: list[dict[str, Any]] = []
    for definition in custom_metrics:
        try:
            summary = evaluate_metric_summary(df, profile, definition)
        except Exception as exc:
            dashboard["warnings"].append(f"Custom metric `{definition.get('name', 'unknown')}` could not be evaluated: {exc}")
            continue
        summaries.append(summary)
        dashboard["kpi_cards"].append(_card(
            summary["label"],
            _fmt_metric_value(summary.get("value"), summary.get("format")),
            f"Custom metric: {summary.get('expression')}",
            "positive" if definition.get("higher_is_better", True) else "neutral",
        ))

    if summaries:
        _add_table(
            dashboard,
            "custom_metrics",
            "Custom Metrics",
            "User-defined metrics evaluated from semantic roles or columns.",
            summaries,
        )

    first_metric = custom_metrics[0] if custom_metrics else None
    if not first_metric:
        return
    by_role = next((role for role in ["category", "segment", "state", "country", "department"] if role in profile.roles), None)
    if not by_role:
        return
    try:
        rows = metric_breakdown(df, profile, first_metric, by_role=by_role, limit=20)
    except Exception as exc:
        dashboard["warnings"].append(f"Custom metric breakdown failed for `{first_metric.get('name')}`: {exc}")
        return
    if rows:
        metric_name = first_metric.get("name", "custom_metric")
        by_col = profile.roles[by_role].column
        table_id = f"custom_metric_{metric_name}_by_{by_role}"
        chart_id = f"{table_id}_chart"
        _add_table(dashboard, table_id, f"{metric_name} by {by_col}", f"Custom metric breakdown by {by_role}.", rows)
        _chart_from_rows(dashboard, chart_id, f"{metric_name} by {by_col}", "Custom metric by semantic dimension.", rows[:10], by_col, metric_name)
        _append_insight(dashboard, top_metric_insight(
            title=f"Top {first_metric.get('label') or metric_name}",
            rows=rows,
            label_key=by_col,
            metric_key=metric_name,
            metric_label=metric_name,
            why_it_matters="Custom metrics encode user-specific business logic, so their leaders are strong candidates for follow-up analysis.",
            next_question=f"Vì sao {by_role} này dẫn đầu theo {metric_name}?",
            related_chart_id=chart_id,
            related_table_id=table_id,
            percent=first_metric.get("format") == "percent",
        ))


def _apply_generic_insights(
    dashboard: dict[str, Any],
    df: pd.DataFrame,
    profile: DatasetSemanticProfile,
    custom_metrics: list[dict[str, Any]],
) -> None:
    target_count = 8 if profile.domain in {"generic", "finance"} else 5
    if len(dashboard["insight_cards"]) >= target_count:
        return
    existing_ids = {card.get("id") for card in dashboard["insight_cards"] if isinstance(card, dict)}
    needed = target_count - len(dashboard["insight_cards"])
    for card in generate_generic_insights(df, profile, custom_metrics, max_insights=needed + 3):
        if card.get("id") in existing_ids:
            continue
        dashboard["insight_cards"].append(card)
        existing_ids.add(card.get("id"))
        if len(dashboard["insight_cards"]) >= target_count:
            break


def _semantic_sections(dashboard: dict[str, Any], df: pd.DataFrame, profile: DatasetSemanticProfile, category_roles: list[str]) -> None:
    time_rows = semantic_time_series(df, profile)
    if time_rows:
        metric = next((key for key in time_rows[0] if key != "period"), None)
        if metric:
            _chart_from_rows(dashboard, "semantic_trend_chart", "Trend Over Time", "Semantic metric by month.", time_rows, "period", metric, "line")
            _add_table(dashboard, "semantic_trend", "Trend Over Time", "Monthly semantic metric.", time_rows)

    metric_role = "revenue" if "revenue" in profile.roles else "profit" if "profit" in profile.roles else "quantity"
    for role in category_roles:
        rows = semantic_breakdown(df, profile, by_role=role, metric_role=metric_role)
        if rows and role in profile.roles and metric_role in profile.roles:
            by_col = profile.roles[role].column
            metric_col = profile.roles[metric_role].column
            table_id = f"semantic_{role}"
            chart_id = f"semantic_{role}_chart"
            _add_table(dashboard, table_id, f"{metric_col} by {by_col}", f"Top {role} groups by {metric_role}.", rows)
            _chart_from_rows(dashboard, chart_id, f"{metric_col} by {by_col}", f"Top {role} groups.", rows[:10], by_col, metric_col)
            _append_insight(dashboard, top_metric_insight(
                title=f"Top {role.title()}",
                rows=rows,
                label_key=by_col,
                metric_key=metric_col,
                metric_label=metric_role,
                why_it_matters="This group is the clearest starting point for drilling into business performance.",
                next_question=f"Vì sao {role} này dẫn đầu về {metric_role}?",
                related_chart_id=chart_id,
                related_table_id=table_id,
            ))


def _business_kpis(kpis: dict[str, Any]) -> list[dict[str, str]]:
    cards = [_card("Rows", _fmt(kpis["rows"]), "Dataset rows")]
    for role, label in [("revenue", "Revenue"), ("profit", "Profit"), ("cost", "Cost"), ("quantity", "Quantity"), ("salary", "Salary/Income")]:
        if role in kpis:
            cards.append(_card(label, _fmt(kpis[role]), f"Sum of semantic role `{role}`"))
    if "target_rate" in kpis:
        cards.append(_card("Target Rate", _pct(kpis["target_rate"]), "Positive target/conversion rate"))
    return cards


def _chart_from_rows(
    dashboard: dict[str, Any],
    chart_id: str,
    title: str,
    description: str,
    rows: list[dict[str, Any]],
    x: str,
    y: str,
    chart_type: str = "bar",
) -> None:
    if not rows or x not in rows[0] or y not in rows[0]:
        return
    chart_df = pd.DataFrame(rows)
    try:
        chart = generate_chart_spec(chart_df, chart_type, x, y)
    except Exception as exc:
        dashboard["warnings"].append(f"Could not generate chart '{title}': {exc}")
        return
    dashboard["charts"].append({"id": chart_id, "title": title, "description": description, "chart": chart})


def _add_table(dashboard: dict[str, Any], table_id: str, title: str, description: str, rows: list[dict[str, Any]]) -> None:
    if rows is None:
        rows = []
    dashboard["tables"].append({"id": table_id, "title": title, "description": description, "rows": rows})


def _append_insight(dashboard: dict[str, Any], card: dict[str, Any] | None) -> None:
    if card:
        dashboard["insight_cards"].append(card)


def _first_group_key(rows: list[dict[str, Any]] | None) -> str | None:
    if not rows:
        return None
    for key in rows[0]:
        if key not in {"rows", "positive_rate", "attrition_rate", "positives", "revenue", "profit", "margin"}:
            return key
    return None


def _card(label: str, value: str, description: str, tone: str = "neutral") -> dict[str, str]:
    return {"label": label, "value": value, "description": description, "tone": tone}


def _fmt(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return "N/A" if value is None else str(value)


def _pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "N/A" if value is None else str(value)


def _fmt_metric_value(value: Any, metric_format: str | None) -> str:
    if not isinstance(value, (int, float)):
        return "N/A" if value is None else str(value)
    if metric_format == "percent":
        return _pct(value)
    if metric_format == "currency":
        return f"{value:,.2f}"
    if metric_format == "integer":
        return f"{value:,.0f}"
    return f"{value:,.2f}"
