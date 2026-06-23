import unittest

from crawler.services.octopus_clean_service import OctopusLLMCleaner


class OctopusCleanServiceTests(unittest.TestCase):
    def test_rule_fallback_without_llm_env(self) -> None:
        cleaner = OctopusLLMCleaner()
        cleaner.api_key = ""
        cleaner.api_base = ""
        cleaner.model = ""

        cleaned, used_llm = cleaner.clean(
            title="测试标题",
            raw_text="<p>正文内容</p>\n\n免责声明：仅供参考。",
        )
        self.assertFalse(used_llm)
        self.assertIn("正文内容", cleaned)

    def test_empty_raw_text_returns_empty(self) -> None:
        cleaner = OctopusLLMCleaner()
        cleaned, used_llm = cleaner.clean(title="测试标题", raw_text="  ")
        self.assertEqual(cleaned, "")
        self.assertFalse(used_llm)


if __name__ == "__main__":
    unittest.main()
