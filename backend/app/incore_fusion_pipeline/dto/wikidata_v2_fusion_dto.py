"""DTOs for the Wikidata + Neo4j v2 fusion skeleton."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.incore_fusion_pipeline.dto.graph_import_dto import GraphImportBatchDTO


class V2SourceNodeDTO(BaseModel):
    """Raw node exported from Neo4j v2."""

    source_system: str = "neo4j_v2"
    source_label: str
    source_uuid: str
    name: Optional[str] = None
    summary: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class V2SourceEdgeDTO(BaseModel):
    """Raw edge exported from Neo4j v2."""

    source_system: str = "neo4j_v2"
    source_edge_uuid: str
    predicate: str
    subject_source_uuid: str
    object_source_uuid: str
    subject_source_type: Optional[str] = None
    object_source_type: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class MappedV2NodeDTO(BaseModel):
    """Layered node payload after v2 mapping."""

    source_system: str
    source_uuid: str
    original_type: str
    normalized_type: str
    name: Optional[str] = None
    match_keys: Dict[str, Any] = Field(default_factory=dict)
    canonical_candidates: Dict[str, Any] = Field(default_factory=dict)
    source_profiles: Dict[str, Any] = Field(default_factory=dict)
    analytics: Dict[str, Any] = Field(default_factory=dict)
    fact_payload: Dict[str, Any] = Field(default_factory=dict)
    raw_properties: Dict[str, Any] = Field(default_factory=dict)


class CanonicalNodeIndexDTO(BaseModel):
    """Minimal canonical node view used by the matcher."""

    graph_id: str
    type_name: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)


class FusionNodeDecisionDTO(BaseModel):
    """Decision for one source node."""

    source_uuid: str
    original_type: str
    normalized_type: str
    decision: str
    resolved_graph_id: Optional[str] = None
    matched_graph_id: Optional[str] = None
    match_method: Optional[str] = None
    match_score: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class FusionRelationDecisionDTO(BaseModel):
    """Decision for one source edge."""

    source_relation_type: str
    source_edge_uuid: str
    subject_source_uuid: str
    object_source_uuid: str
    resolved_subject_graph_id: Optional[str] = None
    resolved_object_graph_id: Optional[str] = None
    decision: str
    target_layer: str
    predicate: str
    evidence_refs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FusionRunResultDTO(BaseModel):
    """Batch plus planning decisions for the skeleton runner."""

    batch: GraphImportBatchDTO
    node_decisions: List[FusionNodeDecisionDTO] = Field(default_factory=list)
    relation_decisions: List[FusionRelationDecisionDTO] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class Neo4jV2ExportPackageDTO(BaseModel):
    """Parsed export package from a Neo4j v2 subgraph dump."""

    package_name: str
    manifest: Dict[str, Any] = Field(default_factory=dict)
    export_dir: str
    nodes: List[V2SourceNodeDTO] = Field(default_factory=list)
    edges: List[V2SourceEdgeDTO] = Field(default_factory=list)
