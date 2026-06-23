import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def test_build_demo_batch_lines_contains_stable_ids_and_demo_company():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "materialize_openspg_demo_graph.py"
    spec = importlib.util.spec_from_file_location("materialize_openspg_demo_graph", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    lines = module.build_demo_batch_lines()

    assert lines
    joined = "\n".join(lines)
    assert "智链机器人" in joined
    assert "DEMO_DOC_ZLR_PARTNER" in joined
    assert "DEMO_DOC_ZLR_PRODUCT" in joined


def test_materialize_demo_graph_script_supports_cli_write_only(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "materialize_openspg_demo_graph.py"
    output = tmp_path / "demo.jsonl"

    result = subprocess.run(
        [sys.executable, str(script_path), "--write-only", "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert "DEMO_DOC_ZLR_PARTNER" in output.read_text(encoding="utf-8")


def test_build_demo_fact_payloads_contains_statement_and_evidence_docs():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "materialize_openspg_demo_graph.py"
    spec = importlib.util.spec_from_file_location("materialize_openspg_demo_graph", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_demo_fact_payloads()

    assert payload["source_news"]
    assert payload["entity_docs"]
    assert payload["statement_docs"]
    assert payload["evidence_docs"]
    assert any(item["canonical_name"] == "智链机器人" for item in payload["entity_docs"])
    assert any(item["predicate_label"] == "研发技术" for item in payload["statement_docs"])
    assert any(item["statement_id"] for item in payload["evidence_docs"])
