"""Canonical DTOs for the IncCore fusion pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.incore_fusion_pipeline.dto.source_dto import SourceReferenceDTO


class ConceptBindingDTO(BaseModel):
    """Resolved concept binding."""

    concept_type: str
    concept_name: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ConflictSourceDetailDTO(BaseModel):
    """Single source value that participated in a conflict."""

    source_system: str
    value: Any
    authority_level: float = 0.0


class ConflictRecordDTO(BaseModel):
    """Conflict resolution audit record."""

    graph_id: str
    field: str
    winning_value: Any
    losing_values: List[Any] = Field(default_factory=list)
    resolution_rule: str
    source_details: List[ConflictSourceDetailDTO] = Field(default_factory=list)


class CanonicalEntityDTO(BaseModel):
    """Canonical entity after resolution and merge."""

    graph_id: str
    entity_type: str
    primary_name: str
    official_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    external_keys: Dict[str, str] = Field(default_factory=dict)
    merged_sources: List[SourceReferenceDTO] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    concept_bindings: List[ConceptBindingDTO] = Field(default_factory=list)


class CanonicalEvidenceDTO(BaseModel):
    """Resolved evidence references for events and facts."""

    document_ids: List[str] = Field(default_factory=list)
    chunk_ids: List[str] = Field(default_factory=list)


class CanonicalEventDTO(BaseModel):
    """Canonical event after entity and evidence resolution."""

    graph_id: str
    event_type: str
    name: str
    summary: Optional[str] = None
    subject_graph_id: Optional[str] = None
    object_graph_id: Optional[str] = None
    location_graph_id: Optional[str] = None
    category_name: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: CanonicalEvidenceDTO = Field(default_factory=CanonicalEvidenceDTO)
    concept_bindings: List[ConceptBindingDTO] = Field(default_factory=list)
    source_refs: List[SourceReferenceDTO] = Field(default_factory=list)
