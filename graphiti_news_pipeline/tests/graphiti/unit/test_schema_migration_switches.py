import os
import unittest
from unittest.mock import patch


os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_BASE", "https://example.invalid/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from services.graphiti_service import GraphitiService  # noqa: E402


class GraphitiSchemaSwitchTests(unittest.TestCase):
    def test_resolve_schema_version_default_v1(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(GraphitiService._resolve_schema_version(), "v1")

    def test_resolve_schema_version_v2_aliases(self) -> None:
        for value in ("v2", "0422", "latest", "new"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"GRAPHITI_SCHEMA_VERSION": value}, clear=False):
                    self.assertEqual(GraphitiService._resolve_schema_version(), "v2")

    def test_build_entity_types_v2_contains_enterprise(self) -> None:
        entity_types = GraphitiService._build_entity_types_v2()
        self.assertIn("Enterprise", entity_types)
        self.assertIn("Product", entity_types)
        self.assertIn("EnterpriseEvent", entity_types)


if __name__ == "__main__":
    unittest.main()
