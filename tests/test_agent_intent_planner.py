import pandas as pd

from app.services.agent_orchestrator import AgentOrchestrator
from app.services.storage import dataset_store


class NoLLMProvider:
    def route(self, messages, **kwargs):
        raise RuntimeError("no llm")

    def explain(self, messages, **kwargs):
        raise RuntimeError("no llm")

    def status(self):
        return {"available": False}


def _retail_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Order Date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "Sales": [100.0, 200.0, 300.0],
        "Profit": [10.0, 50.0, 30.0],
        "Category": ["A", "B", "A"],
        "Segment": ["Consumer", "Corporate", "Consumer"],
    })


def test_agent_uses_intent_for_custom_metric_breakdown_without_llm():
    dataset_id = dataset_store.save_dataframe(_retail_df(), "intent_retail.csv")
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
    assert result["agent_plan"]["strategy"] == "intent:breakdown"
    assert result["agent_plan"]["intent"]["metric"] == "margin"
    assert any(item["step"] == "parsed_intent" for item in result["execution_timeline"])


def test_agent_uses_intent_for_semantic_breakdown_without_llm():
    dataset_id = dataset_store.save_dataframe(_retail_df(), "intent_retail_semantic.csv")
    orchestrator = AgentOrchestrator(provider=NoLLMProvider(), store=dataset_store)

    result = orchestrator.chat(dataset_id, "doanh thu theo category", mode="fast")

    assert result["tool_call"]["tool_name"] == "semantic_breakdown"
    assert result["agent_plan"]["intent"]["task"] == "breakdown"
    assert result["agent_plan"]["intent"]["metric"] == "revenue"


def test_agent_uses_intent_for_trend_without_llm():
    dataset_id = dataset_store.save_dataframe(_retail_df(), "intent_retail_trend.csv")
    orchestrator = AgentOrchestrator(provider=NoLLMProvider(), store=dataset_store)

    result = orchestrator.chat(dataset_id, "doanh thu theo tháng", mode="fast")

    assert result["tool_call"]["tool_name"] == "semantic_time_series"
    assert result["agent_plan"]["intent"]["task"] == "trend"
