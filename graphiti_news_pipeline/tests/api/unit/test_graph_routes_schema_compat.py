import os
import unittest


os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_BASE", "https://example.invalid/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from api.graph_routes import _resolve_entity_label  # noqa: E402


class GraphRoutesSchemaCompatTests(unittest.TestCase):
    def test_resolve_entity_label_new_and_old_aliases(self) -> None:
        self.assertEqual(_resolve_entity_label("company"), "Enterprise")
        self.assertEqual(_resolve_entity_label("enterprise"), "Enterprise")
        self.assertEqual(_resolve_entity_label("product"), "Product")
        self.assertEqual(_resolve_entity_label("productobject"), "Product")
        self.assertEqual(_resolve_entity_label("product_model"), "ProductModel")
        self.assertEqual(_resolve_entity_label("technology"), "Technology")


if __name__ == "__main__":
    unittest.main()
