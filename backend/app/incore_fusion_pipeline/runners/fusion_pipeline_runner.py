"""End-to-end runner for the IncCore fusion pipeline skeleton."""

from __future__ import annotations

from typing import List

from app.incore_fusion_pipeline.builders.concept_batch_builder import ConceptBatchBuilder
from app.incore_fusion_pipeline.builders.entity_batch_builder import EntityBatchBuilder
from app.incore_fusion_pipeline.builders.event_batch_builder import EventBatchBuilder
from app.incore_fusion_pipeline.builders.evidence_batch_builder import EvidenceBatchBuilder
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphImportBatchDTO, GraphImportResultDTO
from app.incore_fusion_pipeline.dto.source_dto import SourceRecordDTO
from app.incore_fusion_pipeline.importers.openspg_importer import OpenSPGImporter
from app.incore_fusion_pipeline.mappers.event_mapper import EventMapper
from app.incore_fusion_pipeline.mappers.source_mapper import SourceMapper
from app.incore_fusion_pipeline.resolvers.entity_resolver import EntityResolver
from app.incore_fusion_pipeline.resolvers.event_resolver import EventResolver


class FusionPipelineRunner:
    """Small but runnable IncCore fusion pipeline.

    The goal of this class is not to implement every rule today, but to make
    the DTO layers and stage boundaries executable and easy to extend.
    """

    def __init__(
        self,
        *,
        source_mapper: SourceMapper | None = None,
        event_mapper: EventMapper | None = None,
        entity_resolver: EntityResolver | None = None,
        event_resolver: EventResolver | None = None,
        concept_builder: ConceptBatchBuilder | None = None,
        entity_builder: EntityBatchBuilder | None = None,
        event_builder: EventBatchBuilder | None = None,
        evidence_builder: EvidenceBatchBuilder | None = None,
        importer: OpenSPGImporter | None = None,
    ):
        self.source_mapper = source_mapper or SourceMapper()
        self.event_mapper = event_mapper or EventMapper()
        self.entity_resolver = entity_resolver or EntityResolver()
        self.event_resolver = event_resolver or EventResolver()
        self.concept_builder = concept_builder or ConceptBatchBuilder()
        self.entity_builder = entity_builder or EntityBatchBuilder()
        self.event_builder = event_builder or EventBatchBuilder()
        self.evidence_builder = evidence_builder or EvidenceBatchBuilder()
        self.importer = importer or OpenSPGImporter()

    def run(
        self,
        *,
        records: List[SourceRecordDTO],
        project: str = "IncCore",
        namespace: str = "IncCore",
        project_id: int | None = None,
        batch_id: str = "incore_fusion_batch_001",
        dry_run: bool = True,
    ) -> GraphImportResultDTO:
        entities, relations, documents, chunks, events, concept_seeds = self.source_mapper.map_records(records)
        enriched_events = [self.event_mapper.enrich(event) for event in events]
        synthetic_entities = self.entity_resolver.build_synthetic_entities_from_event_refs(enriched_events)
        event_region_names = [
            event.location_ref.match_key
            for event in enriched_events
            if event.location_ref is not None and event.location_ref.match_key
        ]

        canonical_entities, conflicts = self.entity_resolver.resolve_entities(
            [*entities, *synthetic_entities],
            extra_region_names=event_region_names,
        )
        entity_lookup = self.entity_resolver.build_lookup(canonical_entities)
        canonical_events = self.event_resolver.resolve_events(
            enriched_events,
            entity_lookup=entity_lookup,
            entities=canonical_entities,
        )

        concept_nodes, concept_edges = self.concept_builder.build(
            concept_seeds,
            canonical_entities,
            canonical_events,
        )
        entity_nodes, entity_edges = self.entity_builder.build(
            canonical_entities,
            relations,
            entity_lookup,
        )
        event_nodes, event_edges = self.event_builder.build(canonical_events)
        document_nodes, chunk_nodes, evidence_edges = self.evidence_builder.build(
            documents,
            chunks,
            canonical_events,
        )

        batch = GraphImportBatchDTO(
            project=project,
            namespace=namespace,
            batch_id=batch_id,
            concept_nodes=concept_nodes,
            entity_nodes=entity_nodes,
            event_nodes=event_nodes,
            document_nodes=document_nodes,
            chunk_nodes=chunk_nodes,
            edges=self._merge_edges(concept_edges, entity_edges, event_edges, evidence_edges),
            metadata={
                "project_id": project_id,
                "conflict_count": len(conflicts),
                "entity_count": len(canonical_entities),
                "event_count": len(canonical_events),
                "document_count": len(documents),
                "chunk_count": len(chunks),
            },
        )

        result = self.importer.import_batch(batch, dry_run=dry_run)
        result.details["conflicts"] = [
            item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in conflicts
        ]
        return result

    @staticmethod
    def _merge_edges(*edge_groups: List[GraphEdgeUpsertDTO]) -> List[GraphEdgeUpsertDTO]:
        merged: List[GraphEdgeUpsertDTO] = []
        seen = set()
        for group in edge_groups:
            for edge in group:
                key = (edge.subject_graph_id, edge.predicate, edge.object_graph_id)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(edge)
        return merged
