import unittest
from types import SimpleNamespace

from crawler.pipeline.steps.dedup_step import run_dedup


class _FakeRepository:
    def __init__(
        self,
        records: list[dict],
        *,
        duplicate_by_key: bool = False,
        duplicate_by_title_day: bool = False,
        duplicate_by_content_signature: bool = False,
    ) -> None:
        self._records = records
        self._duplicate_by_key = duplicate_by_key
        self._duplicate_by_title_day = duplicate_by_title_day
        self._duplicate_by_content_signature = duplicate_by_content_signature
        self.updated: dict[str, dict] = {}

    def list_by_status(self, statuses: list[str], limit: int) -> list[dict]:
        return self._records[:limit]

    def has_duplicate(self, dedup_key: str, article_id: str) -> bool:
        return self._duplicate_by_key

    def has_duplicate_by_title_day(self, title_dedup: str, publish_day: str, article_id: str) -> bool:
        return self._duplicate_by_title_day

    def has_duplicate_by_content_signature(
        self,
        content_signature: str,
        publish_day: str,
        article_id: str,
    ) -> bool:
        return self._duplicate_by_content_signature

    def update_article(self, article_id: str, fields: dict) -> None:
        self.updated[article_id] = fields


def _record() -> dict:
    return {
        "article_id": "a-1",
        "dedup_key": "k-1",
        "title_dedup": "百度智能云新模型发布",
        "publish_day": "2026-04-13",
        "content_signature": "sig-1",
    }


class DedupStepTests(unittest.TestCase):
    def test_rejects_duplicate_by_title_day(self) -> None:
        repo = _FakeRepository([_record()], duplicate_by_title_day=True)
        result = run_dedup(SimpleNamespace(repository=repo), limit=10)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["rejected"], 1)
        self.assertEqual(repo.updated["a-1"]["compress_error"], "duplicate_title_day")

    def test_rejects_duplicate_by_content_signature(self) -> None:
        repo = _FakeRepository([_record()], duplicate_by_content_signature=True)
        result = run_dedup(SimpleNamespace(repository=repo), limit=10)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["rejected"], 1)
        self.assertEqual(repo.updated["a-1"]["compress_error"], "duplicate_content_signature")

    def test_passes_when_not_duplicate(self) -> None:
        repo = _FakeRepository([_record()])
        result = run_dedup(SimpleNamespace(repository=repo), limit=10)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["rejected"], 0)
        self.assertEqual(repo.updated["a-1"]["status"], "DEDUP_PASSED")

    def test_rejects_when_missing_dedup_key(self) -> None:
        record = _record()
        record["dedup_key"] = ""
        repo = _FakeRepository([record])
        result = run_dedup(SimpleNamespace(repository=repo), limit=10)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["rejected"], 1)
        self.assertEqual(repo.updated["a-1"]["compress_error"], "missing_dedup_key")


if __name__ == "__main__":
    unittest.main()
