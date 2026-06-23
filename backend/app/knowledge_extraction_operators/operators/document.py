"""Document-oriented operators for source ingest, parsing, cleaning, and chunking."""

from __future__ import annotations

import re
from pathlib import Path

from app.knowledge_extraction_operators.base import KnowledgeOperatorABC, OperatorSpec
from app.knowledge_extraction_operators.dto import (
    ChunkDTO,
    ChunkListDTO,
    DocumentDTO,
    DocumentSourceDTO,
    MarkdownSourceDTO,
    PdfSourceDTO,
    WebPageSourceDTO,
)
from app.knowledge_extraction_operators.kag_bridge import (
    document_dto_to_kag_chunk,
    ensure_kag_import_path,
    ensure_kag_task_config,
    kag_chunk_to_chunk_dto,
    kag_chunks_to_document_dto,
    source_dto_to_kag_chunk,
    unwrap_kag_outputs,
)
from app.knowledge_extraction_operators.registry import register_operator

ensure_kag_import_path()

from kag.builder.component.reader.markdown_reader import MarkDownReader  # noqa: E402
from kag.builder.component.reader.pdf_reader import PDFReader  # noqa: E402
from kag.builder.component.reader.txt_reader import TXTReader  # noqa: E402
from kag.builder.component.splitter.length_splitter import LengthSplitter  # noqa: E402


def _read_text(location: str) -> str:
    path = Path(location)
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_bytes().decode("utf-8", errors="ignore")


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _clean_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


@register_operator
class PdfSourceIngestOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="pdf_source_ingest",
        stage="ingest",
        layer="source_ingest",
        knowledge_category="data_ingestion_loading",
        operator_class="general",
        description="接入本地或对象存储中的 PDF 文件，统一转成文档源记录。",
        input_type="PdfSourceDTO",
        output_type="DocumentSourceDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.PdfSourceIngestOperator",
        applicable_sources=["report", "pdf"],
        tags=["source", "pdf", "ingest"],
        decoupling_reason="PDF 接入只依赖文件路径和基础元数据，可作为稳定入口复用于研报、公告和政策文档。",
    )

    def run(self, input_data: PdfSourceDTO) -> DocumentSourceDTO:
        metadata = dict(input_data.metadata)
        metadata.setdefault("origin_format", "pdf")
        if input_data.page_hint is not None:
            metadata["page_hint"] = input_data.page_hint
        return DocumentSourceDTO(
            source_id=input_data.source_id,
            source_type=input_data.source_type,
            location=input_data.location,
            title=input_data.title,
            source_name=input_data.source_name,
            metadata=metadata,
        )


@register_operator
class WebPageSourceIngestOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="webpage_source_ingest",
        stage="ingest",
        layer="source_ingest",
        knowledge_category="data_ingestion_loading",
        operator_class="general",
        description="抓取网页正文和元数据，统一生成网页文档源记录。",
        input_type="WebPageSourceDTO",
        output_type="DocumentSourceDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.WebPageSourceIngestOperator",
        applicable_sources=["news", "webpage", "url"],
        tags=["source", "web", "ingest"],
        decoupling_reason="网页接入与后续实体/事件抽取解耦，任何 URL 类输入都可以复用这一步。",
    )

    def run(self, input_data: WebPageSourceDTO) -> DocumentSourceDTO:
        metadata = dict(input_data.metadata)
        metadata.setdefault("url", input_data.url)
        if input_data.fetched_at:
            metadata["fetched_at"] = input_data.fetched_at
        return DocumentSourceDTO(
            source_id=input_data.source_id,
            source_type=input_data.source_type,
            location=input_data.location or input_data.url,
            title=input_data.title,
            source_name=input_data.source_name,
            metadata=metadata,
        )


@register_operator
class MarkdownSourceIngestOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="markdown_source_ingest",
        stage="ingest",
        layer="source_ingest",
        knowledge_category="data_ingestion_loading",
        operator_class="general",
        description="接入 Markdown 文本并保留标题、段落和引用结构。",
        input_type="MarkdownSourceDTO",
        output_type="DocumentSourceDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.MarkdownSourceIngestOperator",
        applicable_sources=["markdown", "note", "report"],
        tags=["source", "markdown", "ingest"],
        decoupling_reason="Markdown 已是半结构化格式，接入可以和抽取逻辑完全分离。",
    )

    def run(self, input_data: MarkdownSourceDTO) -> DocumentSourceDTO:
        metadata = dict(input_data.metadata)
        if input_data.markdown_text:
            metadata["markdown_text"] = input_data.markdown_text
        metadata.setdefault("origin_format", "markdown")
        return DocumentSourceDTO(
            source_id=input_data.source_id,
            source_type=input_data.source_type,
            location=input_data.location,
            title=input_data.title,
            source_name=input_data.source_name,
            metadata=metadata,
        )


@register_operator
class PdfParseOperator(PDFReader, KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="pdf_parse",
        stage="parse",
        layer="document_parse",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="把 PDF 文档解析成正文、页码和版面信息。",
        input_type="DocumentSourceDTO",
        output_type="DocumentDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.PdfParseOperator",
        applicable_sources=["report", "pdf"],
        tags=["parse", "pdf", "document"],
        decoupling_reason="PDF 解析只关注版面到文本的转换，与下游实体/事件抽取无关。",
    )

    def __init__(self):
        self._kag_task_id = ensure_kag_task_config()
        PDFReader.__init__(
            self,
            outline_flag=False,
            kag_qa_task_config_key=self._kag_task_id,
        )
        self._txt_reader = TXTReader(kag_qa_task_config_key=self._kag_task_id)

    def run(self, input_data: DocumentSourceDTO) -> DocumentDTO:
        raw_text = input_data.metadata.get("raw_text")
        reader_name = "PDFReader"
        try:
            if raw_text:
                kag_outputs = unwrap_kag_outputs(
                    self._txt_reader.invoke(str(raw_text), write_ckpt=False)
                )
                reader_name = "TXTReader"
            else:
                kag_outputs = unwrap_kag_outputs(
                    PDFReader.invoke(self, input_data.location, write_ckpt=False)
                )
        except Exception:
            kag_outputs = unwrap_kag_outputs(
                self._txt_reader.invoke(input_data.location, write_ckpt=False)
            )
            reader_name = "TXTReader"
        return kag_chunks_to_document_dto(
            kag_outputs,
            input_data,
            content_type="pdf",
            reader_name=reader_name,
        )


@register_operator
class HtmlExtractOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="html_extract",
        stage="parse",
        layer="document_parse",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="从网页 HTML 中提取正文、标题和发布时间。",
        input_type="DocumentSourceDTO",
        output_type="DocumentDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.HtmlExtractOperator",
        applicable_sources=["news", "webpage", "url"],
        tags=["parse", "html", "document"],
        decoupling_reason="网页正文抽取是通用处理步骤，可服务资讯、公告和政策页面。",
    )

    def run(self, input_data: DocumentSourceDTO) -> DocumentDTO:
        html = input_data.metadata.get("html") or _read_text(input_data.location)
        text = _clean_text(_strip_html_tags(str(html)))
        return DocumentDTO(
            document_id=input_data.source_id,
            title=input_data.title,
            content=text,
            content_type="html",
            source_name=input_data.source_name,
            metadata=dict(input_data.metadata),
        )


@register_operator
class MarkdownNormalizeOperator(MarkDownReader, KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="markdown_normalize",
        stage="parse",
        layer="document_parse",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="规范 Markdown 结构、标题层级和引用块格式。",
        input_type="DocumentSourceDTO",
        output_type="DocumentDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.MarkdownNormalizeOperator",
        applicable_sources=["markdown", "report", "note"],
        tags=["parse", "markdown", "normalize"],
        decoupling_reason="Markdown 规范化只依赖文档结构本身，适合作为统一前置算子。",
    )

    def __init__(self):
        self._kag_task_id = ensure_kag_task_config()
        MarkDownReader.__init__(
            self,
            kag_qa_task_config_key=self._kag_task_id,
        )
        self._txt_reader = TXTReader(kag_qa_task_config_key=self._kag_task_id)

    def run(self, input_data: DocumentSourceDTO) -> DocumentDTO:
        markdown_text = input_data.metadata.get("markdown_text")
        if markdown_text:
            kag_input = source_dto_to_kag_chunk(input_data, str(markdown_text))
        else:
            kag_input = input_data.location
        reader_name = "MarkDownReader"
        try:
            kag_outputs = unwrap_kag_outputs(
                MarkDownReader.invoke(self, kag_input, write_ckpt=False)
            )
        except Exception:
            fallback_text = str(markdown_text) if markdown_text else _read_text(input_data.location)
            kag_outputs = unwrap_kag_outputs(
                self._txt_reader.invoke(fallback_text, write_ckpt=False)
            )
            reader_name = "TXTReader"
        return kag_chunks_to_document_dto(
            kag_outputs,
            input_data,
            content_type="markdown",
            reader_name=reader_name,
        )


@register_operator
class DocumentCleanOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="document_clean",
        stage="parse",
        layer="document_parse",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="清理噪声字符、页眉页脚和多余空白，生成可抽取正文。",
        input_type="DocumentDTO",
        output_type="DocumentDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.DocumentCleanOperator",
        applicable_sources=["report", "news", "document"],
        tags=["parse", "clean", "normalize"],
        decoupling_reason="清洗规则与具体知识 schema 无关，适合复用成标准文档清理算子。",
    )

    def run(self, input_data: DocumentDTO) -> DocumentDTO:
        cleaned = _clean_text(_strip_html_tags(input_data.content))
        return DocumentDTO(
            document_id=input_data.document_id,
            title=input_data.title,
            content=cleaned,
            content_type=input_data.content_type,
            source_name=input_data.source_name,
            metadata=dict(input_data.metadata),
        )


@register_operator
class ChunkSplitOperator(LengthSplitter, KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="chunk_split",
        stage="structure",
        layer="structure",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="按长度、语义或结构把文档拆成标准 chunk。",
        input_type="DocumentDTO",
        output_type="ChunkListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.document.ChunkSplitOperator",
        applicable_sources=["report", "news", "document"],
        tags=["structure", "chunk", "split"],
        decoupling_reason="切块只依赖文档内容和分块策略，天然适合做成可配置算子。",
    )

    def __init__(self):
        self._kag_task_id = ensure_kag_task_config()
        LengthSplitter.__init__(
            self,
            split_length=180,
            window_length=30,
            kag_qa_task_config_key=self._kag_task_id,
        )

    def run(self, input_data: DocumentDTO) -> ChunkListDTO:
        kag_chunk = document_dto_to_kag_chunk(input_data)
        kag_outputs = unwrap_kag_outputs(
            LengthSplitter.invoke(self, kag_chunk, write_ckpt=False)
        )
        chunks = [
            kag_chunk_to_chunk_dto(
                chunk,
                fallback_document_id=input_data.document_id,
                chunk_index=index,
            )
            for index, chunk in enumerate(kag_outputs)
        ]
        return ChunkListDTO(chunks=chunks)
