from fastapi.testclient import TestClient
from main import app


def test_news_pipeline_removed():
    client = TestClient(app)
    res = client.get('/api/v1/news-pipeline/stats')
    assert res.status_code == 404
