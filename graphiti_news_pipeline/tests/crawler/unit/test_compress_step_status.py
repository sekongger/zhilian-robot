import unittest
from types import SimpleNamespace

from crawler.pipeline.steps.compress_step import run_compress


class _FakeRepository:
    def __init__(self, records: list[dict]) -> None:
        self.records = records
        self.updated: dict[str, dict] = {}
        self.incremented: list[str] = []

    def list_by_status(self, statuses: list[str], limit: int) -> list[dict]:
        filtered = [r for r in self.records if r.get("status") in statuses]
        return filtered[:limit]

    def increment_attempt(self, article_id: str) -> int:
        self.incremented.append(article_id)
        return 1

    def update_article(self, article_id: str, fields: dict) -> None:
        self.updated[article_id] = fields


class _FakeCompressor:
    def compress(self, *, title: str, text: str, max_chars: int) -> dict:  # type: ignore[no-untyped-def]
        return {"graphiti_text": f"{title}:{text[:10]}", "structured_facts": {"ok": True}}


class CompressStepStatusTests(unittest.TestCase):
    def test_dedup_passed_record_can_be_compressed(self) -> None:
        repo = _FakeRepository(
            [
                {
                    "article_id": "a-1",
                    "status": "DEDUP_PASSED",
                    "title": "标题",
                    "content_clean": "这是清洗后的正文",
                }
            ]
        )
        context = SimpleNamespace(
            repository=repo,
            compressor=_FakeCompressor(),
            config=SimpleNamespace(compress_max_chars=200),
        )

        result = run_compress(context, limit=10)

        self.assertEqual(result["compressed"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertIn("a-1", repo.incremented)
        self.assertEqual(repo.updated["a-1"]["status"], "COMPRESSED")
        self.assertIn("compressed_text", repo.updated["a-1"])


if __name__ == "__main__":
    unittest.main()
