from fastapi.testclient import TestClient
from main import app


def test_ingest_document_minimal():
    client = TestClient(app)
    payload = {
        "resource_type": "news",
        "source_id": "DS_TEST",
        "content": {"raw_text": "hello"},
        "metadata": {"title": "t"}
    }
    res = client.post("/api/v1/ingest/document", json=payload)
    assert res.status_code == 200
