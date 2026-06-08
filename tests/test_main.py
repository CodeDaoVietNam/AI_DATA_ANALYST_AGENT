"""
HTTP integration tests for the FastAPI app.
Uses TestClient — no server needed, no Ollama needed.
"""
from __future__ import annotations

import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def _small_csv() -> bytes:
    df = pd.DataFrame({"revenue": [100, 200], "category": ["A", "B"]})
    return _csv_bytes(df)


# ── Health Check ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_root_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "ollama" in data
        assert "datasets_count" in data

    def test_request_id_header_present(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers


# ── Upload ───────────────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_valid_csv(self, client):
        resp = client.post(
            "/upload",
            files={"file": ("test.csv", _small_csv(), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dataset_id" in data
        assert data["rows"] == 2
        assert data["columns"] == 2
        assert data["filename"] == "test.csv"

    def test_upload_returns_dataset_id(self, client):
        resp = client.post(
            "/upload",
            files={"file": ("test.csv", _small_csv(), "text/csv")},
        )
        assert resp.status_code == 200
        dataset_id = resp.json()["dataset_id"]
        assert len(dataset_id) == 36  # UUID format

    def test_upload_empty_csv_rejected(self, client):
        empty_csv = b"col1,col2\n"  # header only → empty DataFrame
        resp = client.post(
            "/upload",
            files={"file": ("empty.csv", empty_csv, "text/csv")},
        )
        assert resp.status_code == 400

    def test_upload_file_too_large(self, client, monkeypatch):
        from app import config as cfg_mod
        original = cfg_mod.settings.max_upload_bytes
        try:
            cfg_mod.settings.max_upload_bytes = 10  # 10 bytes limit for test
            resp = client.post(
                "/upload",
                files={"file": ("big.csv", _small_csv(), "text/csv")},
            )
            assert resp.status_code == 413
        finally:
            cfg_mod.settings.max_upload_bytes = original


# ── Datasets List ─────────────────────────────────────────────────────────────

class TestDatasets:
    def test_list_datasets_empty(self, client):
        resp = client.get("/datasets")
        assert resp.status_code == 200
        data = resp.json()
        assert "datasets" in data
        assert isinstance(data["datasets"], list)

    def test_uploaded_dataset_appears_in_list(self, client):
        client.post("/upload", files={"file": ("listed.csv", _small_csv(), "text/csv")})
        resp = client.get("/datasets")
        assert resp.status_code == 200
        filenames = [d["filename"] for d in resp.json()["datasets"]]
        assert "listed.csv" in filenames


# ── Summary ───────────────────────────────────────────────────────────────────

class TestSummary:
    def test_summary_returns_columns(self, client):
        up = client.post("/upload", files={"file": ("s.csv", _small_csv(), "text/csv")})
        dataset_id = up.json()["dataset_id"]

        resp = client.get(f"/summary/{dataset_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data
        assert "revenue" in data["columns"]

    def test_summary_unknown_id_returns_404(self, client):
        resp = client.get("/summary/nonexistent-id")
        assert resp.status_code == 404


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_returns_contract_v2(self, client):
        up = client.post("/upload", files={"file": ("d.csv", _small_csv(), "text/csv")})
        dataset_id = up.json()["dataset_id"]

        resp = client.get(f"/dashboard/{dataset_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("contract_version") == 2
        assert "kpi_cards" in data
        assert "insight_cards" in data
        assert "charts" in data
        assert "tables" in data

    def test_dashboard_unknown_id_returns_400(self, client):
        resp = client.get("/dashboard/nonexistent-id")
        assert resp.status_code == 400
