import os
import unittest

# Ensure module-level GraphitiService initialization has required env vars.
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_BASE", "https://example.invalid/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from services.graphiti_service import GraphitiService  # noqa: E402


class GraphitiServiceIdempotentTests(unittest.TestCase):
    def test_normalize_episode_metadata_trims_and_canonicalizes(self) -> None:
        metadata = {
            "title": "  测试标题  ",
            "news_source": "  Test Source  ",
            "news_url": "example.com/news?id=1&utm_source=abc",
            "raw_text": "  原文  ",
        }
        normalized = GraphitiService._normalize_episode_metadata(metadata)
        self.assertEqual(normalized["title"], "测试标题")
        self.assertEqual(normalized["news_source"], "Test Source")
        self.assertEqual(normalized["raw_text"], "原文")
        self.assertEqual(normalized["news_url"], "https://example.com/news?id=1")

    def test_normalize_episode_metadata_empty_values_to_none(self) -> None:
        normalized = GraphitiService._normalize_episode_metadata(
            {"title": " ", "news_source": "", "news_url": " ", "raw_text": "  "}
        )
        self.assertIsNone(normalized["title"])
        self.assertIsNone(normalized["news_source"])
        self.assertIsNone(normalized["news_url"])
        self.assertIsNone(normalized["raw_text"])

    def test_build_existing_episode_stub(self) -> None:
        stub = GraphitiService._build_existing_episode_stub(
            {"uuid": "ep-1", "valid_at": None, "created_at": None}
        )
        self.assertEqual(stub.episode.uuid, "ep-1")
        self.assertEqual(stub.nodes, [])


if __name__ == "__main__":
    unittest.main()
