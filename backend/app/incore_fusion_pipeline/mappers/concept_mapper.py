"""Map concept seeds and concept bindings into graph-ready structures."""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO, CanonicalEventDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.normalized_dto import NormalizedConceptSeedDTO
from app.incore_fusion_pipeline.taxonomy import COMPANY_CATEGORY_PARENT_MAP, INDUSTRY_SECTOR_PARENT_MAP
from app.incore_fusion_pipeline.utils import normalize_text_key


class ConceptMapper:
    """Build concept nodes and instance-to-concept edges."""

    DEFAULT_PARENT = {
        "IndustrySector": INDUSTRY_SECTOR_PARENT_MAP,
        "CompanyCategory": COMPANY_CATEGORY_PARENT_MAP,
        "OrganizationCategory": {
            "高校": "机构分类",
            "科研机构": "机构分类",
            "行业组织": "机构分类",
            "投资机构": "机构分类",
        },
        "PersonCategory": {
            "科研人才": "人物分类",
            "企业高管": "人物分类",
        },
        "RegionCategory": {
            "省级行政区": "区域分类",
            "地市级行政区": "区域分类",
        },
        "EventCategory": {
            "政策发布": "产业事件",
            "企业合作": "产业事件",
            "企业融资": "产业事件",
            "泛化事件": "产业事件",
        },
        "ImpactCategory": {
            "资本支持": "影响分类",
            "产业协同": "影响分类",
            "政策驱动": "影响分类",
            "产能扩张": "影响分类",
            "成本波动": "影响分类",
        },
    }

    def build_concept_graph(
        self,
        concept_seeds: List[NormalizedConceptSeedDTO],
        entities: List[CanonicalEntityDTO],
        events: List[CanonicalEventDTO],
    ) -> Tuple[List[GraphNodeUpsertDTO], List[GraphEdgeUpsertDTO]]:
        concept_nodes: List[GraphNodeUpsertDTO] = []
        concept_edges: List[GraphEdgeUpsertDTO] = []
        seen_nodes = set()
        seen_edges = set()

        for seed in concept_seeds:
            self._ensure_concept_node(
                concept_nodes,
                concept_edges,
                seen_nodes,
                seen_edges,
                concept_type=seed.concept_type,
                concept_name=seed.name,
                parent_name=seed.parent_name or self._default_parent(seed.concept_type, seed.name),
                description=seed.description,
                aliases=seed.aliases,
                properties=seed.properties,
            )

        for entity in entities:
            for binding in entity.concept_bindings:
                self._ensure_concept_node(
                    concept_nodes,
                    concept_edges,
                    seen_nodes,
                    seen_edges,
                    concept_type=binding.concept_type,
                    concept_name=binding.concept_name,
                    parent_name=self._default_parent(binding.concept_type, binding.concept_name),
                )
                predicate = self._binding_predicate(source_type=entity.entity_type, concept_type=binding.concept_type)
                if not predicate:
                    continue
                self._append_edge(
                    concept_edges,
                    seen_edges,
                    GraphEdgeUpsertDTO(
                        subject_graph_id=entity.graph_id,
                        predicate=predicate,
                        object_graph_id=self._concept_graph_id(binding.concept_type, binding.concept_name),
                        properties={"confidence": binding.confidence},
                    ),
                )

        for event in events:
            for binding in event.concept_bindings:
                self._ensure_concept_node(
                    concept_nodes,
                    concept_edges,
                    seen_nodes,
                    seen_edges,
                    concept_type=binding.concept_type,
                    concept_name=binding.concept_name,
                    parent_name=self._default_parent(binding.concept_type, binding.concept_name),
                )
                predicate = self._binding_predicate(source_type=event.event_type, concept_type=binding.concept_type)
                if not predicate:
                    continue
                self._append_edge(
                    concept_edges,
                    seen_edges,
                    GraphEdgeUpsertDTO(
                        subject_graph_id=event.graph_id,
                        predicate=predicate,
                        object_graph_id=self._concept_graph_id(binding.concept_type, binding.concept_name),
                        properties={"confidence": binding.confidence},
                    ),
                )

        return concept_nodes, concept_edges

    def _ensure_concept_node(
        self,
        concept_nodes: List[GraphNodeUpsertDTO],
        concept_edges: List[GraphEdgeUpsertDTO],
        seen_nodes: set,
        seen_edges: set,
        *,
        concept_type: str,
        concept_name: str,
        parent_name: str | None = None,
        description: str | None = None,
        aliases: List[str] | None = None,
        properties: Dict[str, object] | None = None,
    ) -> None:
        if not concept_type or not concept_name:
            return
        concept_graph_id = self._concept_graph_id(concept_type, concept_name)
        if concept_graph_id not in seen_nodes:
            concept_nodes.append(
                GraphNodeUpsertDTO(
                    type_name=concept_type,
                    graph_id=concept_graph_id,
                    name=concept_name,
                    properties={
                        key: value
                        for key, value in {
                            "description": description,
                            "alias": aliases or [],
                            "semanticType": concept_type,
                            **(properties or {}),
                        }.items()
                        if value not in (None, "", [])
                    },
                )
            )
            seen_nodes.add(concept_graph_id)

        if parent_name and normalize_text_key(parent_name) != normalize_text_key(concept_name):
            grand_parent_name = self._default_parent(concept_type, parent_name)
            if grand_parent_name and normalize_text_key(grand_parent_name) != normalize_text_key(parent_name):
                self._ensure_concept_node(
                    concept_nodes,
                    concept_edges,
                    seen_nodes,
                    seen_edges,
                    concept_type=concept_type,
                    concept_name=parent_name,
                    parent_name=grand_parent_name,
                )
            parent_graph_id = self._concept_graph_id(concept_type, parent_name)
            if parent_graph_id not in seen_nodes:
                concept_nodes.append(
                    GraphNodeUpsertDTO(
                        type_name=concept_type,
                        graph_id=parent_graph_id,
                        name=parent_name,
                        properties={"semanticType": concept_type},
                    )
                )
                seen_nodes.add(parent_graph_id)
            self._append_edge(
                concept_edges,
                seen_edges,
                GraphEdgeUpsertDTO(
                    subject_graph_id=concept_graph_id,
                    predicate="isA",
                    object_graph_id=parent_graph_id,
                ),
            )

    def _append_edge(
        self,
        concept_edges: List[GraphEdgeUpsertDTO],
        seen_edges: set,
        edge: GraphEdgeUpsertDTO,
    ) -> None:
        key = (edge.subject_graph_id, edge.predicate, edge.object_graph_id)
        if key in seen_edges:
            return
        seen_edges.add(key)
        concept_edges.append(edge)

    @staticmethod
    def _concept_graph_id(concept_type: str, concept_name: str) -> str:
        return f"{concept_type}:{concept_name.strip()}"

    def _default_parent(self, concept_type: str, concept_name: str) -> str | None:
        return self.DEFAULT_PARENT.get(concept_type, {}).get(concept_name)

    @staticmethod
    def _binding_predicate(source_type: str, concept_type: str) -> str | None:
        if concept_type == "EventCategory":
            return None
        if concept_type == "ImpactCategory" and source_type.endswith("Event"):
            return "impactCategory"
        if concept_type == "IndustrySector":
            if source_type.endswith("Event"):
                return "relatedIndustry"
            if source_type in {"Company", "ProductObject"}:
                return "industry"
        if concept_type in {
            "CompanyCategory",
            "OrganizationCategory",
            "PersonCategory",
            "ProductCategory",
            "TechnologyCategory",
            "RegionCategory",
        }:
            return "category"
        return "belongTo"
