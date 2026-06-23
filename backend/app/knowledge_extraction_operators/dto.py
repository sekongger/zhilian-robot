"""DTOs used by the operatorized knowledge extraction pipeline."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO, CanonicalEventDTO, ConflictRecordDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphImportBatchDTO, GraphImportResultDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.normalized_dto import (
    NormalizedChunkDTO,
    NormalizedConceptSeedDTO,
    NormalizedDocumentDTO,
    NormalizedEntityDTO,
    NormalizedEventDTO,
    NormalizedRelationDTO,
)
from app.incore_fusion_pipeline.dto.source_dto import SourceRecordDTO


class DocumentSourceDTO(BaseModel):
    source_id: str
    source_type: str
    location: str
    title: Optional[str] = None
    source_name: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)


class PdfSourceDTO(DocumentSourceDTO):
    page_hint: Optional[int] = None


class WebPageSourceDTO(DocumentSourceDTO):
    url: str
    fetched_at: Optional[str] = None


class DocxSourceDTO(DocumentSourceDTO):
    author: Optional[str] = None


class MarkdownSourceDTO(DocumentSourceDTO):
    markdown_text: Optional[str] = None


class RssFeedDTO(BaseModel):
    feed_url: str
    source_name: Optional[str] = None
    category: Optional[str] = None


class StructuredTableRowDTO(BaseModel):
    table_name: str
    row_id: str
    fields: Dict[str, object] = Field(default_factory=dict)


class StructuredRowDTO(BaseModel):
    row_type: str
    row_id: str
    fields: Dict[str, object] = Field(default_factory=dict)
    source_name: Optional[str] = None


class DocumentDTO(BaseModel):
    document_id: str
    title: Optional[str] = None
    content: str = ""
    content_type: Optional[str] = None
    source_name: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)


class ChunkDTO(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int = 0
    section_title: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)


class ChunkListDTO(BaseModel):
    chunks: List[ChunkDTO] = Field(default_factory=list)


class OutlineSectionDTO(BaseModel):
    title: str
    level: int = 1
    anchor_chunk_id: Optional[str] = None


class OutlineDTO(BaseModel):
    document_id: Optional[str] = None
    sections: List[OutlineSectionDTO] = Field(default_factory=list)


class TableSeedDTO(BaseModel):
    table_id: str
    document_id: str
    title: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    row_count: int = 0


class TableSeedListDTO(BaseModel):
    tables: List[TableSeedDTO] = Field(default_factory=list)


class EntitySeedDTO(BaseModel):
    entity_type: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    properties: Dict[str, object] = Field(default_factory=dict)


class EntitySeedListDTO(BaseModel):
    entities: List[EntitySeedDTO] = Field(default_factory=list)


class RelationSeedDTO(BaseModel):
    subject_name: str
    predicate: str
    object_name: str
    properties: Dict[str, object] = Field(default_factory=dict)


class RelationSeedListDTO(BaseModel):
    relations: List[RelationSeedDTO] = Field(default_factory=list)


class EventSeedDTO(BaseModel):
    event_type: str
    name: str
    subject_name: Optional[str] = None
    object_name: Optional[str] = None
    event_time: Optional[str] = None
    location: Optional[str] = None
    properties: Dict[str, object] = Field(default_factory=dict)


class EventSeedListDTO(BaseModel):
    events: List[EventSeedDTO] = Field(default_factory=list)


class ConceptSeedDTO(BaseModel):
    concept_type: str
    name: str
    parent_name: Optional[str] = None
    binding_target: Optional[str] = None


class ConceptSeedListDTO(BaseModel):
    concepts: List[ConceptSeedDTO] = Field(default_factory=list)


class ChunkEntityBundleDTO(BaseModel):
    chunk: ChunkDTO
    entities: List[EntitySeedDTO] = Field(default_factory=list)


class GraphSeedDTO(BaseModel):
    nodes: List[Dict[str, object]] = Field(default_factory=list)
    edges: List[Dict[str, object]] = Field(default_factory=list)


class CanonicalKnowledgeBundleDTO(BaseModel):
    entities: List[CanonicalEntityDTO] = Field(default_factory=list)
    events: List[CanonicalEventDTO] = Field(default_factory=list)
    concepts: List[ConceptSeedDTO] = Field(default_factory=list)


class SourceRecordListDTO(BaseModel):
    records: List[SourceRecordDTO] = Field(default_factory=list)


class NormalizedBatchDTO(BaseModel):
    entities: List[NormalizedEntityDTO] = Field(default_factory=list)
    relations: List[NormalizedRelationDTO] = Field(default_factory=list)
    documents: List[NormalizedDocumentDTO] = Field(default_factory=list)
    chunks: List[NormalizedChunkDTO] = Field(default_factory=list)
    events: List[NormalizedEventDTO] = Field(default_factory=list)
    concept_seeds: List[NormalizedConceptSeedDTO] = Field(default_factory=list)


class EventBatchDTO(BaseModel):
    events: List[NormalizedEventDTO] = Field(default_factory=list)


class EntityResolutionInputDTO(BaseModel):
    entities: List[NormalizedEntityDTO] = Field(default_factory=list)
    events: List[NormalizedEventDTO] = Field(default_factory=list)
    extra_region_names: List[str] = Field(default_factory=list)


class EntityResolutionResultDTO(BaseModel):
    entities: List[CanonicalEntityDTO] = Field(default_factory=list)
    conflicts: List[ConflictRecordDTO] = Field(default_factory=list)
    entity_lookup: Dict[str, str] = Field(default_factory=dict)


class EventResolutionInputDTO(BaseModel):
    events: List[NormalizedEventDTO] = Field(default_factory=list)
    entity_resolution: EntityResolutionResultDTO


class EventResolutionResultDTO(BaseModel):
    events: List[CanonicalEventDTO] = Field(default_factory=list)


class GraphBuildInputDTO(BaseModel):
    normalized_batch: NormalizedBatchDTO
    entity_resolution: EntityResolutionResultDTO
    event_resolution: EventResolutionResultDTO
    project: str = "IncCore"
    namespace: str = "IncCore"
    batch_id: str = "knowledge_operator_batch_001"
    project_id: Optional[int] = None


class GraphBuildResultDTO(BaseModel):
    batch: GraphImportBatchDTO
    concept_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    entity_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    event_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    document_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    chunk_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    edges: List[GraphEdgeUpsertDTO] = Field(default_factory=list)


class GraphImportInputDTO(BaseModel):
    batch: GraphImportBatchDTO
    dry_run: bool = True


class GraphImportOutputDTO(BaseModel):
    result: GraphImportResultDTO

    @property
    def status(self) -> str:
        return self.result.status

    @property
    def node_count(self) -> int:
        return self.result.node_count

    @property
    def edge_count(self) -> int:
        return self.result.edge_count


class PipelineValidationRequestDTO(BaseModel):
    operators: List[str] = Field(default_factory=list)


class PipelineValidationIssueDTO(BaseModel):
    code: str
    severity: str
    message: str
    index: Optional[int] = None
    operator: Optional[str] = None
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None


class PipelineValidationSummaryDTO(BaseModel):
    error_count: int = 0
    warning_count: int = 0


class PipelineValidationResultDTO(BaseModel):
    valid: bool = True
    issues: List[PipelineValidationIssueDTO] = Field(default_factory=list)
    normalized_operators: List[str] = Field(default_factory=list)
    summary: PipelineValidationSummaryDTO = Field(default_factory=PipelineValidationSummaryDTO)


class PipelineExecutionPreviewRequestDTO(BaseModel):
    operators: List[str] = Field(default_factory=list)
    input_type: str
    input_payload: Dict[str, object] = Field(default_factory=dict)


class PipelineExecutionPreviewIssueDTO(BaseModel):
    code: str
    message: str
    severity: str = "error"
    operator: Optional[str] = None
    index: Optional[int] = None


class PipelineExecutionPreviewStepDTO(BaseModel):
    operator: str
    input_type: str
    output_type: str
    summary: Dict[str, object] = Field(default_factory=dict)


class PipelineExecutionPreviewResultDTO(BaseModel):
    valid: bool = True
    issues: List[PipelineExecutionPreviewIssueDTO] = Field(default_factory=list)
    steps: List[PipelineExecutionPreviewStepDTO] = Field(default_factory=list)
    final_output_type: Optional[str] = None
    final_output_summary: Dict[str, object] = Field(default_factory=dict)


class PipelineNodeDTO(BaseModel):
    key: str
    operator: str
    title: Optional[str] = None
    lane: int = 0


class PipelineEdgeDTO(BaseModel):
    source: str
    target: str


class PublishedPipelineDTO(BaseModel):
    key: str
    name: str
    description: str = ""
    source_types: List[str] = Field(default_factory=list)
    nodes: List[PipelineNodeDTO] = Field(default_factory=list)
    edges: List[PipelineEdgeDTO] = Field(default_factory=list)
    operators: List[str] = Field(default_factory=list)
    is_builtin: bool = False
    published_by: str = "system"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PublishPipelineRequestDTO(BaseModel):
    name: str
    description: str = ""
    nodes: List[PipelineNodeDTO] = Field(default_factory=list)
    source_types: List[str] = Field(default_factory=list)
    published_by: str = "admin"
