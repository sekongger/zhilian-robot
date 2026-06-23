from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_cli_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_news_graph_pipeline.py"
    spec = importlib.util.spec_from_file_location("run_news_graph_pipeline", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cli_rejects_link_entities_without_group_id_or_crawler():
    module = _load_cli_module()
    parser = module.build_parser()
    args = parser.parse_args(["--link-entities"])

    try:
        module.run(args)
    except RuntimeError as exc:
        assert "group_id is required" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when link stage has no group_id")


def test_cli_runs_anchor_and_link_pipeline_with_fake_runner(monkeypatch, tmp_path):
    module = _load_cli_module()
    calls = []

    class FakePipelineRunner:
        def run(self, **kwargs):
            calls.append(kwargs)
            return {
                "run_id": "news_graph_1",
                "group_id": kwargs["group_id"],
                "stages": {"anchor_sync": {"synced": 1}, "entity_link": {"refersTo": 1}},
                "warnings": [],
            }

    monkeypatch.setattr(module, "NewsGraphPipelineRunner", lambda: FakePipelineRunner())
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "--group-id",
            "crawl_202606210001",
            "--sync-anchors",
            "--link-entities",
            "--output-dir",
            str(tmp_path),
        ]
    )

    report = module.run(args)

    assert report["group_id"] == "crawl_202606210001"
    assert calls[0]["sync_anchors"] is True
    assert calls[0]["link_entities"] is True
    assert (tmp_path / "run_report.json").exists()


def test_cli_passes_clear_news_group_to_runner(monkeypatch, tmp_path):
    module = _load_cli_module()
    calls = []

    class FakePipelineRunner:
        def run(self, **kwargs):
            calls.append(kwargs)
            return {
                "run_id": "news_graph_1",
                "group_id": kwargs["group_id"],
                "stages": {"clear_news_group": {"cleared_group": 1}},
                "warnings": [],
            }

    monkeypatch.setattr(module, "NewsGraphPipelineRunner", lambda: FakePipelineRunner())
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "--group-id",
            "crawl_202606210001",
            "--clear-news-group",
            "--output-dir",
            str(tmp_path),
        ]
    )

    report = module.run(args)

    assert report["stages"]["clear_news_group"]["cleared_group"] == 1
    assert calls[0]["clear_news_group"] is True
