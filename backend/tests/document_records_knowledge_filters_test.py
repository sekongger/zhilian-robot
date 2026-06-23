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

    def find(self, query=None, *args, **kwargs):
        items = list(self._items)
        if query:
            resource_type = query.get("resource_type")
            if resource_type is not None:
                items = [item for item in items if item.get("resource_type") == resource_type]
            doc_id_filter = query.get("doc_id")
            if isinstance(doc_id_filter, dict) and "$in" in doc_id_filter:
                allowed = set(doc_id_filter["$in"])
                items = [item for item in items if item.get("doc_id") in allowed]
        return _Cursor(items)

    def count_documents(self, *args, **kwargs):
        return len(self._items)


class _StubMongo:
    def get_collection(self, name):
        if name == "inc_document":
            return _Collection([
                {"_id": "1", "doc_id": "D1", "resource_type": "news"},
                {"_id": "2", "doc_id": "D2", "resource_type": "report"},
            ])
        if name == "inc_microcontent":
            return _Collection([
                {"_id": "m1", "microcontent_id": "M1", "doc_id": "D1"},
                {"_id": "m2", "microcontent_id": "M2", "doc_id": "D2"},
            ])
        return _Collection([])


def test_records_micro_document_filtered_by_doc_type(monkeypatch):
    monkeypatch.setattr(mongodb_module, "mongodb_conn", _StubMongo())
    client = TestClient(app)
    res = client.get(
        "/api/v1/document-pipeline/records",
        params={"layer": "knowledge.micro_document", "limit": 10, "offset": 0, "doc_type": "news"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] == 1
    assert payload["data"][0]["micro_document_id"] == "M1"
