import json
from pathlib import Path

from app.wiki_industry_pipeline.cli import run_build, run_fetch_build, run_stream_import
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records


FIXTURE = Path("backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl")
SCHEMA = Path("configs/industry_wiki/IncIndustryWiki.routing.schema.yaml")


def test_wiki_industry_cli_builds_graph_batch_and_report(tmp_path):
    output = tmp_path / "graph_batch.json"
    report = tmp_path / "coverage_report.json"

    result = run_build(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        domain="robotics",
        limit=10,
        output_path=output,
        report_path=report,
        dry_run=True,
    )

    graph_payload = json.loads(output.read_text(encoding="utf-8"))
    report_payload = json.loads(report.read_text(encoding="utf-8"))

    assert result.node_count() >= 3
    assert result.edge_count() >= 2
    assert graph_payload["batch_id"] == "wiki_industry_robotics"
    assert {node["type_name"] for node in graph_payload["entity_nodes"]} >= {"Enterprise", "ProductModel", "Region"}
    assert report_payload["candidate_count"] >= 3
    assert "top_unclaimed_properties" in report_payload


def test_wiki_industry_cli_can_import_graph_batch_with_injected_importer(tmp_path):
    output = tmp_path / "graph_batch.json"
    report = tmp_path / "coverage_report.json"
    import_result = tmp_path / "import_result.json"
    importer = _RecordingImporter()

    result = run_build(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        domain="robotics",
        limit=10,
        output_path=output,
        report_path=report,
        dry_run=False,
        import_to_openspg=True,
        project_id=3,
        import_result_path=import_result,
        importer=importer,
    )

    import_payload = json.loads(import_result.read_text(encoding="utf-8"))

    assert result.batch_id == "wiki_industry_robotics"
    assert importer.called is True
    assert importer.dry_run is False
    assert importer.batch.metadata["project_id"] == 3
    assert import_payload["status"] == "live"


def test_wiki_industry_cli_imports_with_kag_writer_when_importer_not_injected(tmp_path):
    output = tmp_path / "graph_batch.json"
    report = tmp_path / "coverage_report.json"
    import_result = tmp_path / "import_result.json"
    writer = _RecordingKagWriter()

    result = run_build(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        domain="robotics",
        limit=10,
        output_path=output,
        report_path=report,
        dry_run=False,
        import_to_openspg=True,
        project_id=3,
        import_result_path=import_result,
        kag_writer=writer,
    )

    import_payload = json.loads(import_result.read_text(encoding="utf-8"))

    assert result.batch_id == "wiki_industry_robotics"
    assert len(writer.graphs) >= 3
    assert import_payload["status"] == "live"
    assert import_payload["details"]["writer"] == "kag.builder.component.writer.kg_writer.KGWriter"


def test_wiki_industry_cli_fetch_build_does_not_require_local_dump_input(tmp_path):
    fetched_output = tmp_path / "fetched.jsonl"
    graph_output = tmp_path / "graph_batch.json"
    report = tmp_path / "coverage_report.json"

    result = run_fetch_build(
        seed_terms_path=Path("configs/industry_wiki/robotics_seed_terms.yaml"),
        routing_schema_path=SCHEMA,
        fetched_output_path=fetched_output,
        output_path=graph_output,
        report_path=report,
        domain="robotics",
        fetcher=_FixtureFetcher(),
        search_limit_per_term=1,
        max_entities=10,
        expand_depth=0,
        sparql_limit=0,
        dry_run=True,
    )

    graph_payload = json.loads(graph_output.read_text(encoding="utf-8"))

    assert fetched_output.exists()
    assert result.node_count() >= 3
    assert graph_payload["batch_id"] == "wiki_industry_robotics"


def test_wiki_industry_cli_stream_import_uses_candidate_limit_without_graph_batch(tmp_path):
    import_result = tmp_path / "stream_import_result.json"
    writer = _RecordingKagWriter()

    result = run_stream_import(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        domain="all_industry",
        project_id=3,
        import_result_path=import_result,
        candidate_limit=2,
        kag_writer=writer,
    )

    import_payload = json.loads(import_result.read_text(encoding="utf-8"))

    assert result.status == "live"
    assert len(writer.graphs) == 2
    assert import_payload["details"]["graph_count"] == 2
    assert import_payload["details"]["candidate_limit"] == 2
    assert import_payload["details"]["stopped_by"] == "candidate_limit"


class _RecordingImporter:
    def __init__(self):
        self.called = False
        self.dry_run = None
        self.batch = None

    def import_batch(self, batch, *, dry_run):
        from app.incore_fusion_pipeline.dto.graph_import_dto import GraphImportResultDTO

        self.called = True
        self.dry_run = dry_run
        self.batch = batch
        return GraphImportResultDTO(
            batch_id=batch.batch_id,
            status="live" if not dry_run else "dry_run",
            dry_run=dry_run,
            node_count=batch.node_count(),
            edge_count=batch.edge_count(),
        )


class _FixtureFetcher:
    def fetch_records_from_seed_config(self, *args, **kwargs):
        return list(iter_wikidata_records(FIXTURE))


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
