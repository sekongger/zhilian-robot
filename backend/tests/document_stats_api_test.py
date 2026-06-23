from fastapi.testclient import TestClient
from main import app


def test_document_stats_endpoint():
    client = TestClient(app)
    res = client.get("/api/v1/document-pipeline/stats")
    assert res.status_code == 200


def test_document_records_endpoint():
    client = TestClient(app)
    res = client.get('/api/v1/document-pipeline/records', params={'layer': 'resource.lnc_document'})
    assert res.status_code == 200
