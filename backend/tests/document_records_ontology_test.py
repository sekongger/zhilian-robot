from fastapi.testclient import TestClient
from main import app
import app.database.mysql_ontology_db as mysql_ontology_db


class _StubOntologyDB:
    def get_classes(self):
        return [
            {"class_id": "C_001", "class_name": "公司", "category": "实体"},
            {"class_id": "C_002", "class_name": "产品", "category": "实体"},
        ]

    def get_properties(self):
        return []

    def get_relations(self):
        return []

    def get_axioms(self, enabled_only=True):
        return []

    def get_ontology_meta(self):
        return {"ontology_code": "INC", "version": "v1"}


def test_document_records_ontology_classes(monkeypatch):
    monkeypatch.setattr(mysql_ontology_db, "ontology_db", _StubOntologyDB())
    client = TestClient(app)
    res = client.get("/api/v1/document-pipeline/records", params={"layer": "ontology.classes", "limit": 10, "offset": 0})
    assert res.status_code == 200
    payload = res.json()
    assert payload["layer"] == "ontology.classes"
    assert payload["total"] == 2
    assert payload["data"][0]["class_id"] == "C_001"
