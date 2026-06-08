import pandas as pd

from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.dashboard_builder import build_dashboard
from app.services.storage import dataset_store


client = TestClient(app)


class NoLLMProvider:
    def route(self, messages, **kwargs):
        raise RuntimeError("no llm")

    def explain(self, messages, **kwargs):
        raise RuntimeError("no llm")

    def status(self):
        return {"available": False}


def _retail_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-01-02", "2024-02-01"],
        "Sales": [100.0, 200.0, 300.0],
        "Profit": [10.0, 40.0, 30.0],
        "Category": ["A", "A", "B"],
        "Segment": ["Consumer", "Corporate", "Consumer"],
    })


def test_metric_crud_and_evaluate_api():
    dataset_id = dataset_store.save_dataframe(_retail_df(), "retail.csv")
    payload = {
        "name": "margin",
        "label": "Margin",
        "expression": "profit / revenue",
        "format": "percent",
        "aggregation": "mean",
        "required_roles": ["profit", "revenue"],
    }

    create_response = client.post(f"/datasets/{dataset_id}/metrics", json=payload)
    assert create_response.status_code == 200, create_response.text
    assert create_response.json()["metric"]["name"] == "margin"

    list_response = client.get(f"/datasets/{dataset_id}/metrics")
    assert list_response.status_code == 200
    assert len(list_response.json()["metrics"]) == 1

    eval_response = client.post(f"/datasets/{dataset_id}/metrics/margin/evaluate")
    assert eval_response.status_code == 200
    assert eval_response.json()["summary"]["value"] is not None

    delete_response = client.delete(f"/datasets/{dataset_id}/metrics/margin")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def test_custom_metric_appears_in_dashboard():
    df = _retail_df()
    dataset_id = dataset_store.save_dataframe(df, "retail_dashboard.csv")
    dataset_store.set_custom_metric(dataset_id, {
        "name": "margin",
        "label": "Margin",
        "expression": "profit / revenue",
        "format": "percent",
        "aggregation": "mean",
        "required_roles": ["profit", "revenue"],
        "higher_is_better": True,
    })

    dashboard = build_dashboard(dataset_id, df)

    assert any(card["label"] == "Margin" for card in dashboard["kpi_cards"])
    assert any(table["id"] == "custom_metrics" for table in dashboard["tables"])


def test_agent_routes_custom_metric_breakdown():
    df = _retail_df()
    dataset_id = dataset_store.save_dataframe(df, "retail_agent.csv")
    dataset_store.set_custom_metric(dataset_id, {
        "name": "margin",
        "label": "Margin",
        "expression": "profit / revenue",
        "format": "percent",
        "aggregation": "mean",
        "required_roles": ["profit", "revenue"],
        "higher_is_better": True,
    })
    orchestrator = AgentOrchestrator(provider=NoLLMProvider(), store=dataset_store)

    result = orchestrator.chat(dataset_id, "margin theo category như thế nào?", mode="fast")

    assert result["tool_call"]["tool_name"] == "custom_metric_breakdown"
    assert result["data"]
