import json
from pathlib import Path

from app.wiki_industry_pipeline.sharded_export import export_wikidata_graph_shards


FIXTURE = Path("backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl")
SCHEMA = Path("configs/industry_wiki/IncIndustryWiki.routing.schema.yaml")


def test_export_wikidata_graph_shards_writes_candidate_sized_batches(tmp_path):
    result = export_wikidata_graph_shards(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        output_dir=tmp_path,
        domain="robotics",
        shard_candidate_size=2,
    )

    graph_files = sorted(tmp_path.glob("graph_batch_*.json"))
    report_files = sorted(tmp_path.glob("coverage_report_*.json"))
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert result.shard_count == 2
    assert len(graph_files) == 2
    assert len(report_files) == 2
    assert manifest["shard_count"] == 2
    assert manifest["total_candidate_count"] == 3
    assert json.loads(graph_files[0].read_text(encoding="utf-8"))["batch_id"] == "wiki_industry_robotics_shard_000001"


def test_export_wikidata_graph_shards_can_resume_from_existing_manifest(tmp_path):
    export_wikidata_graph_shards(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        output_dir=tmp_path,
        domain="robotics",
        shard_candidate_size=2,
        candidate_limit=2,
    )

    result = export_wikidata_graph_shards(
        dump_path=FIXTURE,
        routing_schema_path=SCHEMA,
        output_dir=tmp_path,
        domain="robotics",
        shard_candidate_size=2,
        resume=True,
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert result.shard_count == 2
    assert manifest["status"] == "completed"
    assert manifest["total_candidate_count"] == 3
    assert Path(tmp_path / "graph_batch_000002.json").exists()


def test_export_wikidata_graph_shards_resume_uses_manifest_cursor_when_present(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "status": "interrupted",
                "domain": "all_industry",
                "dump_path": "https://example.test/latest-all.json.bz2",
                "routing_schema_path": str(SCHEMA),
                "type_whitelist_path": None,
                "shard_count": 0,
                "raw_record_count": 12345,
                "total_candidate_count": 0,
                "total_node_count": 0,
                "total_edge_count": 0,
                "resume_cursor": 98765,
                "shards": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    observed = {}

    def fake_iter_wikidata_records(path, *, source="wikidata", limit=None, skip_records=0, resume_cursor=None, **kwargs):
        observed["path"] = path
        observed["skip_records"] = skip_records
        observed["resume_cursor"] = resume_cursor
        return iter([])

    monkeypatch.setattr(
        "app.wiki_industry_pipeline.sharded_export.iter_wikidata_records",
        fake_iter_wikidata_records,
    )

    result = export_wikidata_graph_shards(
        dump_path="https://example.test/latest-all.json.bz2",
        routing_schema_path=SCHEMA,
        output_dir=tmp_path,
        domain="all_industry",
        resume=True,
    )

    assert result.shard_count == 0
    assert observed["path"] == "https://example.test/latest-all.json.bz2"
    assert observed["skip_records"] == 0
    assert observed["resume_cursor"] == 98765
