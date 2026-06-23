from pathlib import Path


def test_backend_dockerfile_copies_modules_tree_for_openks_schema_runtime():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY --chown=appuser:appuser modules /app/modules" in dockerfile


def test_backend_dockerfile_installs_minimal_kag_schema_runtime_dependency():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "pip install ruamel.yaml" in dockerfile
    assert "cachetools" in dockerfile
    assert "/app/modules/kag/requirements.txt" not in dockerfile
