import pytest


def test_discovery_reads_module_toml_and_returns_21_modules():
    from openks.common.registry.discovery import discover_kg_modules

    modules = discover_kg_modules()

    assert len(modules) == 21
    assert any(item.name == "news_kg" and item.owner == "楼彦炜" for item in modules)
    assert any(item.name == "event_kg" for item in modules)
    assert any(item.name == "industry_network" for item in modules)


@pytest.mark.parametrize(
    ("stage", "module_name"),
    [
        ("fact", "news_kg"),
        ("fact", "report_kg"),
        ("fact", "event_kg"),
        ("fact", "industry_network"),
        ("cognition", "industry_chain"),
        ("decision", "hotspot"),
    ],
)
def test_each_sample_module_has_module_toml(stage, module_name):
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    module_file = root / "openks" / "kg" / stage / module_name / "module.toml"

    payload = tomllib.loads(module_file.read_text(encoding="utf-8"))

    assert payload["name"] == module_name
