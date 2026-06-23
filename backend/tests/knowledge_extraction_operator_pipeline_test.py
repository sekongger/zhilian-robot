from app.incore_fusion_pipeline.dto.source_dto import SourceRecordDTO
from app.knowledge_extraction_operators import get_operator
from app.knowledge_extraction_operators.dto import (
    EntityResolutionInputDTO,
    EventBatchDTO,
    EventResolutionInputDTO,
    GraphBuildInputDTO,
    GraphImportInputDTO,
    SourceRecordListDTO,
)


def test_operator_pipeline_runs_from_source_records_to_dry_run_import():
    records = SourceRecordListDTO(
        records=[
            SourceRecordDTO(
                source_system="fact_library",
                source_table="company",
                record_id="company_001",
                record_type="entity",
                payload={
                    "entity_type": "Company",
                    "name": "上海某某机器人科技有限公司",
                    "credit_code": "91310000X",
                    "province": "上海",
                    "city": "上海",
                    "status": "存续",
                    "description": "一家从事工业机器人控制系统和自动化装备研发的科技企业",
                    "business_scope": "工业机器人控制器、自动化产线、伺服系统研发与制造",
                },
            ),
            SourceRecordDTO(
                source_system="report_pipeline",
                source_table="document",
                record_id="doc_001",
                record_type="document",
                payload={
                    "doc_type": "research_report",
                    "title": "机器人行业专题",
                    "content": "上海某某机器人科技有限公司完成B轮融资。",
                    "source_name": "某研究院",
                    "source_type": "report",
                },
            ),
            SourceRecordDTO(
                source_system="report_pipeline",
                source_table="chunk",
                record_id="chunk_001",
                record_type="chunk",
                payload={
                    "doc_id": "doc_001",
                    "chunk_index": 0,
                    "content": "上海某某机器人科技有限公司完成B轮融资，投资方为某产业基金。",
                },
            ),
            SourceRecordDTO(
                source_system="report_extract",
                source_table="event",
                record_id="event_001",
                record_type="event",
                payload={
                    "event_type": "CompanyFinancingEvent",
                    "name": "上海某某机器人科技有限公司完成B轮融资",
                    "summary": "公司完成B轮融资，投资方为某产业基金",
                    "subject_name": "上海某某机器人科技有限公司",
                    "object_name": "某产业基金",
                    "location": "上海",
                    "source_doc_id": "doc_001",
                    "source_chunk_ids": ["chunk_001"],
                    "trigger_terms": ["融资", "B轮"],
                    "properties": {
                        "publishTime": "2026-04-01T09:00:00",
                        "financingRound": "B轮",
                        "financingAmount": 500000000,
                    },
                },
            ),
        ]
    )

    normalized = get_operator("source_record_map").run(records)
    enriched_events = get_operator("event_enrich").run(EventBatchDTO(events=normalized.events))
    entity_resolution = get_operator("entity_resolve").run(
        EntityResolutionInputDTO(
            entities=normalized.entities,
            events=enriched_events.events,
        )
    )
    event_resolution = get_operator("event_resolve").run(
        EventResolutionInputDTO(
            events=enriched_events.events,
            entity_resolution=entity_resolution,
        )
    )
    graph_build = get_operator("fusion_graph_build").run(
        GraphBuildInputDTO(
            normalized_batch=normalized,
            entity_resolution=entity_resolution,
            event_resolution=event_resolution,
            project="IncCore",
            namespace="IncCore",
            batch_id="operator_test_batch",
        )
    )
    graph_import = get_operator("graph_import").run(
        GraphImportInputDTO(
            batch=graph_build.batch,
            dry_run=True,
        )
    )

    assert normalized.entities
    assert enriched_events.events[0].category_ref is not None
    assert entity_resolution.entities
    assert any(binding.concept_type == "CompanyCategory" for binding in entity_resolution.entities[0].concept_bindings)
    assert event_resolution.events[0].subject_graph_id is not None
    assert graph_build.batch.node_count() > 0
    assert graph_build.batch.edge_count() > 0
    assert graph_import.status == "dry_run"
    assert graph_import.node_count == graph_build.batch.node_count()
