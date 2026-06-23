import json
from pathlib import Path

from app.incore_fusion_pipeline.dto.graph_import_dto import (
    GraphEdgeUpsertDTO,
    GraphImportBatchDTO,
    GraphNodeUpsertDTO,
)
from app.knowledge_extraction_operators.kag_bridge import (
    ensure_kag_task_config,
    unwrap_kag_outputs,
)
from app.wiki_industry_pipeline.kag_adapter import (
    IncCoreWikidataClaimMapping,
    WikidataJSONLScanner,
    import_graph_batch_with_kag_writer,
    import_wikidata_dump_with_kag_components,
)


FIXTURE = Path("backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl")
SCHEMA = Path("configs/industry_wiki/IncIndustryWiki.routing.schema.yaml")


def _task_id() -> str:
    return ensure_kag_task_config(project_id=3, namespace="IncCore")


def test_wikidata_jsonl_scanner_reads_wikidata_records_for_kag_chain():
    scanner = WikidataJSONLScanner(limit=2, kag_qa_task_config_key=_task_id())

    records = scanner.invoke(str(FIXTURE))

    assert len(records) == 2
    assert records[0]["entity_id"] == "Q1001"
    assert records[0]["raw"]["labels"]["en"]["value"] == "Acme Robotics"


def test_incore_wikidata_claim_mapping_outputs_kag_subgraph_with_routed_edges():
    raw_record = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    mapping = IncCoreWikidataClaimMapping(
        routing_schema_path=SCHEMA,
        domain="robotics",
        kag_qa_task_config_key=_task_id(),
    )

    [graph] = unwrap_kag_outputs(mapping.invoke(raw_record, write_ckpt=False))

    nodes = {(node.label, node.id): node for node in graph.nodes}
    edges = {(edge.from_type, edge.from_id, edge.label, edge.to_type, edge.to_id) for edge in graph.edges}

    assert ("Enterprise", "Enterprise:wiki:Q1001") in nodes
    assert nodes[("Enterprise", "Enterprise:wiki:Q1001")].properties["inception"] == "2010-01-01"
    assert (
        "ProductModel",
        "ProductModel:wiki:Q2001",
        "manufacturer",
        "Enterprise",
        "Enterprise:wiki:Q1001",
    ) in edges
    assert (
        "Enterprise",
        "Enterprise:wiki:Q1001",
        "belongsToIndustry",
        "Industry",
        "Industry:wiki:Q170978",
    ) in edges


def test_import_graph_batch_with_kag_writer_converts_batch_to_subgraph_and_strips_internal_props():
    batch = GraphImportBatchDTO(
        project="IncCore",
        namespace="IncCore",
        batch_id="wiki-test",
        entity_nodes=[
            GraphNodeUpsertDTO(
                type_name="Enterprise",
                graph_id="Enterprise:wiki:Q1001",
                name="Acme Robotics",
                properties={"name": "Acme Robotics", "_source": "wikidata"},
            ),
            GraphNodeUpsertDTO(
                type_name="Industry",
                graph_id="Industry:wiki:Q170978",
                name="Robotics",
                properties={"name": "Robotics", "_semanticType": "stub"},
            ),
        ],
        edges=[
            GraphEdgeUpsertDTO(
                subject_graph_id="Enterprise:wiki:Q1001",
                predicate="belongsToIndustry",
                object_graph_id="Industry:wiki:Q170978",
                properties={"_propertyId": "P452", "confidence": 1.0},
            )
        ],
        metadata={"project_id": 3},
    )
    writer = _RecordingKagWriter()

    result = import_graph_batch_with_kag_writer(batch, writer=writer)

    assert result.status == "live"
    assert result.dry_run is False
    assert result.details["writer"] == "kag.builder.component.writer.kg_writer.KGWriter"
    assert writer.kwargs["write_ckpt"] is False
    assert len(writer.graph.nodes) == 2
    assert len(writer.graph.edges) == 1
    assert "_source" not in writer.graph.nodes[0].properties
    assert "_propertyId" not in writer.graph.edges[0].properties
    assert writer.graph.edges[0].properties["confidence"] == 1.0


def test_import_wikidata_dump_with_kag_components_stops_at_candidate_limit():
    writer = _RecordingKagWriter()

    result = import_wikidata_dump_with_kag_components(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        domain="all_industry",
        project_id=3,
        writer=writer,
        candidate_limit=2,
    )

    assert result.status == "live"
    assert len(writer.graphs) == 2
    assert result.details["graph_count"] == 2
    assert result.details["candidate_limit"] == 2
    assert result.details["stopped_by"] == "candidate_limit"


class _RecordingKagWriter:
    def __init__(self):
        self.graph = None
        self.graphs = []
        self.kwargs = None

    def invoke(self, graph, **kwargs):
        self.graph = graph
        self.graphs.append(graph)
        self.kwargs = kwargs
        return [graph]
