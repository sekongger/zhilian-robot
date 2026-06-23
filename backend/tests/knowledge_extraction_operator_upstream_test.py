from pathlib import Path

import app.knowledge_extraction_operators.operators.extract as extract_module
from app.knowledge_extraction_operators import get_operator
from app.knowledge_extraction_operators.dto import (
    ChunkDTO,
    ChunkEntityBundleDTO,
    DocumentDTO,
    MarkdownSourceDTO,
    PdfSourceDTO,
)
from app.knowledge_extraction_operators.operators.kag_adapter import KagExtractionPayload, reset_kag_backend_state
from kag.builder.component.extractor.schema_constraint_extractor import SchemaConstraintExtractor
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.writer.kg_writer import KGWriter
from kag.builder.model.chunk import Chunk as KagChunk


def setup_function():
    reset_kag_backend_state()


def test_workbench_document_and_extract_operators_extend_kag_components():
    assert isinstance(get_operator("pdf_parse"), PDFReader)
    assert isinstance(get_operator("markdown_normalize"), MarkDownReader)
    assert isinstance(get_operator("chunk_split"), LengthSplitter)
    assert isinstance(get_operator("entity_extract"), SchemaConstraintExtractor)
    assert isinstance(get_operator("relation_extract"), SchemaConstraintExtractor)
    assert isinstance(get_operator("event_extract"), SchemaConstraintExtractor)
    assert isinstance(get_operator("graph_import"), KGWriter)


def test_chunk_split_operator_invokes_kag_length_splitter(monkeypatch):
    called = {}

    def fake_kag_invoke(self, input_chunk, **kwargs):
        called["input_type"] = type(input_chunk).__name__
        called["content"] = input_chunk.content
        return [
            KagChunk(
                id="kag_chunk_001",
                name="kag_chunk_001",
                content="KAG 切块结果",
                document_id="doc_kag",
            )
        ]

    monkeypatch.setattr(LengthSplitter, "_invoke", fake_kag_invoke)

    document = get_operator("chunk_split").run(
        DocumentDTO(
            document_id="doc_kag",
            title="KAG 切块测试",
            content="原始内容应该交给 KAG LengthSplitter 处理。",
            content_type="text",
        )
    )

    assert called == {
        "input_type": "Chunk",
        "content": "原始内容应该交给 KAG LengthSplitter 处理。",
    }
    assert document.chunks[0].chunk_id == "kag_chunk_001"
    assert document.chunks[0].text == "KAG 切块结果"


def test_source_and_document_operators_run_basic_chain(tmp_path: Path):
    fake_pdf = tmp_path / "sample.pdf"
    fake_pdf.write_text("上海某某机器人科技有限公司完成B轮融资。", encoding="utf-8")

    pdf_source = PdfSourceDTO(
        source_id="pdf_001",
        source_type="pdf",
        location=str(fake_pdf),
        title="机器人融资快报",
        source_name="测试来源",
    )

    document_source = get_operator("pdf_source_ingest").run(pdf_source)
    document = get_operator("pdf_parse").run(document_source)
    cleaned = get_operator("document_clean").run(document)
    chunks = get_operator("chunk_split").run(cleaned)

    assert document_source.source_id == "pdf_001"
    assert document.content
    assert "机器人科技有限公司" in cleaned.content
    assert chunks.chunks
    assert chunks.chunks[0].document_id == document.document_id


def test_markdown_normalize_operator_reads_inline_markdown():
    markdown_source = MarkdownSourceDTO(
        source_id="md_001",
        source_type="markdown",
        location="inline://markdown",
        title="测试 Markdown",
        source_name="测试来源",
        markdown_text="# 标题\n\n上海某某机器人科技有限公司与某产业基金签署合作协议。",
    )

    document_source = get_operator("markdown_source_ingest").run(markdown_source)
    document = get_operator("markdown_normalize").run(document_source)

    assert document.document_id == "md_001"
    assert "上海某某机器人科技有限公司" in document.content
    assert "某产业基金" in document.content


def test_extract_operators_produce_entity_relation_and_event_seeds(monkeypatch):
    chunk = ChunkDTO(
        chunk_id="chunk_001",
        document_id="doc_001",
        text="上海某某机器人科技有限公司完成B轮融资，投资方为某产业基金。随后公司与浙江大学签署合作协议。",
        chunk_index=0,
    )

    # This test verifies fallback extraction semantics and must not depend on
    # a live KAG/OpenAI backend being reachable in the current environment.
    monkeypatch.setattr(
        extract_module.KagSchemaConstraintOperatorBase,
        "_extract_payload",
        lambda self, input_chunk: None,
    )

    entity_result = get_operator("entity_extract").run(chunk)
    standardized_entities = get_operator("entity_standardize").run(entity_result)
    relation_result = get_operator("relation_extract").run(
        ChunkEntityBundleDTO(chunk=chunk, entities=standardized_entities.entities)
    )
    event_result = get_operator("event_extract").run(chunk)

    entity_names = {item.name for item in standardized_entities.entities}
    relation_predicates = {item.predicate for item in relation_result.relations}
    event_types = {item.event_type for item in event_result.events}

    assert "上海某某机器人科技有限公司" in entity_names
    assert "某产业基金" in entity_names
    assert "浙江大学" in entity_names
    assert "investedIn" in relation_predicates or "cooperateWith" in relation_predicates
    assert "CompanyFinancingEvent" in event_types
    assert "CompanyCooperationEvent" in event_types


def test_extract_operators_use_kag_backend_when_available(monkeypatch):
    chunk = ChunkDTO(
        chunk_id="chunk_kag_001",
        document_id="doc_001",
        text="原始文本不应该命中 fallback。",
        chunk_index=0,
    )

    class FakeBackend:
        def extract(self, input_chunk: ChunkDTO):
            assert input_chunk.chunk_id == "chunk_kag_001"
            return KagExtractionPayload(
                entities=[
                    {
                        "name": "上海某某机器人科技有限公司",
                        "category": "Company",
                        "properties": {"semanticType": "科技企业"},
                    },
                    {
                        "name": "某产业基金",
                        "category": "Organization",
                        "properties": {"semanticType": "投资机构"},
                    },
                ],
                standardized_entities=[
                    {
                        "name": "上海某某机器人科技有限公司",
                        "category": "Company",
                        "official_name": "上海某某机器人科技有限公司",
                    }
                ],
                relations=[
                    [
                        "某产业基金",
                        "Organization",
                        "investedIn",
                        "上海某某机器人科技有限公司",
                        "Company",
                    ]
                ],
                events=[
                    {
                        "category": "CompanyFinancingEvent",
                        "properties": {
                            "name": "上海某某机器人科技有限公司融资事件",
                            "subject": "上海某某机器人科技有限公司",
                            "object": "某产业基金",
                            "time": "2026-04-13",
                        },
                    }
                ],
            )

    monkeypatch.setattr(
        extract_module.KagSchemaConstraintOperatorBase,
        "_extract_payload",
        lambda self, input_chunk: FakeBackend().extract(input_chunk),
    )

    entity_result = get_operator("entity_extract").run(chunk)
    relation_result = get_operator("relation_extract").run(
        ChunkEntityBundleDTO(chunk=chunk, entities=entity_result.entities)
    )
    event_result = get_operator("event_extract").run(chunk)

    assert {item.name for item in entity_result.entities} == {
        "上海某某机器人科技有限公司",
        "某产业基金",
    }
    assert relation_result.relations[0].predicate == "investedIn"
    assert relation_result.relations[0].properties["backend"] == "kag"
    assert event_result.events[0].event_type == "CompanyFinancingEvent"
    assert event_result.events[0].properties["backend"] == "kag"
