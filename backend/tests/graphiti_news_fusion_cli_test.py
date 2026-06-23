from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_cli_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_graphiti_news_big_graph_fusion.py"
    spec = importlib.util.spec_from_file_location("run_graphiti_news_big_graph_fusion", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_graphiti_crawler_returns_run_summary_and_sets_graphiti_api_base(monkeypatch, tmp_path):
    module = _load_cli_module()
    captured: dict = {}

    def fake_run(command, *, cwd, check, capture_output, text, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["env"] = env
        return SimpleNamespace(
            stdout='crawler log line\n{"run_id":"crawl_202605240001","ingest":{"ingested":1,"failed":0,"total":1}}\n',
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    args = SimpleNamespace(
        graphiti_project_dir=str(tmp_path),
        crawler_command="python",
        since_hours=24,
        source="rss_36kr_newsflash",
        max_items_per_source=1,
        process_limit=1,
        ingest=True,
        graphiti_api_base="http://127.0.0.1:18001/api",
    )

    summary = module._run_graphiti_crawler(args)

    assert summary["run_id"] == "crawl_202605240001"
    assert captured["env"]["CRAWLER_GRAPHITI_API_BASE"] == "http://127.0.0.1:18001/api"
    assert captured["capture_output"] is True
    assert "--ingest" in captured["command"]


def test_run_graphiti_crawler_rejects_all_failed_ingest(monkeypatch, tmp_path):
    module = _load_cli_module()

    def fake_run(command, *, cwd, check, capture_output, text, env):
        return SimpleNamespace(
            stdout='{"run_id":"crawl_failed","ingest":{"ingested":0,"failed":2,"total":2}}\n',
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    args = SimpleNamespace(
        graphiti_project_dir=str(tmp_path),
        crawler_command="python",
        since_hours=24,
        source=None,
        max_items_per_source=1,
        process_limit=2,
        ingest=True,
        graphiti_api_base="http://127.0.0.1:18001/api",
    )

    try:
        module._run_graphiti_crawler(args)
    except RuntimeError as exc:
        assert "Graphiti crawler ingest failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for all failed ingest")
