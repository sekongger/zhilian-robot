"""DTOs for the Wikipedia/Wikidata industry-chain base graph pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RouteType = Literal["core", "intrinsic", "relational", "unclaimed"]


class WikiDumpRecordDTO(BaseModel):
    source: str = "wikidata"
    entity_id: str
    raw: Dict[str, Any] = Field(default_factory=dict)


class WikiEntityCandidateDTO(BaseModel):
    source: str = "wikidata"
    entity_id: str
    label: str
    labels: Dict[str, str] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    language: str = "en"
    sitelinks: Dict[str, Any] = Field(default_factory=dict)
    claims: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    matched_reasons: List[str] = Field(default_factory=list)
    candidate_categories: List[str] = Field(default_factory=list)


class WikiClaimDTO(BaseModel):
    source: str = "wikidata"
    subject_id: str
    subject_label: str
    property_id: str
    property_label: Optional[str] = None
    value_id: Optional[str] = None
    value_label: Optional[str] = None
    value_literal: Any = None
    value_datatype: Optional[str] = None
    qualifiers: Dict[str, Any] = Field(default_factory=dict)
    references: List[Dict[str, Any]] = Field(default_factory=list)


class RoutedClaimDTO(BaseModel):
    source: str = "wikidata"
    subject_id: str
    subject_label: str
    subject_category: str
    property_id: str
    route: RouteType
    module: Optional[str] = None
    property_name: Optional[str] = None
    target_type: Optional[str] = None
    edge_type: Optional[str] = None
    direction: Literal["forward", "reverse"] = "forward"
    value_id: Optional[str] = None
    value_label: Optional[str] = None
    value_literal: Any = None
    value_datatype: Optional[str] = None
    confidence: float = 1.0
    route_reason: str = ""


class WikiGraphBuildBatchDTO(BaseModel):
    source_batch_id: str
    entities: List[WikiEntityCandidateDTO] = Field(default_factory=list)
    claims: List[WikiClaimDTO] = Field(default_factory=list)
    routed_claims: List[RoutedClaimDTO] = Field(default_factory=list)
    unclaimed: List[WikiClaimDTO] = Field(default_factory=list)
    entity_contexts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WikiCoverageReportDTO(BaseModel):
    raw_record_count: int = 0
    candidate_count: int = 0
    claim_count: int = 0
    routed_claim_count: int = 0
    intrinsic_claim_count: int = 0
    relational_claim_count: int = 0
    unclaimed_count: int = 0
    stub_node_count: int = 0
    claim_routing_rate: float = 0.0
    intrinsic_claim_rate: float = 0.0
    relational_claim_rate: float = 0.0
    unclaimed_rate: float = 0.0
    top_properties: List[Dict[str, Any]] = Field(default_factory=list)
    top_unclaimed_properties: List[Dict[str, Any]] = Field(default_factory=list)
