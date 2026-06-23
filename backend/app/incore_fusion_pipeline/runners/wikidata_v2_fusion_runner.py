"""Runnable first-pass fusion skeleton for Wikidata + Neo4j v2."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphImportBatchDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import (
    CanonicalNodeIndexDTO,
    FusionNodeDecisionDTO,
    FusionRunResultDTO,
    V2SourceEdgeDTO,
    V2SourceNodeDTO,
)
from app.incore_fusion_pipeline.loaders.neo4j_v2_export_loader import Neo4jV2ExportLoader
from app.incore_fusion_pipeline.loaders.wikidata_shard_canonical_index_loader import (
    WikidataShardCanonicalIndexLoader,
)
from app.incore_fusion_pipeline.mappers.wikidata_v2_source_mapper import WikidataV2SourceMapper
from app.incore_fusion_pipeline.resolvers.fusion_property_merger import FusionPropertyMerger
from app.incore_fusion_pipeline.resolvers.fusion_relation_planner import FusionRelationPlanner
from app.incore_fusion_pipeline.resolvers.wikidata_canonical_matcher import WikidataCanonicalMatcher


class WikidataV2FusionRunner:
    """Build a GraphImportBatchDTO from v2 nodes/edges using Wikidata as the skeleton."""

    DOCUMENT_TYPES = {"Document", "Episodic", "StoryThread"}
    CHUNK_TYPES = {"Chunk"}
    EVENT_TYPES = {"Event", "EnterpriseEvent", "OrganizationEvent"}

    def __init__(
        self,
        *,
        source_mapper: WikidataV2SourceMapper | None = None,
        export_loader: Neo4jV2ExportLoader | None = None,
        canonical_index_loader: WikidataShardCanonicalIndexLoader | None = None,
        matcher: WikidataCanonicalMatcher | None = None,
        property_merger: FusionPropertyMerger | None = None,
        relation_planner: FusionRelationPlanner | None = None,
    ):
        self.source_mapper = source_mapper or WikidataV2SourceMapper()
        self.export_loader = export_loader or Neo4jV2ExportLoader()
        self.canonical_index_loader = canonical_index_loader or WikidataShardCanonicalIndexLoader()
        self.matcher = matcher or WikidataCanonicalMatcher()
        self.property_merger = property_merger or FusionPropertyMerger()
        self.relation_planner = relation_planner or FusionRelationPlanner()

    def run(
        self,
        *,
        source_nodes: List[V2SourceNodeDTO],
        source_edges: List[V2SourceEdgeDTO],
        canonical_index: Iterable[CanonicalNodeIndexDTO],
        batch_id: str,
        project: str = "IncCore",
        namespace: str = "IncCore",
        source_namespace: str = "v2",
    ) -> FusionRunResultDTO:
        node_decisions: List[FusionNodeDecisionDTO] = []
        relation_decisions = []
        warnings: List[str] = []
        graph_id_by_source_uuid: Dict[str, str] = {}

        concept_nodes: List[GraphNodeUpsertDTO] = []
        entity_nodes: List[GraphNodeUpsertDTO] = []
        event_nodes: List[GraphNodeUpsertDTO] = []
        document_nodes: List[GraphNodeUpsertDTO] = []
        chunk_nodes: List[GraphNodeUpsertDTO] = []
        edges: List[GraphEdgeUpsertDTO] = []

        canonical_nodes = list(canonical_index)

        for source_node in source_nodes:
            mapped = self.source_mapper.map_source_node(source_node)
            matched, match_method, match_score = self.matcher.match(
                mapped_node=mapped,
                canonical_index=canonical_nodes,
            )
            resolved_graph_id = (
                self._build_news_profile_graph_id(source_node.source_uuid, source_namespace=source_namespace)
                if matched
                else self._build_fusion_graph_id(
                    mapped.normalized_type,
                    source_node.source_uuid,
                    source_namespace=source_namespace,
                )
            )
            decision = "merge" if matched else "create"
            node_decision = FusionNodeDecisionDTO(
                source_uuid=source_node.source_uuid,
                original_type=mapped.original_type,
                normalized_type=mapped.normalized_type,
                decision=decision,
                resolved_graph_id=resolved_graph_id,
                matched_graph_id=matched.graph_id if matched else None,
                match_method=match_method,
                match_score=match_score,
            )
            node_decisions.append(node_decision)
            graph_id_by_source_uuid[source_node.source_uuid] = resolved_graph_id

            properties = (
                self._build_news_profile_properties(
                    mapped_node=mapped,
                    source_node=source_node,
                    canonical_node=matched,
                    match_method=match_method,
                    match_score=match_score,
                    batch_id=batch_id,
                )
                if matched
                else self.property_merger.merge(mapped_node=mapped, canonical_node=None)
            )
            graph_node = GraphNodeUpsertDTO(
                type_name="NewsEntityProfile" if matched else mapped.normalized_type,
                graph_id=resolved_graph_id,
                name=mapped.name or (matched.name if matched else None),
                properties=properties,
            )
            self._append_node(
                graph_node=graph_node,
                normalized_type="NewsEntityProfile" if matched else mapped.normalized_type,
                concept_nodes=concept_nodes,
                entity_nodes=entity_nodes,
                event_nodes=event_nodes,
                document_nodes=document_nodes,
                chunk_nodes=chunk_nodes,
            )
            if matched:
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=resolved_graph_id,
                        predicate="refersTo",
                        object_graph_id=matched.graph_id,
                        properties={
                            "sourceSystem": source_node.source_system,
                            "sourceUuid": source_node.source_uuid,
                            "sourceType": mapped.original_type,
                            "targetLayer": "identity_link",
                            "fusionDecision": "link_to_canonical",
                            "matchMethod": match_method,
                            "matchScore": match_score,
                            "batchId": batch_id,
                        },
                    )
                )

        for source_edge in source_edges:
            resolved_subject_graph_id = graph_id_by_source_uuid.get(source_edge.subject_source_uuid)
            resolved_object_graph_id = graph_id_by_source_uuid.get(source_edge.object_source_uuid)
            plan = self.relation_planner.plan(
                source_edge,
                resolved_subject_graph_id=resolved_subject_graph_id,
                resolved_object_graph_id=resolved_object_graph_id,
            )
            relation_decisions.append(plan)
            if not resolved_subject_graph_id or not resolved_object_graph_id:
                warnings.append(f"skip_edge:{source_edge.source_edge_uuid}")
                continue
            edges.append(
                GraphEdgeUpsertDTO(
                    subject_graph_id=resolved_subject_graph_id,
                    predicate=plan.predicate,
                    object_graph_id=resolved_object_graph_id,
                    properties={
                        **(source_edge.properties or {}),
                        "sourceSystem": source_edge.source_system,
                        "sourceEdgeUuid": source_edge.source_edge_uuid,
                        "targetLayer": plan.target_layer,
                        "fusionDecision": plan.decision,
                        "evidenceRefs": plan.evidence_refs,
                    },
                )
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
            edges=edges,
            metadata={
                "source_system": ",".join(sorted({node.source_system for node in source_nodes})) or "unknown",
                "source_namespace": source_namespace,
                "node_decision_count": len(node_decisions),
                "relation_decision_count": len(relation_decisions),
            },
        )
        return FusionRunResultDTO(
            batch=batch,
            node_decisions=node_decisions,
            relation_decisions=relation_decisions,
            warnings=warnings,
        )

    def run_export_package(
        self,
        *,
        export_dir: str,
        canonical_index: Iterable[CanonicalNodeIndexDTO],
        batch_id: str,
        project: str = "IncCore",
        namespace: str = "IncCore",
        source_namespace: str = "v2",
    ) -> FusionRunResultDTO:
        package = self.export_loader.load(export_dir)
        return self.run(
            source_nodes=package.nodes,
            source_edges=package.edges,
            canonical_index=canonical_index,
            batch_id=batch_id,
            project=project,
            namespace=namespace,
            source_namespace=source_namespace,
        )

    def run_export_package_with_wikidata_shards(
        self,
        *,
        export_dir: str | Path,
        wikidata_shard_dir: str | Path,
        batch_id: str,
        project: str = "IncCore",
        namespace: str = "IncCore",
        source_namespace: str = "v2",
    ) -> FusionRunResultDTO:
        canonical_index = self.canonical_index_loader.load_from_dir(wikidata_shard_dir)
        return self.run_export_package(
            export_dir=str(export_dir),
            canonical_index=canonical_index,
            batch_id=batch_id,
            project=project,
            namespace=namespace,
            source_namespace=source_namespace,
        )

    def _append_node(
        self,
        *,
        graph_node: GraphNodeUpsertDTO,
        normalized_type: str,
        concept_nodes: List[GraphNodeUpsertDTO],
        entity_nodes: List[GraphNodeUpsertDTO],
        event_nodes: List[GraphNodeUpsertDTO],
        document_nodes: List[GraphNodeUpsertDTO],
        chunk_nodes: List[GraphNodeUpsertDTO],
    ) -> None:
        if normalized_type in self.DOCUMENT_TYPES:
            document_nodes.append(graph_node)
            return
        if normalized_type in self.CHUNK_TYPES:
            chunk_nodes.append(graph_node)
            return
        if normalized_type in self.EVENT_TYPES or normalized_type.endswith("Event"):
            event_nodes.append(graph_node)
            return
        if normalized_type.endswith("Concept"):
            concept_nodes.append(graph_node)
            return
        entity_nodes.append(graph_node)

    @staticmethod
    def _build_fusion_graph_id(type_name: str, source_uuid: str, *, source_namespace: str = "v2") -> str:
        return f"{type_name}:fusion:{source_namespace}:{source_uuid}"

    @staticmethod
    def _build_news_profile_graph_id(source_uuid: str, *, source_namespace: str = "v2") -> str:
        return f"NewsEntityProfile:{source_namespace}:{source_uuid}"

    def _build_news_profile_properties(
        self,
        *,
        mapped_node,
        source_node: V2SourceNodeDTO,
        canonical_node: CanonicalNodeIndexDTO,
        match_method: str | None,
        match_score: float,
        batch_id: str,
    ) -> dict:
        properties = self.property_merger.merge(mapped_node=mapped_node, canonical_node=None)
        source_profiles = dict(properties.get("sourceProfiles") or {})
        v2_profile = dict(source_profiles.get("v2") or {})
        v2_profile.update(
            {
                "sourceType": mapped_node.original_type,
                "sourceUuid": source_node.source_uuid,
                "canonicalGraphId": canonical_node.graph_id,
                "canonicalType": canonical_node.type_name,
                "matchMethod": match_method,
                "matchScore": match_score,
            }
        )
        source_profiles["v2"] = v2_profile
        properties["sourceProfiles"] = source_profiles
        properties["canonicalGraphId"] = canonical_node.graph_id
        properties["canonicalType"] = canonical_node.type_name
        properties["sourceSystem"] = source_node.source_system
        properties["sourceUuid"] = source_node.source_uuid
        properties["sourceType"] = mapped_node.original_type
        properties["matchMethod"] = match_method
        properties["matchScore"] = match_score
        properties["batchId"] = batch_id
        return properties
