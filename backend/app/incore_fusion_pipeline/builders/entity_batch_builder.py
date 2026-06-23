"""Build canonical entity and relation upserts."""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.normalized_dto import NormalizedRelationDTO
from app.incore_fusion_pipeline.utils import normalize_text_key


class EntityBatchBuilder:
    """Translate canonical entities and resolved relations into graph upserts."""

    PROPERTY_ALLOWLIST = {
        "Company": {
            "description",
            "alias",
            "officialName",
            "semanticType",
            "nameEn",
            "code",
            "foundedDate",
            "status",
            "website",
            "businessScope",
            "companyScale",
        },
        "Organization": {"description", "alias", "officialName", "semanticType", "website"},
        "Person": {"description", "alias", "officialName", "semanticType", "nameEn", "gender", "jobTitle", "eduDgree", "birthYear", "honors"},
        "Region": {"description", "alias", "officialName", "semanticType"},
        "IndustryNode": {"description", "alias", "officialName", "semanticType", "nameEn"},
        "Technology": {"description", "alias", "officialName", "semanticType"},
        "ProductObject": {"description", "alias", "officialName", "semanticType", "brand", "model"},
        "DataSource": {"description", "confidence", "sourceType", "authorityLevel"},
    }

    def build(
        self,
        entities: List[CanonicalEntityDTO],
        relations: List[NormalizedRelationDTO],
        entity_lookup: Dict[str, str],
    ) -> Tuple[List[GraphNodeUpsertDTO], List[GraphEdgeUpsertDTO]]:
        nodes: List[GraphNodeUpsertDTO] = []
        edges: List[GraphEdgeUpsertDTO] = []

        for entity in entities:
            nodes.append(
                GraphNodeUpsertDTO(
                    type_name=entity.entity_type,
                    graph_id=entity.graph_id,
                    name=entity.primary_name,
                    properties=self._node_properties(entity),
                )
            )
            for region_graph_id in entity.properties.get("_region_graph_ids", []):
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=entity.graph_id,
                        predicate="region",
                        object_graph_id=region_graph_id,
                    )
                )

        for relation in relations:
            subject_id = entity_lookup.get(normalize_text_key(relation.subject_ref.match_key))
            object_id = entity_lookup.get(normalize_text_key(relation.object_ref.match_key))
            if not subject_id or not object_id:
                continue
            edges.append(
                GraphEdgeUpsertDTO(
                    subject_graph_id=subject_id,
                    predicate=relation.predicate,
                    object_graph_id=object_id,
                    properties=relation.properties,
                )
            )

        return nodes, self._dedupe_edges(edges)

    def _node_properties(self, entity: CanonicalEntityDTO) -> Dict[str, object]:
        properties = dict(entity.properties)
        properties.setdefault("officialName", entity.official_name)
        properties.setdefault("alias", entity.aliases)
        properties.setdefault("semanticType", entity.entity_type)
        allowlist = self.PROPERTY_ALLOWLIST.get(entity.entity_type, {"description", "alias", "officialName", "semanticType"})
        return {
            key: value
            for key, value in properties.items()
            if key in allowlist and value not in (None, "", [])
        }

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
