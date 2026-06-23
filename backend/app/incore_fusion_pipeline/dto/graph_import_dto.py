"""Graph import DTOs for OpenSPG batch upserts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNodeUpsertDTO(BaseModel):
    """Single node upsert instruction."""

    type_name: str
    graph_id: str
    name: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeUpsertDTO(BaseModel):
    """Single edge upsert instruction."""

    subject_graph_id: str
    predicate: str
    object_graph_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphImportBatchDTO(BaseModel):
    """Single import batch submitted to OpenSPG."""

    project: str
    namespace: str
    batch_id: str
    concept_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    entity_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    event_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    document_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    chunk_nodes: List[GraphNodeUpsertDTO] = Field(default_factory=list)
    edges: List[GraphEdgeUpsertDTO] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def node_count(self) -> int:
        return (
            len(self.concept_nodes)
            + len(self.entity_nodes)
            + len(self.event_nodes)
            + len(self.document_nodes)
            + len(self.chunk_nodes)
        )

    def edge_count(self) -> int:
        return len(self.edges)


class GraphImportResultDTO(BaseModel):
    """Result returned by the importer."""

    batch_id: str
    status: str
    dry_run: bool = True
    node_count: int = 0
    edge_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
