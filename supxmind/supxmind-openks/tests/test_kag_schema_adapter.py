from pathlib import Path


def test_compile_openks_schema_to_kag_marklang_contains_namespace_and_types():
    from openks.common.interop.kag_schema_adapter import compile_module_schema

    schema_text = compile_module_schema("news_kg", namespace="OpenKSNews")

    assert schema_text.startswith("namespace OpenKSNews\n\n")
    assert "NewsDocument(资讯文档): EntityType" in schema_text
    assert "Enterprise(企业主体): EntityType" in schema_text
    assert "mentions_technology(资讯提及技术要素): Technology" not in schema_text
    assert "mentionsTechnology(资讯提及技术要素): Technology" in schema_text
    assert "publishTime(资讯发布时间): Text" in schema_text
    assert "confidence(抽取或推理置信度): Float" in schema_text
    assert "\tproperties:" in schema_text
    assert "\t\tpublishTime(资讯发布时间): Text" in schema_text


def test_export_module_schema_writes_schema_file_into_kag_project(tmp_path: Path):
    from openks.common.interop.kag_schema_adapter import export_module_schema_to_kag_project

    project_dir = tmp_path / "NewsProject"
    result = export_module_schema_to_kag_project(
        "news_kg",
        namespace="OpenKSNews",
        project_dir=project_dir,
    )

    schema_path = project_dir / "schema" / "OpenKSNews.schema"
    assert schema_path.exists()
    assert result["schema_path"] == schema_path
    assert result["namespace"] == "OpenKSNews"
    assert result["module_name"] == "news_kg"
    assert "namespace OpenKSNews" in schema_path.read_text(encoding="utf-8")


def test_export_module_schema_can_trigger_commit(monkeypatch, tmp_path: Path):
    from openks.common.interop import kag_schema_adapter

    events = {}

    class FakeMarkLang:
        def __init__(self, filename, host_addr=None, project_id=None):
            events["filename"] = filename
            events["host_addr"] = host_addr
            events["project_id"] = project_id

        def sync_schema(self):
            events["sync_called"] = True
            return True

    monkeypatch.setattr(kag_schema_adapter, "_resolve_spg_schema_marklang", lambda: FakeMarkLang)

    project_dir = tmp_path / "NewsProject"
    result = kag_schema_adapter.export_module_schema_to_kag_project(
        "news_kg",
        namespace="OpenKSNews",
        project_dir=project_dir,
        commit=True,
        host_addr="http://127.0.0.1:8887",
        project_id=123,
    )

    assert result["committed"] is True
    assert events["sync_called"] is True
    assert events["host_addr"] == "http://127.0.0.1:8887"
    assert events["project_id"] == 123
    assert events["filename"].endswith("OpenKSNews.schema")
