"""Operator wrappers over the current IncCore fusion stages."""

from __future__ import annotations

from typing import List

from app.incore_fusion_pipeline.builders.concept_batch_builder import ConceptBatchBuilder
from app.incore_fusion_pipeline.builders.entity_batch_builder import EntityBatchBuilder
from app.incore_fusion_pipeline.builders.event_batch_builder import EventBatchBuilder
from app.incore_fusion_pipeline.builders.evidence_batch_builder import EvidenceBatchBuilder
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphImportBatchDTO
from app.incore_fusion_pipeline.importers.openspg_importer import OpenSPGImporter
from app.incore_fusion_pipeline.mappers.event_mapper import EventMapper
from app.incore_fusion_pipeline.mappers.source_mapper import SourceMapper
from app.incore_fusion_pipeline.resolvers.entity_resolver import EntityResolver
from app.incore_fusion_pipeline.resolvers.event_resolver import EventResolver
from app.knowledge_extraction_operators.base import KnowledgeOperatorABC, OperatorSpec
from app.knowledge_extraction_operators.dto import (
    EntityResolutionInputDTO,
    EntityResolutionResultDTO,
    EventBatchDTO,
    EventResolutionInputDTO,
    EventResolutionResultDTO,
    GraphBuildInputDTO,
    GraphBuildResultDTO,
    GraphImportInputDTO,
    GraphImportOutputDTO,
    NormalizedBatchDTO,
    SourceRecordListDTO,
)
from app.knowledge_extraction_operators.kag_bridge import (
    ensure_kag_import_path,
    ensure_kag_task_config,
    graph_batch_to_kag_subgraph,
)
from app.knowledge_extraction_operators.registry import register_operator

ensure_kag_import_path()

from kag.builder.component.writer.kg_writer import KGWriter  # noqa: E402


@register_operator
class SourceRecordMapOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="source_record_map",
        stage="normalize",
        layer="fusion",
        knowledge_category="data_preprocessing_structuring",
        operator_class="general",
        description="Map source envelopes into normalized entity, relation, document, chunk, event, and concept batches.",
        input_type="SourceRecordListDTO",
        output_type="NormalizedBatchDTO",
        implementation_ref="app.incore_fusion_pipeline.mappers.source_mapper.SourceMapper",
        applicable_sources=["fact_table", "news", "report", "document"],
        tags=["normalize", "mapping", "source-record"],
        decoupling_reason="源记录映射统一了不同来源进入融合层的格式，是后续归一和落图的稳定边界。",
    )

    def __init__(self, mapper: SourceMapper | None = None):
        self.mapper = mapper or SourceMapper()

    def run(self, input_data: SourceRecordListDTO) -> NormalizedBatchDTO:
        entities, relations, documents, chunks, events, concept_seeds = self.mapper.map_records(input_data.records)
        return NormalizedBatchDTO(
            entities=entities,
            relations=relations,
            documents=documents,
            chunks=chunks,
            events=events,
            concept_seeds=concept_seeds,
        )


@register_operator
class EventEnrichOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="event_enrich",
        stage="normalize",
        layer="fusion",
        knowledge_category="knowledge_alignment_standardization",
        operator_class="business",
        description="Apply default event category, actor typing, and summary enrichment to normalized events.",
        input_type="EventBatchDTO",
        output_type="EventBatchDTO",
        implementation_ref="app.incore_fusion_pipeline.mappers.event_mapper.EventMapper",
        applicable_sources=["news", "report", "document"],
        tags=["event", "normalize", "enrich"],
        decoupling_reason="事件补全只依赖归一前的事件结构，可独立复用到资讯链和研报链。",
    )

    def __init__(self, mapper: EventMapper | None = None):
        self.mapper = mapper or EventMapper()

    def run(self, input_data: EventBatchDTO) -> EventBatchDTO:
        return EventBatchDTO(events=[self.mapper.enrich(event) for event in input_data.events])


@register_operator
class EntityResolveOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="entity_resolve",
        stage="resolve",
        layer="fusion",
        knowledge_category="knowledge_alignment_standardization",
        operator_class="business",
        description="Resolve normalized entities into canonical entities, generate synthetic event actors, and build entity lookup keys.",
        input_type="EntityResolutionInputDTO",
        output_type="EntityResolutionResultDTO",
        implementation_ref="app.incore_fusion_pipeline.resolvers.entity_resolver.EntityResolver",
        applicable_sources=["fact_table", "news", "report", "document"],
        tags=["entity", "resolve", "canonical"],
        decoupling_reason="实体归一面向全局主实体，不应和单篇文档抽取逻辑耦合。",
    )

    def __init__(self, resolver: EntityResolver | None = None):
        self.resolver = resolver or EntityResolver()

    def run(self, input_data: EntityResolutionInputDTO) -> EntityResolutionResultDTO:
        synthetic_entities = self.resolver.build_synthetic_entities_from_event_refs(input_data.events)
        event_region_names = [
            event.location_ref.match_key
            for event in input_data.events
            if event.location_ref is not None and event.location_ref.match_key
        ]
        canonical_entities, conflicts = self.resolver.resolve_entities(
            [*input_data.entities, *synthetic_entities],
            extra_region_names=[*input_data.extra_region_names, *event_region_names],
        )
        entity_lookup = self.resolver.build_lookup(canonical_entities)
        return EntityResolutionResultDTO(
            entities=canonical_entities,
            conflicts=conflicts,
            entity_lookup=entity_lookup,
        )


@register_operator
class EventResolveOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="event_resolve",
        stage="resolve",
        layer="fusion",
        knowledge_category="knowledge_alignment_standardization",
        operator_class="business",
        description="Resolve normalized events against canonical entities and emit canonical event records with concept bindings.",
        input_type="EventResolutionInputDTO",
        output_type="EventResolutionResultDTO",
        implementation_ref="app.incore_fusion_pipeline.resolvers.event_resolver.EventResolver",
        applicable_sources=["news", "report", "document"],
        tags=["event", "resolve", "canonical"],
        decoupling_reason="事件归一依赖全局实体结果，但与图谱写入和概念落图是独立步骤。",
    )

    def __init__(self, resolver: EventResolver | None = None):
        self.resolver = resolver or EventResolver()

    def run(self, input_data: EventResolutionInputDTO) -> EventResolutionResultDTO:
        canonical_events = self.resolver.resolve_events(
            input_data.events,
            entity_lookup=input_data.entity_resolution.entity_lookup,
            entities=input_data.entity_resolution.entities,
        )
        return EventResolutionResultDTO(events=canonical_events)


@register_operator
class FusionGraphBuildOperator(KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="fusion_graph_build",
        stage="build",
        layer="fusion",
        knowledge_category="knowledge_fusion_graph_build",
        operator_class="business",
        description="Build concept, entity, event, document, and chunk upsert batches for OpenSPG import.",
        input_type="GraphBuildInputDTO",
        output_type="GraphBuildResultDTO",
        implementation_ref="app.incore_fusion_pipeline.builders.*",
        applicable_sources=["fact_table", "news", "report", "document"],
        tags=["graph", "build", "openspg"],
        decoupling_reason="建图批次构造只消费标准化对象和归一结果，是典型的可复用图构建算子。",
    )

    def __init__(
        self,
        *,
        concept_builder: ConceptBatchBuilder | None = None,
        entity_builder: EntityBatchBuilder | None = None,
        event_builder: EventBatchBuilder | None = None,
        evidence_builder: EvidenceBatchBuilder | None = None,
    ):
        self.concept_builder = concept_builder or ConceptBatchBuilder()
        self.entity_builder = entity_builder or EntityBatchBuilder()
        self.event_builder = event_builder or EventBatchBuilder()
        self.evidence_builder = evidence_builder or EvidenceBatchBuilder()

    def run(self, input_data: GraphBuildInputDTO) -> GraphBuildResultDTO:
        concept_nodes, concept_edges = self.concept_builder.build(
            input_data.normalized_batch.concept_seeds,
            input_data.entity_resolution.entities,
            input_data.event_resolution.events,
        )
        entity_nodes, entity_edges = self.entity_builder.build(
            input_data.entity_resolution.entities,
            input_data.normalized_batch.relations,
            input_data.entity_resolution.entity_lookup,
        )
        event_nodes, event_edges = self.event_builder.build(input_data.event_resolution.events)
        document_nodes, chunk_nodes, evidence_edges = self.evidence_builder.build(
            input_data.normalized_batch.documents,
            input_data.normalized_batch.chunks,
            input_data.event_resolution.events,
        )
        edges = self._merge_edges(concept_edges, entity_edges, event_edges, evidence_edges)
        batch = GraphImportBatchDTO(
            project=input_data.project,
            namespace=input_data.namespace,
            batch_id=input_data.batch_id,
            concept_nodes=concept_nodes,
            entity_nodes=entity_nodes,
            event_nodes=event_nodes,
            document_nodes=document_nodes,
            chunk_nodes=chunk_nodes,
            edges=edges,
            metadata={
                "project_id": input_data.project_id,
                "entity_count": len(input_data.entity_resolution.entities),
                "event_count": len(input_data.event_resolution.events),
                "document_count": len(input_data.normalized_batch.documents),
                "chunk_count": len(input_data.normalized_batch.chunks),
                "conflict_count": len(input_data.entity_resolution.conflicts),
            },
        )
        return GraphBuildResultDTO(
            batch=batch,
            concept_nodes=concept_nodes,
            entity_nodes=entity_nodes,
            event_nodes=event_nodes,
            document_nodes=document_nodes,
            chunk_nodes=chunk_nodes,
            edges=edges,
        )

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


@register_operator
class GraphImportOperator(KGWriter, KnowledgeOperatorABC):
    SPEC = OperatorSpec(
        name="graph_import",
        stage="import",
        layer="fusion",
        knowledge_category="knowledge_fusion_graph_build",
        operator_class="general",
        description="Import a graph batch into OpenSPG or execute a dry-run import with node and edge counts.",
        input_type="GraphImportInputDTO",
        output_type="GraphImportOutputDTO",
        implementation_ref="app.incore_fusion_pipeline.importers.openspg_importer.OpenSPGImporter",
        applicable_sources=["fact_table", "news", "report", "document"],
        tags=["graph", "import", "openspg"],
        side_effect=True,
        decoupling_reason="图导入是最终 sink，有明确副作用，必须与纯变换算子分离。",
    )

    def __init__(self, importer: OpenSPGImporter | None = None):
        self.importer = importer or OpenSPGImporter()
        self._kag_writer_ready = False
        self._kag_writer_error: str | None = None
        try:
            task_id = ensure_kag_task_config(project_id=self.importer.project_id)
            KGWriter.__init__(
                self,
                project_id=self.importer.project_id,
                kag_qa_task_config_key=task_id,
            )
            self._kag_writer_ready = True
        except Exception as exc:
            self._kag_writer_error = str(exc)

    def run(self, input_data: GraphImportInputDTO) -> GraphImportOutputDTO:
        if not input_data.dry_run and self._kag_writer_ready:
            sub_graph = graph_batch_to_kag_subgraph(input_data.batch)
            KGWriter.invoke(self, sub_graph, write_ckpt=False)
            result = self.importer.import_batch(input_data.batch, dry_run=True)
            result.status = "live"
            result.dry_run = False
            result.details["writer"] = "kag.builder.component.writer.kg_writer.KGWriter"
            return GraphImportOutputDTO(result=result)
        result = self.importer.import_batch(input_data.batch, dry_run=input_data.dry_run)
        return GraphImportOutputDTO(result=result)
