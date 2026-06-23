"""Map routed wiki claims to IncCore/OpenSPG graph import batches."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

from app.incore_fusion_pipeline.dto.graph_import_dto import (
    GraphEdgeUpsertDTO,
    GraphImportBatchDTO,
    GraphNodeUpsertDTO,
)
from app.wiki_industry_pipeline.dto import RoutedClaimDTO, WikiEntityCandidateDTO, WikiGraphBuildBatchDTO


class WikiIndustryGraphMapper:
    def map_batch(self, batch: WikiGraphBuildBatchDTO) -> GraphImportBatchDTO:
        node_map: Dict[str, GraphNodeUpsertDTO] = {}
        entity_category_by_id: Dict[str, str] = {}
        entity_contexts = batch.entity_contexts or {}

        for candidate in batch.entities:
            category = _primary_category(candidate)
            entity_category_by_id[candidate.entity_id] = category
            node = self._candidate_node(candidate, category)
            node_map[node.graph_id] = node

        edges: List[GraphEdgeUpsertDTO] = []
        for routed in batch.routed_claims:
            if routed.route == "intrinsic":
                self._apply_intrinsic(node_map, entity_category_by_id, routed)
            elif routed.route == "relational" and routed.value_id and routed.edge_type and routed.target_type:
                subject_category = entity_category_by_id.get(routed.subject_id, routed.subject_category)
                subject_id = _graph_id(subject_category, routed.subject_id)
                target_category = entity_category_by_id.get(routed.value_id) or _type_name(routed.target_type)
                target_id = _graph_id(target_category, routed.value_id)
                if target_id not in node_map:
                    context = entity_contexts.get(routed.value_id or "", {})
                    stub_label = routed.value_label or str(context.get("label") or "")
                    node_map[target_id] = self._stub_node(
                        target_category,
                        routed.value_id,
                        stub_label or None,
                        context=context,
                    )
                source_id, object_id = (
                    (target_id, subject_id) if routed.direction == "reverse" else (subject_id, target_id)
                )
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=source_id,
                        predicate=routed.edge_type,
                        object_graph_id=object_id,
                        properties={"_source": routed.source, "_propertyId": routed.property_id},
                    )
                )

        nodes = list(node_map.values())
        return GraphImportBatchDTO(
            project="IncCore",
            namespace="IncCore",
            batch_id=batch.source_batch_id,
            concept_nodes=[node for node in nodes if node.type_name.endswith("Category")],
            entity_nodes=[node for node in nodes if not node.type_name.endswith("Category")],
            edges=_dedupe_edges(edges),
            metadata=dict(batch.metadata),
        )

    def _candidate_node(self, candidate: WikiEntityCandidateDTO, category: str) -> GraphNodeUpsertDTO:
        properties = {
            "name": candidate.label,
            "officialName": candidate.label,
            "alias": candidate.aliases,
            "description": candidate.description,
            "_externalId": candidate.entity_id,
            "_semanticType": "wiki_core",
            "_source": candidate.source,
        }
        english_labels = _english_labels(candidate)
        if english_labels:
            properties["nameEn"] = english_labels
        if category == "Enterprise" and candidate.description:
            properties["mainBusiness"] = candidate.description
            properties["businessScope"] = candidate.description
        return GraphNodeUpsertDTO(
            type_name=category,
            graph_id=_graph_id(category, candidate.entity_id),
            name=candidate.label,
            properties=properties,
        )

    def _stub_node(
        self,
        category: str,
        entity_id: str,
        label: str | None,
        *,
        context: Dict[str, object] | None = None,
    ) -> GraphNodeUpsertDTO:
        resolved_context = context or {}
        labels = resolved_context.get("labels") or {}
        aliases = resolved_context.get("aliases") or []
        description = resolved_context.get("description")
        official_name = str(resolved_context.get("officialName") or "").strip()
        short_name = str(resolved_context.get("shortName") or "").strip()
        english_name = str((labels or {}).get("en") or "").strip() if isinstance(labels, dict) else ""
        properties = {
            "name": label or entity_id,
            "_externalId": entity_id,
            "_semanticType": "stub",
            "_source": "wikidata",
        }
        if official_name:
            properties["officialName"] = official_name
        if short_name:
            properties["shortName"] = short_name
        if aliases:
            properties["alias"] = aliases
        if description:
            properties["description"] = description
        if english_name:
            properties["nameEn"] = [english_name]
        return GraphNodeUpsertDTO(
            type_name=category,
            graph_id=_graph_id(category, entity_id),
            name=label or entity_id,
            properties=properties,
        )

    def _apply_intrinsic(
        self,
        node_map: Dict[str, GraphNodeUpsertDTO],
        entity_category_by_id: Dict[str, str],
        routed: RoutedClaimDTO,
    ) -> None:
        if not routed.property_name:
            return
        category = entity_category_by_id.get(routed.subject_id, routed.subject_category)
        node = node_map.get(_graph_id(category, routed.subject_id))
        if node is None:
            return
        value = routed.value_literal if routed.value_literal is not None else routed.value_label or routed.value_id
        coerced_value = _coerce_property_value(routed.property_name, value)
        _set_property(node.properties, routed.property_name, coerced_value)
        if (
            category == "ProductModel"
            and routed.property_name == "publishDate"
            and node.properties.get("productLifecycleStatus") in (None, "", [])
        ):
            node.properties["productLifecycleStatus"] = "launched"


def _primary_category(candidate: WikiEntityCandidateDTO) -> str:
    return candidate.candidate_categories[0] if candidate.candidate_categories else "Technology"


def _type_name(target_type: str) -> str:
    return target_type.split(".")[-1]


def _graph_id(category: str, entity_id: str) -> str:
    return f"{category}:wiki:{entity_id}"


def _dedupe_edges(edges: Iterable[GraphEdgeUpsertDTO]) -> List[GraphEdgeUpsertDTO]:
    seen: set[Tuple[str, str, str]] = set()
    result: List[GraphEdgeUpsertDTO] = []
    for edge in edges:
        key = (edge.subject_graph_id, edge.predicate, edge.object_graph_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result


def _set_property(properties: Dict[str, object], key: str, value: object) -> None:
    if value in (None, "", []):
        return
    if key in {"alias", "officialWebsite", "nameEn", "specification"}:
        existing = properties.get(key)
        values = list(existing) if isinstance(existing, list) else ([existing] if existing else [])
        incoming = value if isinstance(value, list) else [value]
        for item in incoming:
            if item not in values:
                values.append(item)
        properties[key] = values
        return
    properties[key] = value


def _coerce_property_value(property_name: str, value: object) -> object:
    if property_name == "status":
        return _coerce_status(value)
    if property_name.endswith("Date") or property_name in {"inception"}:
        return _coerce_date(value)
    if property_name == "companyScale" and value is not None:
        return str(value)
    return value


def _coerce_date(value: object) -> object:
    if not isinstance(value, str):
        return value
    match = re.match(r"^\+?(\d{4})-(\d{2})-(\d{2})", value.strip())
    if not match:
        return value
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _coerce_status(value: object) -> object:
    if value in (None, "", []):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.match(r"^\+?\d{4}-\d{2}-\d{2}", text):
            return "inactive"
        return text
    return value


def _english_labels(candidate: WikiEntityCandidateDTO) -> List[str]:
    labels: List[str] = []
    direct_en = str(candidate.labels.get("en") or "").strip()
    if direct_en:
        labels.append(direct_en)
    return labels
