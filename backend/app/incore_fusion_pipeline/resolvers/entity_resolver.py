"""Canonical entity resolution."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEntityDTO, ConceptBindingDTO, ConflictRecordDTO
from app.incore_fusion_pipeline.dto.normalized_dto import ConceptCandidateDTO, NormalizedEntityDTO, NormalizedEventDTO
from app.incore_fusion_pipeline.resolvers.conflict_resolver import ConflictResolver
from app.incore_fusion_pipeline.taxonomy import CompanyConceptClassifier
from app.incore_fusion_pipeline.utils import (
    build_region_graph_id,
    infer_region_category,
    normalize_company_core_name,
    normalize_region_name,
    normalize_text_key,
)


class EntityResolver:
    """Resolve normalized entities into canonical graph entities."""

    SOURCE_AUTHORITY = {
        "fact_library": 1.0,
        "report_pipeline": 0.9,
        "report_extract": 0.8,
        "graphiti": 0.7,
        "mongo_news": 0.6,
        "media_extract": 0.55,
    }

    INDUSTRY_RULES = {
        "人工智能": ("人工智能", "大模型", "机器学习", "计算机视觉", "智能算法"),
        "高端装备": ("机器人", "自动化", "机床", "伺服", "减速器", "控制器"),
        "半导体": ("芯片", "半导体", "集成电路", "晶圆", "封测"),
        "新能源": ("新能源", "储能", "电池", "光伏", "氢能"),
        "汽车": ("汽车", "整车", "汽配", "新能源车"),
        "生物医药": ("医药", "制药", "生物", "医疗器械", "基因"),
        "新材料": ("新材料", "碳纤维", "复合材料", "高分子"),
    }

    ORGANIZATION_CATEGORY_RULES = {
        "高校": ("大学", "学院"),
        "科研机构": ("研究院", "研究所", "实验室"),
        "行业组织": ("协会", "联盟", "学会"),
        "投资机构": ("资本", "创投", "基金", "投资"),
    }

    PERSON_CATEGORY_RULES = {
        "科研人才": ("教授", "研究员", "博士生导师", "学者"),
        "企业高管": ("董事长", "总经理", "创始人", "CEO", "总裁"),
    }

    def __init__(self, conflict_resolver: ConflictResolver | None = None):
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.company_classifier = CompanyConceptClassifier()

    def build_synthetic_entities_from_event_refs(self, events: List[NormalizedEventDTO]) -> List[NormalizedEntityDTO]:
        """Materialize minimal actor entities so event-only batches can still resolve."""

        synthetic_entities: List[NormalizedEntityDTO] = []
        seen = set()
        for event in events:
            for ref, role in ((event.subject_ref, "subject"), (event.object_ref, "object")):
                if ref is None or not ref.match_key:
                    continue
                canonical_type = self._normalize_actor_type(ref.type, ref.match_key, event.event_type, role)
                if canonical_type not in {"Company", "Organization", "Person"}:
                    continue
                key = (canonical_type, normalize_text_key(ref.match_key))
                if key in seen:
                    continue
                seen.add(key)
                synthetic_entities.append(
                    NormalizedEntityDTO(
                        canonical_type=canonical_type,
                        source_refs=event.source_refs,
                        primary_name=ref.match_key,
                        aliases=[],
                        external_keys={},
                        properties={"semanticType": canonical_type},
                        concept_candidates=self._infer_entity_concepts(
                            NormalizedEntityDTO(
                                canonical_type=canonical_type,
                                source_refs=event.source_refs,
                                primary_name=ref.match_key,
                                aliases=[],
                                external_keys={},
                                properties={"semanticType": canonical_type},
                            )
                        ),
                    )
                )
        return synthetic_entities

    def resolve_entities(
        self,
        entities: List[NormalizedEntityDTO],
        *,
        extra_region_names: Iterable[str] | None = None,
    ) -> Tuple[List[CanonicalEntityDTO], List[ConflictRecordDTO]]:
        grouped: Dict[str, List[NormalizedEntityDTO]] = defaultdict(list)
        region_index: Dict[str, Dict[str, object]] = {}

        for entity in entities:
            grouped[self._entity_graph_id(entity)].append(entity)
            self._collect_regions_from_entity(entity, region_index)

        for region_name in extra_region_names or []:
            self._upsert_region_seed(region_index, raw_name=region_name)

        canonical_entities: List[CanonicalEntityDTO] = []
        conflicts: List[ConflictRecordDTO] = []

        for graph_id, items in grouped.items():
            property_candidates = defaultdict(list)
            aliases = set()
            concept_bindings: Dict[Tuple[str, str], float] = {}
            external_keys: Dict[str, str] = {}
            merged_sources = []
            region_graph_ids = set()

            for item in items:
                authority = self._source_authority(item)
                aliases.update(alias for alias in item.aliases if alias)
                external_keys.update(item.external_keys)
                merged_sources.extend(item.source_refs)
                inferred_candidates = self._infer_entity_concepts(item)
                for field, value in item.properties.items():
                    if value in (None, "", []):
                        continue
                    source_name = item.source_refs[0].source_system if item.source_refs else "unknown"
                    property_candidates[field].append((value, authority, source_name))
                for region_graph_id in self._region_graph_ids_for_entity(item):
                    if region_graph_id:
                        region_graph_ids.add(region_graph_id)
                for candidate in [*item.concept_candidates, *inferred_candidates]:
                    if not candidate.concept_name:
                        continue
                    key = (candidate.concept_type, candidate.concept_name)
                    concept_bindings[key] = max(concept_bindings.get(key, 0.0), candidate.score)

            resolved_properties, item_conflicts = self.conflict_resolver.resolve_property_map(graph_id, property_candidates)
            conflicts.extend(item_conflicts)

            primary_item = items[0]
            primary_name = self._select_primary_name(items)
            resolved_properties["semanticType"] = resolved_properties.get("semanticType") or primary_item.canonical_type
            if primary_item.canonical_type == "Company":
                company_code = external_keys.get("credit_code") or external_keys.get("code")
                if company_code:
                    resolved_properties["code"] = company_code
            if region_graph_ids:
                resolved_properties["_region_graph_ids"] = sorted(region_graph_ids)

            canonical_entities.append(
                CanonicalEntityDTO(
                    graph_id=graph_id,
                    entity_type=primary_item.canonical_type,
                    primary_name=primary_name,
                    official_name=primary_name,
                    aliases=sorted({*aliases, *(item.primary_name for item in items if item.primary_name)}),
                    external_keys=external_keys,
                    merged_sources=merged_sources,
                    properties=resolved_properties,
                    concept_bindings=[
                        ConceptBindingDTO(
                            concept_type=concept_type,
                            concept_name=concept_name,
                            confidence=score,
                        )
                        for (concept_type, concept_name), score in sorted(concept_bindings.items())
                    ],
                )
            )

        canonical_entities.extend(self._build_region_entities(region_index))
        canonical_entities.sort(key=lambda item: (item.entity_type, item.graph_id))
        return canonical_entities, conflicts

    def build_lookup(self, entities: List[CanonicalEntityDTO]) -> Dict[str, str]:
        """Build a loose name/id lookup for downstream relation and event resolution."""

        lookup: Dict[str, str] = {}
        for entity in entities:
            for key in self._lookup_keys(entity):
                lookup[key] = entity.graph_id
        return lookup

    def _lookup_keys(self, entity: CanonicalEntityDTO) -> List[str]:
        keys = {
            normalize_text_key(entity.graph_id),
            normalize_text_key(entity.primary_name),
        }
        if entity.official_name:
            keys.add(normalize_text_key(entity.official_name))
        for alias in entity.aliases:
            keys.add(normalize_text_key(alias))
        for key_value in entity.external_keys.values():
            keys.add(normalize_text_key(key_value))
        if entity.entity_type == "Company":
            keys.add(normalize_company_core_name(entity.primary_name))
            for alias in entity.aliases:
                keys.add(normalize_company_core_name(alias))
        if entity.entity_type == "Region":
            for alias in entity.aliases:
                keys.add(normalize_region_name(alias))
            keys.add(normalize_region_name(entity.primary_name))
            if entity.official_name:
                keys.add(normalize_region_name(entity.official_name))
        return [item for item in keys if item and item != "unknown"]

    def _entity_graph_id(self, entity: NormalizedEntityDTO) -> str:
        canonical_type = entity.canonical_type
        if canonical_type == "Company":
            key = entity.external_keys.get("credit_code") or entity.external_keys.get("code") or entity.primary_name
            return f"Company:{normalize_text_key(key)}"
        if canonical_type == "Region":
            return build_region_graph_id(raw_name=entity.primary_name)
        if canonical_type == "Organization":
            return f"Organization:{normalize_text_key(entity.primary_name)}"
        if canonical_type == "Person":
            org = entity.properties.get("org") or entity.properties.get("organization") or ""
            suffix = f"@{normalize_text_key(org)}" if org else ""
            return f"Person:{normalize_text_key(entity.primary_name)}{suffix}"
        return f"{canonical_type}:{normalize_text_key(entity.primary_name)}"

    def _source_authority(self, entity: NormalizedEntityDTO) -> float:
        if not entity.source_refs:
            return 0.5
        source_system = entity.source_refs[0].source_system
        return self.SOURCE_AUTHORITY.get(source_system, 0.5)

    def _select_primary_name(self, items: List[NormalizedEntityDTO]) -> str:
        return max((item.primary_name for item in items if item.primary_name), key=len, default=items[0].primary_name)

    def _infer_entity_concepts(self, entity: NormalizedEntityDTO) -> List[ConceptCandidateDTO]:
        concepts: Dict[Tuple[str, str], float] = {}
        text_fields = " ".join(
            str(entity.properties.get(field, "") or "")
            for field in ("description", "businessScope", "business_scope", "status", "jobTitle", "job_title")
        )
        text = f"{entity.primary_name} {text_fields}"
        if entity.canonical_type == "Company":
            classification = self.company_classifier.classify_company(
                name=entity.primary_name,
                business_scope=str(
                    entity.properties.get("businessScope")
                    or entity.properties.get("business_scope")
                    or ""
                ),
                description=str(entity.properties.get("description") or ""),
            )
            for predicted in classification["company_categories"]:
                concepts[(predicted.concept_type, predicted.concept_name)] = max(
                    concepts.get((predicted.concept_type, predicted.concept_name), 0.0),
                    predicted.score,
                )
            for predicted in classification["industry_sectors"]:
                concepts[(predicted.concept_type, predicted.concept_name)] = max(
                    concepts.get((predicted.concept_type, predicted.concept_name), 0.0),
                    predicted.score,
                )
        elif entity.canonical_type == "Organization":
            self._apply_keyword_rules(concepts, "OrganizationCategory", text, self.ORGANIZATION_CATEGORY_RULES, 0.82)
            self._apply_keyword_rules(concepts, "IndustrySector", text, self.INDUSTRY_RULES, 0.65)
        elif entity.canonical_type == "Person":
            self._apply_keyword_rules(concepts, "PersonCategory", text, self.PERSON_CATEGORY_RULES, 0.75)
        elif entity.canonical_type == "Region":
            region_category = entity.properties.get("category") or infer_region_category(raw_name=entity.primary_name)
            if region_category:
                concepts[("RegionCategory", str(region_category))] = 1.0
        return [
            ConceptCandidateDTO(concept_type=concept_type, concept_name=concept_name, score=score)
            for (concept_type, concept_name), score in sorted(concepts.items())
        ]

    def _apply_keyword_rules(
        self,
        concept_map: Dict[Tuple[str, str], float],
        concept_type: str,
        text: str,
        rules: Dict[str, Tuple[str, ...]],
        score: float,
    ) -> None:
        for concept_name, keywords in rules.items():
            if any(keyword in text for keyword in keywords):
                concept_map[(concept_type, concept_name)] = max(concept_map.get((concept_type, concept_name), 0.0), score)

    def _collect_regions_from_entity(self, entity: NormalizedEntityDTO, region_index: Dict[str, Dict[str, object]]) -> None:
        province = normalize_region_name(entity.properties.get("province"))
        city = normalize_region_name(entity.properties.get("city"))
        if province:
            self._upsert_region_seed(region_index, raw_name=province)
        if province and city and city != province:
            self._upsert_region_seed(region_index, raw_name=province, city=city)
        elif city:
            self._upsert_region_seed(region_index, raw_name=city)

    def _upsert_region_seed(
        self,
        region_index: Dict[str, Dict[str, object]],
        *,
        raw_name: str,
        city: str | None = None,
    ) -> None:
        province = normalize_region_name(raw_name)
        normalized_city = normalize_region_name(city)
        graph_id = build_region_graph_id(province=province, city=normalized_city, raw_name=raw_name)
        display_name = normalized_city if normalized_city and normalized_city != province else province
        if not display_name:
            return
        region_data = region_index.setdefault(
            graph_id,
            {
                "graph_id": graph_id,
                "name": display_name,
                "official_name": display_name,
                "category": infer_region_category(province=province, city=normalized_city, raw_name=display_name),
                "aliases": set(),
            },
        )
        region_data["aliases"].add(str(raw_name))
        if city:
            region_data["aliases"].add(str(city))

    def _region_graph_ids_for_entity(self, entity: NormalizedEntityDTO) -> List[str]:
        province = normalize_region_name(entity.properties.get("province"))
        city = normalize_region_name(entity.properties.get("city"))
        graph_ids: List[str] = []
        if province:
            graph_ids.append(build_region_graph_id(raw_name=province))
        if city and city != province:
            graph_ids.append(build_region_graph_id(province=province or city, city=city))
        return graph_ids

    def _build_region_entities(self, region_index: Dict[str, Dict[str, object]]) -> List[CanonicalEntityDTO]:
        result: List[CanonicalEntityDTO] = []
        for region_data in region_index.values():
            result.append(
                CanonicalEntityDTO(
                    graph_id=str(region_data["graph_id"]),
                    entity_type="Region",
                    primary_name=str(region_data["name"]),
                    official_name=str(region_data["official_name"]),
                    aliases=sorted({item for item in region_data["aliases"] if item}),
                    external_keys={},
                    merged_sources=[],
                    properties={"semanticType": "Region"},
                    concept_bindings=[
                        ConceptBindingDTO(
                            concept_type="RegionCategory",
                            concept_name=str(region_data["category"]),
                            confidence=1.0,
                        )
                    ],
                )
            )
        return result

    def _normalize_actor_type(self, type_name: str, name: str, event_type: str, role: str) -> str:
        type_name = str(type_name or "").strip() or "IndustryActor"
        if type_name in {"Company", "Organization", "Person"}:
            return type_name
        if role == "subject" and event_type in {"CompanyFinancingEvent", "CompanyCooperationEvent"}:
            return "Company"
        if event_type == "CompanyFinancingEvent" and role == "object":
            return "Organization"
        if any(keyword in name for keyword in ("有限公司", "股份", "集团", "公司", "科技", "实业")):
            return "Company"
        if any(keyword in name for keyword in ("大学", "学院", "研究院", "研究所", "协会", "基金", "资本")):
            return "Organization"
        return "Organization"
