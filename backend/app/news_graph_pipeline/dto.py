"""DTO contracts for the separated news graph pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CommonSenseAnchorDTO(BaseModel):
    """Stable common-sense node mirrored into Graphiti as an anchor."""

    anchor_id: str
    type_name: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    source_graph: str = "incore_common_neo4j"
    source_version: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class EntityLinkDecisionDTO(BaseModel):
    """Decision for linking one Graphiti news entity to one common-sense anchor."""

    news_entity_id: str
    news_entity_name: str
    candidate_anchor_id: Optional[str] = None
    match_score: float = 0.0
    match_method: str = "none"
    decision: str = "unresolved"
    reason: str = ""
    group_id: str


class NewsGraphRunReportDTO(BaseModel):
    """Top-level report emitted by the news graph pipeline CLI."""

    run_id: str
    group_id: Optional[str] = None
    stages: Dict[str, Any] = Field(default_factory=dict)
    output_dir: str
    warnings: List[str] = Field(default_factory=list)
    crawler_summary: Optional[Dict[str, Any]] = None
    mcp_smoke_test: Optional[Dict[str, Any]] = None

