import asyncio

from app.services import openks_schema_runtime_service


def test_apply_openks_news_kg_schema_uses_project_namespace(monkeypatch):
    events = {}

    def fake_compile(module_name, *, namespace):
        events["compile_namespace"] = namespace
        return f"namespace {namespace}\n\nNewsDocument(资讯文档): EntityType\n"

    def fake_export(module_name, *, namespace, project_dir, commit, host_addr, project_id):
        events["export_namespace"] = namespace
        events["host_addr"] = host_addr
        events["project_id"] = project_id
        return {
            "module_name": module_name,
            "namespace": namespace,
            "project_dir": project_dir,
            "schema_path": project_dir / f"{namespace}.schema",
            "committed": True,
        }

    monkeypatch.setattr(openks_schema_runtime_service, "_load_openks_interop", lambda: (fake_compile, fake_export))
    monkeypatch.setattr(openks_schema_runtime_service, "_resolve_project_namespace", lambda project_id, host_addr: "zhilian")
    monkeypatch.setattr(
        openks_schema_runtime_service,
        "_activate_openks_model_profile",
        lambda project_id, schema_script, activate_label: {
            "project_id": project_id,
            "schema_script": schema_script,
            "label": activate_label,
            "source": "openks_module",
        },
    )

    payload = asyncio.run(
        openks_schema_runtime_service.apply_openks_news_kg_schema(
            project_id=1,
            activate_label="workflow-step",
        )
    )

    assert events["compile_namespace"] == "zhilian"
    assert events["export_namespace"] == "zhilian"
    assert payload["namespace"] == "zhilian"
    assert payload["compiled_schema_script"].startswith("namespace zhilian")
