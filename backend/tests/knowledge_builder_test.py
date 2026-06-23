from app.document_pipeline.knowledge_builder import (
    build_context_docs,
    build_entity_docs,
    build_statement_docs,
    make_context_id,
    make_statement_id,
)


def test_make_ids_deterministic():
    sid1 = make_statement_id("doc1", "sub", "pred", "obj")
    sid2 = make_statement_id("doc1", "sub", "pred", "obj")
    assert sid1 == sid2


def test_build_entities_maps_and_dedupes():
    entities = {"companies": ["A", "A"], "products": ["P"]}
    docs = build_entity_docs(entities)
    names = sorted([d["name"] for d in docs])
    assert names == ["A", "P"]


def test_build_statements_from_relations():
    relations = [{"subject": "A", "relation": "合作", "object": "B", "confidence": 0.9}]
    entity_map = {"A": "EN1", "B": "EN2"}
    stmts = build_statement_docs("doc1", relations, entity_map, "news")
    assert len(stmts) == 1
    assert stmts[0]["subject_id"] == "EN1"
    assert stmts[0]["object_entity_id"] == "EN2"


def test_build_contexts_match_statements():
    stmts = [{"statement_id": "ST1", "doc_id": "doc1"}]
    ctxs = build_context_docs("doc1", stmts, "news", "sourceA", "2025-01-01")
    assert ctxs[0]["context_id"] == make_context_id("doc1", "ST1")
