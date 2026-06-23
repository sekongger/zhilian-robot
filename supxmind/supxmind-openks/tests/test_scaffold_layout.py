from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("stage", "module_name"),
    [
        ("fact", "news_kg"),
        ("fact", "report_kg"),
        ("fact", "event_kg"),
        ("fact", "industry_network"),
        ("cognition", "industry_chain"),
        ("decision", "recommendation"),
    ],
)
def test_scaffolded_module_contains_minimum_runtime_files(stage, module_name):
    root = Path(__file__).resolve().parents[1]
    module_root = root / "openks" / "kg" / stage / module_name

    expected = [
        module_root / "schema" / "__init__.py",
        module_root / "builder" / "__init__.py",
        module_root / "reasoner" / "__init__.py",
        module_root / "solver" / "__init__.py",
        module_root / "config" / f"{module_name}.yaml",
        module_root / "tests" / f"test_{module_name}.py",
    ]

    missing = [str(path.relative_to(root)) for path in expected if not path.exists()]
    assert not missing, f"missing scaffold files: {missing}"
