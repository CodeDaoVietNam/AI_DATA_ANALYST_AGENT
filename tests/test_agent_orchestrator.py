"""
Integration tests for AgentOrchestrator.
Uses MockOllamaProvider to run deterministically without Ollama.
"""
from __future__ import annotations

import json
import io
import pandas as pd
import pytest

from app.services.agent_orchestrator import AgentOrchestrator
from app.services.storage import DatasetStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

class MockOllamaProvider:
    """Returns deterministic responses without calling Ollama."""

    def __init__(self, route_response: str | None = None, explain_response: str = "Đây là kết quả phân tích."):
        self._route = route_response
        self._explain = explain_response
        self.route_called = 0
        self.explain_called = 0

    def route(self, messages, **kwargs) -> str:
        self.route_called += 1
        if self._route is None:
            raise RuntimeError("Mock: Ollama unavailable")
        return self._route

    def explain(self, messages, **kwargs) -> str:
        self.explain_called += 1
        return self._explain

    def status(self) -> dict:
        return {"available": False, "error": "mock", "model": "mock", "router_model": "mock",
                "model_loaded": False, "router_model_loaded": False, "models": []}


def _make_amazon_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Order ID": ["401-1", "401-2", "401-3"],
        "SKU": ["SKU-A", "SKU-B", "SKU-A"],
        "Category": ["Kurta", "Set", "Kurta"],
        "Amount": [1000.0, 2000.0, 1500.0],
        "Status": ["Shipped", "Cancelled", "Shipped"],
        "ship-city": ["Mumbai", "Delhi", "Pune"],
        "ship-state": ["Maharashtra", "Delhi", "Maharashtra"],
        "Fulfilment": ["Amazon", "Merchant", "Amazon"],
        "Sales Channel ": ["Amazon.in", "Amazon.in", "Amazon.in"],
        "courier-status": ["Shipped", "Cancelled", "Shipped"],
        "Qty": [1, 2, 1],
        "Size": ["M", "L", "S"],
        "B2B": [False, False, True],
        "promotion-ids": ["", "promo1", ""],
        "Date": ["2022-04-01", "2022-04-02", "2022-04-03"],
    })


def _make_generic_df() -> pd.DataFrame:
    return pd.DataFrame({
        "revenue": [100.0, 200.0, 150.0],
        "category": ["A", "B", "A"],
        "quantity": [10, 20, 15],
    })


@pytest.fixture
def tmp_store(tmp_path) -> DatasetStore:
    import app.services.storage as storage_mod
    storage_mod.UPLOAD_DIR = tmp_path
    store = DatasetStore.__new__(DatasetStore)
    store.meta_path = tmp_path / "metadata.json"
    store.datasets = {}
    yield store


def _save_df(store: DatasetStore, df: pd.DataFrame, name: str) -> str:
    df.to_csv(store.meta_path.parent / "tmp.csv", index=False)
    return store.save_dataframe(df, name)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestOllamaFallback:
    def test_fallback_when_llm_route_fails(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        mock = MockOllamaProvider(route_response=None)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Tổng doanh thu là bao nhiêu?")
        assert isinstance(result, dict)
        assert "answer" in result
        assert result["answer"]

    def test_fallback_explanation_source_marked(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        mock = MockOllamaProvider(route_response=None)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Category nào doanh thu cao nhất?")
        assert result.get("explanation_source") in {"deterministic_fallback", "llm"}


class TestResponseStructure:
    def test_required_fields_present(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "get_dataset_overview", "arguments": {}, "purpose": "overview"}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Tổng quan dataset?")
        for field in ["answer", "warnings", "execution_timeline", "latency"]:
            assert field in result, f"Missing field: {field}"

    def test_answer_card_present_in_fast_mode(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        mock = MockOllamaProvider(route_response=None)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Category nào doanh thu cao nhất?", mode="fast")

        assert result["answer_card"]
        assert result["answer_card"]["headline"]
        assert result["answer_card"]["evidence"]
        assert "Bằng chứng" in result["answer"]

    def test_execution_timeline_populated(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "get_dataset_overview", "arguments": {}}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Tổng quan?")
        assert isinstance(result["execution_timeline"], list)
        assert len(result["execution_timeline"]) > 0

    def test_latency_has_total_ms(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "get_dataset_overview", "arguments": {}}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Tổng quan?")
        assert "total_ms" in result.get("latency", {})


class TestChartOutput:
    def test_chart_request_returns_chart(self, tmp_store):
        df = _make_generic_df()
        dataset_id = _save_df(tmp_store, df, "test.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "generate_chart_spec", "arguments": {"chart_type": "bar", "x": "category", "y": "revenue"}}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        result = orch.chat(dataset_id, "Vẽ biểu đồ revenue theo category")
        assert result.get("chart") is not None
        chart = result["chart"]
        assert "data" in chart and "layout" in chart


class TestStreamChat:
    def test_stream_yields_final_event(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "get_dataset_overview", "arguments": {}}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        events = list(orch.stream_chat(dataset_id, "Tổng quan?"))
        event_names = [e["event"] for e in events]
        assert "final" in event_names

    def test_stream_yields_progress_events(self, tmp_store):
        df = _make_amazon_df()
        dataset_id = _save_df(tmp_store, df, "amazon.csv")
        plan_json = json.dumps({"steps": [{"tool_name": "get_dataset_overview", "arguments": {}}]})
        mock = MockOllamaProvider(route_response=plan_json)
        orch = AgentOrchestrator(provider=mock, store=tmp_store)

        events = list(orch.stream_chat(dataset_id, "Tổng quan?"))
        event_names = [e["event"] for e in events]
        assert "progress" in event_names
