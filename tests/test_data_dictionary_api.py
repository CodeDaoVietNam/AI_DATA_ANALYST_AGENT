import io

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _upload_dataset() -> str:
    df = pd.DataFrame({
        "amt": [100.0, 200.0],
        "dt": ["2024-01-01", "2024-01-02"],
        "prod_grp": ["A", "B"],
    })
    response = client.post("/upload", files={"file": ("data.csv", _csv_bytes(df), "text/csv")})
    assert response.status_code == 200
    return response.json()["dataset_id"]


def test_upload_get_delete_data_dictionary_csv():
    dataset_id = _upload_dataset()
    dictionary_csv = b"""column_name,business_name,semantic_role,data_type,aggregation,sensitive,allowed_values
amt,Revenue,revenue,number,sum,false,
dt,Order Date,date,date,,false,
prod_grp,Product Group,category,string,,false,A|B
"""

    upload = client.post(
        f"/datasets/{dataset_id}/data-dictionary",
        files={"file": ("dictionary.csv", dictionary_csv, "text/csv")},
    )
    assert upload.status_code == 200
    assert upload.json()["dictionary"]["domain"] is None

    get_response = client.get(f"/datasets/{dataset_id}/data-dictionary")
    assert get_response.status_code == 200
    assert get_response.json()["source"] == "saved"
    assert get_response.json()["dictionary"]["fields"][0]["column_name"] == "amt"

    profile = client.get(f"/semantic-profile/{dataset_id}")
    assert profile.status_code == 200
    assert profile.json()["roles"]["revenue"]["column"] == "amt"
    assert profile.json()["roles"]["revenue"]["confidence_label"] == "dictionary"

    delete_response = client.delete(f"/datasets/{dataset_id}/data-dictionary")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def test_put_data_dictionary_json_sets_dashboard_domain():
    dataset_id = _upload_dataset()
    payload = {
        "domain": "retail",
        "fields": [
            {"column_name": "amt", "business_name": "Revenue", "semantic_role": "revenue", "data_type": "number"},
            {"column_name": "dt", "semantic_role": "date", "data_type": "date"},
            {"column_name": "prod_grp", "semantic_role": "category", "data_type": "string"},
        ],
    }

    response = client.put(
        f"/datasets/{dataset_id}/data-dictionary",
        json=payload,
    )
    assert response.status_code == 200

    dashboard = client.get(f"/dashboard/{dataset_id}")
    assert dashboard.status_code == 200
    assert dashboard.json()["domain"] == "retail"


def test_data_dictionary_rejects_unknown_column():
    dataset_id = _upload_dataset()
    payload = {
        "fields": [
            {"column_name": "missing_col", "semantic_role": "revenue"},
        ],
    }

    response = client.put(
        f"/datasets/{dataset_id}/data-dictionary",
        json=payload,
    )

    assert response.status_code == 400
    assert "missing columns" in response.text
