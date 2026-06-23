from app.document_pipeline.utils import (
    generate_doc_id,
    generate_microcontent_id,
    hash_content,
    normalize_source_name,
    split_microcontent,
)


def test_generate_doc_id_prefix_and_length():
    doc_id = generate_doc_id()
    assert doc_id.startswith("DOC")
    assert len(doc_id) == 20


def test_generate_microcontent_id_prefix():
    mc_id = generate_microcontent_id()
    assert mc_id.startswith("MC")


def test_hash_content_is_sha256():
    h = hash_content("abc")
    assert len(h) == 64


def test_normalize_source_name():
    assert normalize_source_name("东方财富网") == "unknown"
    assert normalize_source_name("EastMoney") == "eastmoney"


def test_split_microcontent():
    blocks = split_microcontent("a\n\n bbb")
    assert blocks == ["a", "bbb"]
