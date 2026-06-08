import json

import pandas as pd

from app.services.dashboard_builder import build_dashboard


def test_build_retail_dashboard_shape():
    df = pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-02-01"],
        "Sales": [100.0, 200.0],
        "Profit": [10.0, 20.0],
        "Quantity": [1, 2],
        "Segment": ["Consumer", "Corporate"],
        "State": ["A", "B"],
    })

    dashboard = build_dashboard("d1", df)

    assert dashboard["domain"] == "retail"
    assert dashboard["contract_version"] == 2
    assert dashboard["kpi_cards"]
    assert dashboard["charts"]
    assert dashboard["insight_cards"]
    assert {"finding", "why_it_matters", "recommended_next_question"} <= set(dashboard["insight_cards"][0])
    json.dumps(dashboard)


def test_build_marketing_dashboard_shape():
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Campaign_Type": ["Email", "Email", "Ads"],
        "Response": [1, 0, 1],
        "Country": ["A", "A", "B"],
        "Income": [100.0, 200.0, 300.0],
    })

    dashboard = build_dashboard("d1", df)

    assert dashboard["domain"] == "marketing"
    assert any(card["label"] == "Response Rate" for card in dashboard["kpi_cards"])
    json.dumps(dashboard)


def test_build_hr_dashboard_shape():
    df = pd.DataFrame({
        "EmployeeNumber": [1, 2, 3],
        "Attrition": ["Yes", "No", "No"],
        "Department": ["Sales", "Sales", "R&D"],
        "MonthlyIncome": [1000, 2000, 3000],
    })

    dashboard = build_dashboard("d1", df)

    assert dashboard["domain"] == "hr"
    assert any(card["label"] == "Attrition Rate" for card in dashboard["kpi_cards"])
    json.dumps(dashboard)


def test_build_generic_dashboard_missing_roles_does_not_crash():
    df = pd.DataFrame({"A": [1, 2], "B": ["x", None]})

    dashboard = build_dashboard("d1", df)

    assert dashboard["domain"] == "generic"
    assert dashboard["warnings"]
    json.dumps(dashboard)
