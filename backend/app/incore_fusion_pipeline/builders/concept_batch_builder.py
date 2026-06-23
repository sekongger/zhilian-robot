"""Build concept graph upserts."""

from __future__ import annotations

from typing import List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO, CanonicalEventDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.normalized_dto import NormalizedConceptSeedDTO
from app.incore_fusion_pipeline.mappers.concept_mapper import ConceptMapper


class ConceptBatchBuilder:
    """Build concept nodes and instance-to-concept edges."""

    def __init__(self, concept_mapper: ConceptMapper | None = None):
        self.concept_mapper = concept_mapper or ConceptMapper()

    def build(
        self,
        concept_seeds: List[NormalizedConceptSeedDTO],
        entities: List[CanonicalEntityDTO],
        events: List[CanonicalEventDTO],
    ) -> Tuple[List[GraphNodeUpsertDTO], List[GraphEdgeUpsertDTO]]:
        return self.concept_mapper.build_concept_graph(concept_seeds, entities, events)
