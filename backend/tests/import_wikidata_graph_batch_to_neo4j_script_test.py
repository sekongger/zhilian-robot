import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "wiki_industry" / "import_wikidata_graph_batch_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("import_wikidata_graph_batch_to_neo4j", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_import_payload_keeps_wikidata_core_nodes_and_skips_stubs(tmp_path):
    module = load_script_module()
    batch_path = tmp_path / "graph_batch_000001.json"
    batch_path.write_text(
        json.dumps(
            {
                "batch_id": "wiki_industry_all_industry_shard_000001",
                "entity_nodes": [
                    {
                        "type_name": "Enterprise",
                        "graph_id": "Enterprise:wiki:Q20716",
                        "name": "三星集团",
                        "properties": {
                            "name": "三星集团",
                            "alias": ["三星", "Samsung Group"],
                            "description": "韩国综合性企业集团",
                            "_source": "wikidata",
                            "_semanticType": "wiki_core",
                        },
                    },
                    {
                        "type_name": "Enterprise",
                        "graph_id": "Enterprise:wiki:Q999",
                        "name": "Enterprise:wiki:Q999",
                        "properties": {
                            "name": "Enterprise:wiki:Q999",
                            "_source": "wikidata",
                            "_semanticType": "stub",
                        },
                    },
                ],
                "edges": [
                    {
                        "subject_graph_id": "Enterprise:wiki:Q20716",
                        "predicate": "headquarteredIn",
                        "object_graph_id": "Region:wiki:Q884",
                        "properties": {"_source": "wikidata"},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = module.build_import_payload([module.load_batch(batch_path)], include_edges=True)

    assert [node.graph_id for node in payload.nodes] == ["Enterprise:wiki:Q20716"]
    assert payload.nodes[0].labels == ["CommonSenseNode", "IncCore.Enterprise", "Enterprise"]
    assert payload.nodes[0].properties["sourceSystem"] == "wikidata_graph_batch"
    assert payload.nodes[0].properties["isStub"] is False
    assert payload.nodes[0].properties["alias"] == ["三星", "Samsung Group"]
    assert payload.edges == []


def test_import_wikidata_graph_batch_to_neo4j_supports_dry_run(tmp_path):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "wiki_industry" / "import_wikidata_graph_batch_to_neo4j.py"
    batch_path = tmp_path / "graph_batch_000001.json"
    batch_path.write_text(
        json.dumps(
            {
                "batch_id": "wiki_industry_all_industry_shard_000001",
                "entity_nodes": [
                    {
                        "type_name": "Product",
                        "graph_id": "Product:wiki:Q123",
                        "name": "固态硬盘",
                        "properties": {"alias": ["SSD"], "_source": "wikidata", "_semanticType": "wiki_core"},
                    }
                ],
                "edges": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(script_path), "--batch", str(batch_path), "--dry-run"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "nodes=1" in result.stdout
    assert "edges=0" in result.stdout
