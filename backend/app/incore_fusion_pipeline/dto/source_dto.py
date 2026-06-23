"""Source-level DTOs for the IncCore fusion pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceReferenceDTO(BaseModel):
    """Minimal source record pointer."""

    source_system: str = Field(..., description="Source pipeline or storage system")
    source_table: str = Field(..., description="Original table, collection, or feed name")
    record_id: str = Field(..., description="Source record identifier")


class SourceEntityPayloadDTO(BaseModel):
    """Payload for structured entity records."""

    entity_type: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    code: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    status: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    business_scope: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class SourceRelationPayloadDTO(BaseModel):
    """Payload for structured relation records."""

    subject_type: str
    subject_key: str
    predicate: str
    object_type: str
    object_key: str
    confidence: Optional[float] = None
    effective_time: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class SourceDocumentPayloadDTO(BaseModel):
    """Payload for document records."""

    doc_type: str
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    publish_time: Optional[datetime] = None
    url: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    authority_level: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceChunkPayloadDTO(BaseModel):
    """Payload for text chunks."""

    doc_id: str
    chunk_index: int
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    content: str


class SourceEventPayloadDTO(BaseModel):
    """Payload for extracted or aggregated event records."""

    event_type: str
    name: Optional[str] = None
    summary: Optional[str] = None
    subject_name: Optional[str] = None
    object_name: Optional[str] = None
    event_time: Optional[datetime] = None
    publish_time: Optional[datetime] = None
    location: Optional[str] = None
    confidence: Optional[float] = None
    trigger_terms: List[str] = Field(default_factory=list)
    source_doc_id: Optional[str] = None
    source_chunk_ids: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)


class ConceptSeedPayloadDTO(BaseModel):
    """Payload for concept seed or taxonomy entries."""

    concept_type: str
    name: str
    parent_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class SourceRecordDTO(BaseModel):
    """Generic source envelope used by the fusion pipeline."""

    source_system: str = Field(..., description="Source pipeline or storage system")
    source_table: str = Field(..., description="Original table, collection, or feed name")
    record_id: str = Field(..., description="Source record identifier")
    record_type: str = Field(..., description="entity | relation | document | chunk | event | concept_seed")
    payload: Dict[str, Any] = Field(default_factory=dict)
    ingest_time: Optional[datetime] = None

    def to_source_ref(self) -> SourceReferenceDTO:
        """Return a minimal source pointer for downstream DTOs."""

        return SourceReferenceDTO(
            source_system=self.source_system,
            source_table=self.source_table,
            record_id=self.record_id,
        )
