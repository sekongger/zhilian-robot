"""Build event graph upserts."""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEventDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphNodeUpsertDTO


class EventBatchBuilder:
    """Translate canonical events into event nodes and event edges."""

    PROPERTY_ALLOWLIST = {
        "Event": {"summary", "semanticType", "publishTime", "eventTime", "endTime", "confidence"},
        "GovernmentPublishPolicyEvent": {
            "summary",
            "semanticType",
            "publishTime",
            "eventTime",
            "confidence",
            "policyNo",
            "policyLevel",
            "policyType",
            "object",
        },
        "CompanyCooperationEvent": {
            "summary",
            "semanticType",
            "publishTime",
            "eventTime",
            "confidence",
            "cooperationMode",
            "contractAmount",
        },
        "CompanyFinancingEvent": {
            "summary",
            "semanticType",
            "publishTime",
            "eventTime",
            "confidence",
            "financingAmount",
            "financingRound",
            "financingPurpose",
        },
    }

    def build(self, events: List[CanonicalEventDTO]) -> Tuple[List[GraphNodeUpsertDTO], List[GraphEdgeUpsertDTO]]:
        nodes: List[GraphNodeUpsertDTO] = []
        edges: List[GraphEdgeUpsertDTO] = []

        for event in events:
            nodes.append(
                GraphNodeUpsertDTO(
                    type_name=event.event_type,
                    graph_id=event.graph_id,
                    name=event.name,
                    properties=self._node_properties(event),
                )
            )

            if event.subject_graph_id:
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate="subject",
                        object_graph_id=event.subject_graph_id,
                    )
                )
            if event.object_graph_id:
                predicate = "object" if event.event_type in {"CompanyCooperationEvent", "CompanyFinancingEvent"} else "relatedActor"
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate=predicate,
                        object_graph_id=event.object_graph_id,
                    )
                )
            if event.location_graph_id:
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate="location",
                        object_graph_id=event.location_graph_id,
                    )
                )
            if event.category_name:
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate="category",
                        object_graph_id=f"EventCategory:{event.category_name}",
                    )
                )

            for binding in event.concept_bindings:
                predicate = self._binding_predicate(binding.concept_type)
                if not predicate:
                    continue
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate=predicate,
                        object_graph_id=f"{binding.concept_type}:{binding.concept_name}",
                        properties={"confidence": binding.confidence},
                    )
                )

        return nodes, self._dedupe_edges(edges)

    def _node_properties(self, event: CanonicalEventDTO) -> Dict[str, object]:
        properties = dict(event.properties)
        allowlist = self.PROPERTY_ALLOWLIST.get(event.event_type, self.PROPERTY_ALLOWLIST["Event"])
        return {
            key: value
            for key, value in properties.items()
            if key in allowlist and value not in (None, "", [])
        }

    @staticmethod
    def _binding_predicate(concept_type: str) -> str | None:
        if concept_type == "EventCategory":
            return None
        if concept_type == "IndustrySector":
            return "relatedIndustry"
        if concept_type == "ImpactCategory":
            return "impactCategory"
        return None

    @staticmethod
    def _dedupe_edges(edges: List[GraphEdgeUpsertDTO]) -> List[GraphEdgeUpsertDTO]:
        deduped: List[GraphEdgeUpsertDTO] = []
        seen = set()
        for edge in edges:
            key = (edge.subject_graph_id, edge.predicate, edge.object_graph_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped
