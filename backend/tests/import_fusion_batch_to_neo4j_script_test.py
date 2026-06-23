import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "fusion" / "import_fusion_batch_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("import_fusion_batch_to_neo4j", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_import_payload_adds_stub_nodes_for_edge_endpoints(tmp_path):
    module = load_script_module()
    batch_path = tmp_path / "fusion_batch.json"
    batch_path.write_text(
        json.dumps(
            {
                "batch_id": "fusion_batch",
                "entity_nodes": [
                    {
                        "type_name": "NewsEntityProfile",
                        "graph_id": "NewsEntityProfile:v2:profile-1",
                        "name": "腾讯",
                        "properties": {
                            "canonicalGraphId": "Enterprise:wiki:Q860580",
                            "sourceProfiles": {"v2": {"summary": "资讯摘要"}},
                        },
                    }
                ],
                "concept_nodes": [],
                "event_nodes": [],
                "document_nodes": [],
                "chunk_nodes": [],
                "edges": [
                    {
                        "subject_graph_id": "NewsEntityProfile:v2:profile-1",
                        "predicate": "refersTo",
                        "object_graph_id": "Enterprise:wiki:Q860580",
                        "properties": {"targetLayer": "identity_link"},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = module.build_import_payload(module.load_batch(batch_path))

    assert len(payload.nodes) == 2
    assert any(node.graph_id == "NewsEntityProfile:v2:profile-1" and "NewsEntityProfile" in node.labels for node in payload.nodes)
    assert any(node.graph_id == "Enterprise:wiki:Q860580" and node.is_stub for node in payload.nodes)
    assert payload.nodes[0].properties["sourceProfiles"] == '{"v2": {"summary": "资讯摘要"}}'
    assert payload.edges[0].rel_type == "refersTo"


def test_import_fusion_batch_to_neo4j_supports_dry_run(tmp_path):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "fusion" / "import_fusion_batch_to_neo4j.py"
    batch_path = tmp_path / "fusion_batch.json"
    batch_path.write_text(
        json.dumps(
            {
                "batch_id": "fusion_batch",
                "entity_nodes": [
                    {
                        "type_name": "NewsEntityProfile",
                        "graph_id": "NewsEntityProfile:v2:profile-1",
                        "name": "腾讯",
                        "properties": {"canonicalGraphId": "Enterprise:wiki:Q860580"},
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
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )

    assert result.returncode == 0, result.stderr
    assert "nodes=1" in result.stdout
    assert "edges=0" in result.stdout
