import unittest

from crawler.services.relevance_service import evaluate_relevance


class RelevanceServiceTests(unittest.TestCase):
    def test_high_recall_passes_single_keyword(self) -> None:
        result = evaluate_relevance("某公司发布新产品", "该产品用于工业机器人产线", mode="high_recall")
        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 1.0)
        self.assertIn("工业机器人", result.matched_keywords)

    def test_high_precision_rejects_irrelevant_text(self) -> None:
        result = evaluate_relevance("消费电子新品", "这是一条普通科技新闻", mode="high_precision")
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_title_hit_has_higher_weight(self) -> None:
        body_only = evaluate_relevance("普通标题", "出现协作机器人", mode="high_precision")
        title_hit = evaluate_relevance("协作机器人量产", "普通正文", mode="high_precision")
        self.assertLess(body_only.score, title_hit.score)


if __name__ == "__main__":
    unittest.main()
