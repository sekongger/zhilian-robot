import builtins
import importlib
import sys


def test_database_import_without_neo4j(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "neo4j":
            raise ImportError("mock missing neo4j")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    neo4j_module = sys.modules.pop("neo4j", None)
    sys.modules.pop("app.database", None)
    sys.modules.pop("app.database.neo4j_db", None)

    try:
        module = importlib.import_module("app.database")
        assert getattr(module, "NEO4J_AVAILABLE", True) is False
    finally:
        if neo4j_module is not None:
            sys.modules["neo4j"] = neo4j_module
