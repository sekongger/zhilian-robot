from app.document_pipeline.repository import DocumentRepository


def test_build_resource_doc_shape():
    repo = DocumentRepository(db=None)
    doc = repo.build_resource_doc(
        resource_type="news",
        source="baidu",
        title="t",
        content="c",
        url="u",
    )
    assert doc["resource_type"] == "news"
    assert "resource_doc_id" in doc


def test_build_inc_document_uses_resource_id():
    repo = DocumentRepository(db=None)
    resource = repo.build_resource_doc("news", "baidu", "t", "c", "u")
    inc = repo.build_inc_document(resource)
    assert inc["doc_id"] == resource["resource_doc_id"]
