"""Normalized DTOs for the IncCore fusion pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.incore_fusion_pipeline.dto.source_dto import SourceReferenceDTO


class ConceptCandidateDTO(BaseModel):
    """Candidate concept binding before canonical resolution."""

    concept_type: str
    concept_name: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class MatchReferenceDTO(BaseModel):
    """Reference used for matching entities or concepts."""

    type: str
    match_key: str


class NormalizedEntityDTO(BaseModel):
    """Schema-aligned normalized entity."""

    canonical_type: str
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)
    primary_name: str
    aliases: List[str] = Field(default_factory=list)
    external_keys: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
    concept_candidates: List[ConceptCandidateDTO] = Field(default_factory=list)


class NormalizedDocumentDTO(BaseModel):
    """Schema-aligned document."""

    document_id: str
    doc_type: str
    name: str
    description: Optional[str] = None
    content: Optional[str] = None
    publish_time: Optional[datetime] = None
    url: Optional[str] = None
    source: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)


class NormalizedChunkDTO(BaseModel):
    """Schema-aligned text chunk."""

    chunk_id: str
    document_id: str
    chunk_index: int
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    content: str
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)


class NormalizedEventDTO(BaseModel):
    """Schema-aligned event before canonical resolution."""

    event_type: str
    name: str
    summary: Optional[str] = None
    subject_ref: Optional[MatchReferenceDTO] = None
    object_ref: Optional[MatchReferenceDTO] = None
    location_ref: Optional[MatchReferenceDTO] = None
    category_ref: Optional[MatchReferenceDTO] = None
    source_document_ids: List[str] = Field(default_factory=list)
    source_chunk_ids: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    concept_candidates: List[ConceptCandidateDTO] = Field(default_factory=list)
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)


class NormalizedRelationDTO(BaseModel):
    """Schema-aligned relation before canonical resolution."""

    subject_ref: MatchReferenceDTO
    predicate: str
    object_ref: MatchReferenceDTO
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)


class NormalizedConceptSeedDTO(BaseModel):
    """Normalized concept seed from taxonomies or rules."""

    concept_type: str
    name: str
    parent_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)
