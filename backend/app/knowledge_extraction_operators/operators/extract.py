"""Extraction operators with KAG-backed execution and lightweight fallback."""

from __future__ import annotations

import re

from config.settings import settings

from app.knowledge_extraction_operators.base import KnowledgeOperatorABC, OperatorSpec
from app.knowledge_extraction_operators.dto import (
    ChunkDTO,
    ChunkEntityBundleDTO,
    ConceptSeedListDTO,
    EntitySeedDTO,
    EntitySeedListDTO,
    EventSeedDTO,
    EventSeedListDTO,
    RelationSeedDTO,
    RelationSeedListDTO,
)
from app.knowledge_extraction_operators.kag_bridge import (
    chunk_dto_to_kag_chunk,
    ensure_kag_import_path,
    ensure_kag_task_config,
)
from app.knowledge_extraction_operators.operators.kag_adapter import (
    KagExtractionPayload,
    disable_kag_backend,
)
from app.knowledge_extraction_operators.registry import register_operator

ensure_kag_import_path()

from kag.builder.component.extractor.schema_constraint_extractor import (  # noqa: E402
    SchemaConstraintExtractor,
)


ORG_PATTERN = re.compile(
    r"[\u4e00-\u9fffA-Za-z0-9]{2,40}(?:公司|集团|基金|大学|学院|研究院|研究所|实验室|银行|协会)"
)
GENERIC_NAMES = {"公司", "企业", "机构", "学校", "大学"}
LEADING_PREFIXES = [
    "投资方为",
    "投资方",
    "随后公司与",
    "随后与",
    "公司与",
    "随后",
    "以及",
    "与",
]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name).strip("，,。.；;（）()[]【】")


def _trim_entity_name(name: str) -> str:
    normalized = _normalize_name(name)
    changed = True
    while changed:
        changed = False
        for prefix in LEADING_PREFIXES:
            if normalized.startswith(prefix) and len(normalized) > len(prefix):
                normalized = normalized[len(prefix) :]
                changed = True
    return _normalize_name(normalized)


def _classify_entity(name: str) -> str:
    if name.endswith(("公司", "集团")):
        return "Company"
    if name.endswith("基金"):
        return "Organization"
    if name.endswith(("大学", "学院", "研究院", "研究所", "实验室", "协会")):
        return "Organization"
    return "Entity"


def _extract_names(text: str) -> list[str]:
    names = []
    for match in ORG_PATTERN.findall(text):
        name = _trim_entity_name(match)
        if not name or name in GENERIC_NAMES:
            continue
        names.append(name)
    return _dedupe_preserve_order(names)


def _leading_company(text: str, entities: list[EntitySeedDTO]) -> str | None:
    for entity in entities:
        if entity.entity_type == "Company":
            return entity.name
    company_match = re.match(r"([\u4e00-\u9fffA-Za-z0-9]{2,40}公司)", text)
    if company_match:
        return _normalize_name(company_match.group(1))
    return None


def _entity_seed_from_kag_record(record: dict) -> EntitySeedDTO | None:
    category = str(record.get("category") or "").strip()
    name = _normalize_name(str(record.get("name") or "").strip())
    if not category or not name:
        return None
    properties = dict(record.get("properties") or {})
    aliases: list[str] = []
    official_name = _normalize_name(str(record.get("official_name") or "").strip())
    if official_name and official_name != name:
        aliases.append(name)
        name = official_name
    return EntitySeedDTO(
        entity_type=category,
        name=name,
        aliases=_dedupe_preserve_order([alias for alias in aliases if alias]),
        properties=properties,
    )


def _event_seed_from_kag_record(record: dict) -> EventSeedDTO | None:
    category = str(record.get("category") or "").strip()
    properties = dict(record.get("properties") or {})
    if not category:
        return None
    name = _normalize_name(str(properties.get("name") or record.get("name") or "").strip())
    if not name:
        return None
    subject_name = properties.get("subject") or properties.get("subject_name")
    object_name = properties.get("object") or properties.get("object_name")
    event_time = properties.get("time") or properties.get("event_time")
    location = properties.get("location")
    passthrough = {
        key: value
        for key, value in properties.items()
        if key not in {"name", "subject", "subject_name", "object", "object_name", "time", "event_time", "location"}
    }
    return EventSeedDTO(
        event_type=category,
        name=name,
        subject_name=_normalize_name(str(subject_name)) if subject_name else None,
        object_name=_normalize_name(str(object_name)) if object_name else None,
        event_time=str(event_time) if event_time is not None else None,
        location=str(location) if location is not None else None,
        properties=passthrough,
    )


class KagSchemaConstraintOperatorBase(SchemaConstraintExtractor, KnowledgeOperatorABC):
    """Workbench operator base that executes KAG SchemaConstraintExtractor directly."""

    def __init__(self):
        self._kag_initialized = False
        self._kag_init_error: str | None = None
        try:
            self._initialize_kag_component()
        except Exception as exc:
            self._kag_init_error = str(exc)
            disable_kag_backend(f"schema constraint init failure: {exc}")

    def _initialize_kag_component(self) -> None:
        from kag.builder.prompt.spg_prompt import SPGEventPrompt, SPGRelationPrompt  # noqa: F401
        from kag.common.llm.openai_client import OpenAIClient
        from kag.interface import PromptABC

        if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL or not settings.OPENAI_API_BASE:
            raise RuntimeError("missing OpenAI settings for KAG SchemaConstraintExtractor")

        task_id = ensure_kag_task_config()
        SchemaConstraintExtractor.__init__(
            self,
            llm=OpenAIClient(
                base_url=settings.OPENAI_API_BASE,
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
                kag_qa_task_config_key=task_id,
            ),
            relation_prompt=PromptABC.from_config({"type": "spg_relation"}),
            event_prompt=PromptABC.from_config({"type": "spg_event"}),
            kag_qa_task_config_key=task_id,
        )
        self._kag_initialized = True

    def _extract_payload(self, chunk: ChunkDTO) -> KagExtractionPayload | None:
        if not self._kag_initialized:
            return None
        try:
            kag_chunk = chunk_dto_to_kag_chunk(chunk)
            passage = f"{kag_chunk.name}\n{kag_chunk.content}"
            entities = self.named_entity_recognition(passage) or []
            named_entities = [
                {"name": item.get("name"), "category": item.get("category")}
                for item in entities
                if item.get("name") and item.get("category")
            ]
            standardized_entities = self.named_entity_standardization(
                passage, named_entities
            ) or []
            self.append_official_name(entities, standardized_entities)
            relations = self.relations_extraction(passage, named_entities) or []
            events = self.event_extraction(passage) or []
            return KagExtractionPayload(
                entities=entities,
                standardized_entities=standardized_entities,
                relations=relations,
                events=events,
            )
        except Exception as exc:
            self._kag_initialized = False
            self._kag_init_error = str(exc)
            disable_kag_backend(f"schema constraint runtime failure: {exc}")
            return None


@register_operator
class EntityExtractOperator(KagSchemaConstraintOperatorBase):
    SPEC = OperatorSpec(
        name="entity_extract",
        stage="extract",
        layer="extract",
        knowledge_category="knowledge_extraction",
        operator_class="general",
        description="从 chunk 中抽取实体候选。",
        input_type="ChunkDTO",
        output_type="EntitySeedListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.extract.EntityExtractOperator",
        applicable_sources=["news", "report", "document"],
        tags=["extract", "entity", "seed"],
        decoupling_reason="实体抽取是基础能力，可独立复用到问答、图谱和指标标注任务。",
    )

    def run(self, input_data: ChunkDTO) -> EntitySeedListDTO:
        payload = self._extract_payload(input_data)
        if payload is not None:
            entities = []
            for item in payload.entities:
                entity = _entity_seed_from_kag_record(item)
                if entity is not None:
                    entities.append(entity)
            if entities:
                return EntitySeedListDTO(entities=entities)
        entities = [
            EntitySeedDTO(
                entity_type=_classify_entity(name),
                name=name,
                aliases=[],
                properties={"source_chunk_id": input_data.chunk_id},
            )
            for name in _extract_names(input_data.text)
        ]
        return EntitySeedListDTO(entities=entities)


@register_operator
class EntityStandardizeOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="entity_standardize",
        stage="extract",
        layer="extract",
        knowledge_category="knowledge_extraction",
        operator_class="general",
        description="对实体候选做标准名归一、别名补充和官方名补齐。",
        input_type="EntitySeedListDTO",
        output_type="EntitySeedListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.extract.EntityStandardizeOperator",
        applicable_sources=["news", "report", "document"],
        tags=["extract", "entity", "standardize"],
        decoupling_reason="标准化是实体抽取后的通用步骤，和关系/事件抽取可独立演进。",
    )

    def run(self, input_data: EntitySeedListDTO) -> EntitySeedListDTO:
        normalized: list[EntitySeedDTO] = []
        seen = set()
        for entity in input_data.entities:
            name = _normalize_name(entity.name)
            if not name or name in seen:
                continue
            seen.add(name)
            aliases = _dedupe_preserve_order([_normalize_name(alias) for alias in entity.aliases if alias])
            normalized.append(
                EntitySeedDTO(
                    entity_type=entity.entity_type,
                    name=name,
                    aliases=[alias for alias in aliases if alias and alias != name],
                    properties=dict(entity.properties),
                )
            )
        return EntitySeedListDTO(entities=normalized)


@register_operator
class RelationExtractOperator(KagSchemaConstraintOperatorBase):
    SPEC = OperatorSpec(
        name="relation_extract",
        stage="extract",
        layer="extract",
        knowledge_category="knowledge_extraction",
        operator_class="general",
        description="从 chunk 与实体候选中抽取关系候选。",
        input_type="ChunkEntityBundleDTO",
        output_type="RelationSeedListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.extract.RelationExtractOperator",
        applicable_sources=["news", "report", "document"],
        tags=["extract", "relation", "seed"],
        decoupling_reason="关系抽取的输入输出边界清晰，适合独立成可观测算子。",
    )

    def run(self, input_data: ChunkEntityBundleDTO) -> RelationSeedListDTO:
        payload = self._extract_payload(input_data.chunk)
        if payload is not None:
            relations: list[RelationSeedDTO] = []
            for item in payload.relations:
                if not isinstance(item, list) or len(item) != 5:
                    continue
                subject_name, _subject_type, predicate, object_name, _object_type = item
                subject_name = _normalize_name(str(subject_name or ""))
                object_name = _normalize_name(str(object_name or ""))
                predicate = str(predicate or "").strip()
                if not subject_name or not object_name or not predicate:
                    continue
                relations.append(
                    RelationSeedDTO(
                        subject_name=subject_name,
                        predicate=predicate,
                        object_name=object_name,
                        properties={"source_chunk_id": input_data.chunk.chunk_id, "backend": "kag"},
                    )
                )
            if relations:
                return RelationSeedListDTO(relations=relations)
        relations: list[RelationSeedDTO] = []
        text = input_data.chunk.text
        company_name = _leading_company(text, input_data.entities)

        investor_match = re.search(r"投资方为([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:基金|公司|集团))", text)
        if investor_match and company_name:
            investor_name = _normalize_name(investor_match.group(1))
            relations.append(
                RelationSeedDTO(
                    subject_name=investor_name,
                    predicate="investedIn",
                    object_name=company_name,
                    properties={"source_chunk_id": input_data.chunk.chunk_id},
                )
            )

        cooperation_match = re.search(
            r"([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:公司|集团))与([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:大学|学院|研究院|研究所|公司|集团))签署合作协议",
            text,
        )
        if cooperation_match:
            relations.append(
                RelationSeedDTO(
                    subject_name=_normalize_name(cooperation_match.group(1)),
                    predicate="cooperateWith",
                    object_name=_normalize_name(cooperation_match.group(2)),
                    properties={"source_chunk_id": input_data.chunk.chunk_id},
                )
            )

        return RelationSeedListDTO(relations=relations)


@register_operator
class EventExtractOperator(KagSchemaConstraintOperatorBase):
    SPEC = OperatorSpec(
        name="event_extract",
        stage="extract",
        layer="extract",
        knowledge_category="knowledge_extraction",
        operator_class="general",
        description="从 chunk 中抽取事件候选，包括主体、客体、时间和地点。",
        input_type="ChunkDTO",
        output_type="EventSeedListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.extract.EventExtractOperator",
        applicable_sources=["news", "report", "document"],
        tags=["extract", "event", "seed"],
        decoupling_reason="事件抽取本身就是稳定职责边界，适合被资讯和研报两条链共同复用。",
    )

    def run(self, input_data: ChunkDTO) -> EventSeedListDTO:
        payload = self._extract_payload(input_data)
        if payload is not None:
            events = []
            for item in payload.events:
                event = _event_seed_from_kag_record(item)
                if event is not None:
                    if "backend" not in event.properties:
                        event.properties["backend"] = "kag"
                    if "source_chunk_id" not in event.properties:
                        event.properties["source_chunk_id"] = input_data.chunk_id
                    events.append(event)
            if events:
                return EventSeedListDTO(events=events)
        events: list[EventSeedDTO] = []
        text = input_data.text
        company_match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]{2,40}公司)", text)
        investor_match = re.search(r"投资方为([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:基金|公司|集团))", text)
        cooperation_match = re.search(
            r"([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:公司|集团))与([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:大学|学院|研究院|研究所|公司|集团))签署合作协议",
            text,
        )

        if "融资" in text and company_match:
            events.append(
                EventSeedDTO(
                    event_type="CompanyFinancingEvent",
                    name=f"{_normalize_name(company_match.group(1))}融资事件",
                    subject_name=_normalize_name(company_match.group(1)),
                    object_name=_normalize_name(investor_match.group(1)) if investor_match else None,
                    properties={"source_chunk_id": input_data.chunk_id},
                )
            )

        if cooperation_match:
            events.append(
                EventSeedDTO(
                    event_type="CompanyCooperationEvent",
                    name=f"{_normalize_name(cooperation_match.group(1))}合作事件",
                    subject_name=_normalize_name(cooperation_match.group(1)),
                    object_name=_normalize_name(cooperation_match.group(2)),
                    properties={"source_chunk_id": input_data.chunk_id},
                )
            )

        return EventSeedListDTO(events=events)


@register_operator
class ConceptSeedExtractOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="concept_seed_extract",
        stage="extract",
        layer="extract",
        knowledge_category="knowledge_extraction",
        operator_class="business",
        description="从文本中抽取行业、技术、企业分类等概念候选。",
        input_type="ChunkDTO",
        output_type="ConceptSeedListDTO",
        implementation_ref="app.knowledge_extraction_operators.operators.extract.ConceptSeedExtractOperator",
        applicable_sources=["news", "report", "document"],
        tags=["extract", "concept", "seed"],
        decoupling_reason="概念候选抽取和最终概念绑定是两件事，前者适合独立成中间算子。",
    )

    def run(self, input_data: ChunkDTO) -> ConceptSeedListDTO:
        concepts = []
        text = input_data.text
        if "机器人" in text:
            concepts.append({"concept_type": "IndustrySector", "name": "机器人"})
        if "融资" in text:
            concepts.append({"concept_type": "EventCategory", "name": "企业融资"})
        return ConceptSeedListDTO(concepts=concepts)
