"""Canonical event resolution."""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO, CanonicalEventDTO, CanonicalEvidenceDTO, ConceptBindingDTO
from app.incore_fusion_pipeline.dto.normalized_dto import MatchReferenceDTO, NormalizedEventDTO
from app.incore_fusion_pipeline.utils import normalize_region_name, normalize_text_key


class EventResolver:
    """Resolve normalized events using canonical entity lookup tables."""

    IMPACT_RULES = {
        "资本支持": ("融资", "领投", "跟投", "投资"),
        "产业协同": ("合作", "签约", "共建", "协同"),
        "政策驱动": ("政策", "办法", "方案", "通知", "意见"),
        "产能扩张": ("扩产", "投建", "开工", "落地", "建设"),
        "成本波动": ("涨价", "提价", "价格上涨", "成本"),
    }

    def resolve_events(
        self,
        events: List[NormalizedEventDTO],
        *,
        entity_lookup: Dict[str, str],
        entities: List[CanonicalEntityDTO],
    ) -> List[CanonicalEventDTO]:
        entity_map = {entity.graph_id: entity for entity in entities}
        canonical_events: List[CanonicalEventDTO] = []

        for event in events:
            subject_graph_id = self._resolve_ref(event.subject_ref, entity_lookup)
            object_graph_id = self._resolve_ref(event.object_ref, entity_lookup)
            location_graph_id = self._resolve_location(event.location_ref, entity_lookup)
            graph_id = self._event_graph_id(
                event_type=event.event_type,
                subject_graph_id=subject_graph_id,
                object_graph_id=object_graph_id,
                location_graph_id=location_graph_id,
                event=event,
            )

            properties = dict(event.properties)
            properties["semanticType"] = properties.get("semanticType") or event.event_type
            if event.event_type == "GovernmentPublishPolicyEvent" and event.object_ref is not None:
                properties["object"] = event.object_ref.match_key

            concept_bindings = self._merge_concept_bindings(
                event=event,
                entity_map=entity_map,
                subject_graph_id=subject_graph_id,
                object_graph_id=object_graph_id,
            )

            canonical_events.append(
                CanonicalEventDTO(
                    graph_id=graph_id,
                    event_type=event.event_type,
                    name=event.name,
                    summary=event.summary,
                    subject_graph_id=subject_graph_id,
                    object_graph_id=self._event_object_graph_id(event.event_type, object_graph_id),
                    location_graph_id=location_graph_id,
                    category_name=event.category_ref.match_key if event.category_ref else None,
                    properties=properties,
                    evidence=CanonicalEvidenceDTO(
                        document_ids=event.source_document_ids,
                        chunk_ids=event.source_chunk_ids,
                    ),
                    concept_bindings=concept_bindings,
                    source_refs=event.source_refs,
                )
            )
        return canonical_events

    def _resolve_ref(self, ref: MatchReferenceDTO | None, entity_lookup: Dict[str, str]) -> str | None:
        if ref is None:
            return None
        key = normalize_text_key(ref.match_key)
        if key in entity_lookup:
            return entity_lookup[key]
        if ref.type == "Region":
            region_key = normalize_region_name(ref.match_key)
            return entity_lookup.get(region_key)
        return entity_lookup.get(key)

    def _resolve_location(self, ref: MatchReferenceDTO | None, entity_lookup: Dict[str, str]) -> str | None:
        if ref is None:
            return None
        region_key = normalize_region_name(ref.match_key)
        if region_key and region_key in entity_lookup:
            return entity_lookup[region_key]
        return self._resolve_ref(ref, entity_lookup)

    def _event_object_graph_id(self, event_type: str, object_graph_id: str | None) -> str | None:
        if event_type == "GovernmentPublishPolicyEvent":
            return None
        return object_graph_id

    def _event_graph_id(
        self,
        *,
        event_type: str,
        subject_graph_id: str | None,
        object_graph_id: str | None,
        location_graph_id: str | None,
        event: NormalizedEventDTO,
    ) -> str:
        event_time = event.properties.get("eventTime") or event.properties.get("publishTime")
        time_key = str(event_time)[:10] if event_time else "unknown"
        location_key = location_graph_id or (normalize_region_name(event.location_ref.match_key) if event.location_ref else "unknown")
        subject_key = subject_graph_id or (normalize_text_key(event.subject_ref.match_key) if event.subject_ref else "unknown_subject")
        object_key = object_graph_id or (normalize_text_key(event.object_ref.match_key) if event.object_ref else "unknown_object")
        return f"{event_type}:{subject_key}:{object_key}:{time_key}:{location_key}"

    def _merge_concept_bindings(
        self,
        *,
        event: NormalizedEventDTO,
        entity_map: Dict[str, CanonicalEntityDTO],
        subject_graph_id: str | None,
        object_graph_id: str | None,
    ) -> List[ConceptBindingDTO]:
        concepts: Dict[Tuple[str, str], float] = {}

        if event.category_ref and event.category_ref.match_key:
            concepts[("EventCategory", event.category_ref.match_key)] = 1.0

        for candidate in event.concept_candidates:
            self._upsert_concept(concepts, candidate.concept_type, candidate.concept_name, candidate.score)

        for graph_id in (subject_graph_id, object_graph_id):
            entity = entity_map.get(graph_id or "")
            if entity is None:
                continue
            for binding in entity.concept_bindings:
                if binding.concept_type == "IndustrySector":
                    self._upsert_concept(concepts, binding.concept_type, binding.concept_name, max(binding.confidence - 0.15, 0.55))

        event_text = " ".join(
            str(item or "")
            for item in (event.name, event.summary, *(event.properties.get("triggerTerms") or []))
        )
        for concept_name, keywords in self.IMPACT_RULES.items():
            if any(keyword in event_text for keyword in keywords):
                self._upsert_concept(concepts, "ImpactCategory", concept_name, 0.8)

        return [
            ConceptBindingDTO(concept_type=concept_type, concept_name=concept_name, confidence=score)
            for (concept_type, concept_name), score in sorted(concepts.items())
        ]

    @staticmethod
    def _upsert_concept(concepts: Dict[Tuple[str, str], float], concept_type: str, concept_name: str, score: float) -> None:
        if not concept_type or not concept_name:
            return
        key = (concept_type, concept_name)
        concepts[key] = max(concepts.get(key, 0.0), score)
