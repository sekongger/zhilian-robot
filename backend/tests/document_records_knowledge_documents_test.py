from fastapi.testclient import TestClient
from main import app
import app.database.mongodb as mongodb_module


class _Cursor:
    def __init__(self, items):
        self._items = list(items)
        self._skip = 0
        self._limit = None

    def sort(self, *args, **kwargs):
        return self

    def skip(self, value):
        self._skip = value
        return self

    def limit(self, value):
        self._limit = value
        return self

    def __iter__(self):
        items = self._items[self._skip:]
        if self._limit is not None:
            items = items[: self._limit]
        return iter(items)


class _Collection:
    def __init__(self, items):
        self._items = items

    def find(self, *args, **kwargs):
        return _Cursor(self._items)

    def count_documents(self, *args, **kwargs):
        return len(self._items)


class _StubMongo:
    def get_collection(self, name):
        if name == "inc_document":
            return _Collection([
                {"_id": "1", "doc_id": "D1", "title": "t1", "content": "c1"},
            ])
        if name == "inc_microcontent":
            return _Collection([
                {"_id": "2", "microcontent_id": "M1", "doc_id": "D1", "block": "b1"},
            ])
        return _Collection([])


def test_records_standard_document(monkeypatch):
    monkeypatch.setattr(mongodb_module, "mongodb_conn", _StubMongo())
    client = TestClient(app)
    res = client.get(
        "/api/v1/document-pipeline/records",
        params={"layer": "knowledge.standard_document", "limit": 10, "offset": 0},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["layer"] == "knowledge.standard_document"
    assert payload["total"] == 1
    assert payload["data"][0]["doc_id"] == "D1"


def test_records_micro_document(monkeypatch):
    monkeypatch.setattr(mongodb_module, "mongodb_conn", _StubMongo())
    client = TestClient(app)
    res = client.get(
        "/api/v1/document-pipeline/records",
        params={"layer": "knowledge.micro_document", "limit": 10, "offset": 0},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["layer"] == "knowledge.micro_document"
    assert payload["total"] == 1
    assert payload["data"][0]["micro_document_id"] == "M1"
