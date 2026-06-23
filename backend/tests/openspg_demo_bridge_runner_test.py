from datetime import datetime, timezone
from pathlib import Path


def test_bridge_runner_creates_jsonl_batch_and_state(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))

    from app.openspg_demo.bridge_runner import BridgeRunner

    rows = [
        {
            "id": "n1",
            "title": "智链机器人与某伺服科技达成合作",
            "content": "双方签约合作推进机器人产线。",
            "source": "rss_demo",
            "url": "https://example.com/1",
            "published_at": "2026-02-26T10:00:00+00:00",
        },
        {
            "id": "n2",
            "title": "某减速器公司扩产项目投产",
            "content": "新基地投产带来产能提升。",
            "source": "rss_demo",
            "url": "https://example.com/2",
            "published_at": "2026-02-26T11:00:00+00:00",
        },
    ]

    runner = BridgeRunner()
    run1 = runner.run_export(rows, limit=100, force_full=False)

    assert run1["status"] == "success"
    assert run1["export_count"] == 2
    assert run1["batch_file_path"]
    assert Path(run1["batch_file_path"]).exists()

    state = runner.get_status()
    assert state["last_run"]["run_id"] == run1["run_id"]
    assert state["last_run"]["export_count"] == 2
    assert state["cursor"]["last_seen_time"]

    # 第二次增量导出应为空（游标生效）
    run2 = runner.run_export(rows, limit=100, force_full=False)
    assert run2["status"] == "success"
    assert run2["export_count"] == 0


def test_bridge_runner_force_full_ignores_cursor(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo.bridge_runner import BridgeRunner

    rows = [
        {
            "id": "n1",
            "title": "某整机厂发布新产品",
            "content": "新品发布面向工业机器人场景。",
            "source": "rss_demo",
            "url": "https://example.com/3",
            "published_at": datetime(2026, 2, 26, 12, 0, tzinfo=timezone.utc).isoformat(),
        }
    ]

    runner = BridgeRunner()
    _ = runner.run_export(rows, force_full=False)
    run2 = runner.run_export(rows, force_full=True)

    assert run2["export_count"] == 1
    assert run2["force_full"] is True
