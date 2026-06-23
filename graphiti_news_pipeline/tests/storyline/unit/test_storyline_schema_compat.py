import os
import unittest


os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_BASE", "https://example.invalid/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from services.storyline_service import _is_company_entity, _is_product_entity  # noqa: E402


class StorylineSchemaCompatTests(unittest.TestCase):
    def test_company_entity_recognizes_old_and_new_labels(self) -> None:
        self.assertTrue(_is_company_entity({"Company"}))
        self.assertTrue(_is_company_entity({"Enterprise"}))

    def test_product_entity_recognizes_old_and_new_labels(self) -> None:
        self.assertTrue(_is_product_entity({"ProductObject"}))
        self.assertTrue(_is_product_entity({"Product"}))
        self.assertTrue(_is_product_entity({"ProductModel"}))


if __name__ == "__main__":
    unittest.main()
