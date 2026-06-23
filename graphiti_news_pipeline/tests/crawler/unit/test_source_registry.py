import textwrap
import unittest
from pathlib import Path

from crawler.connectors.source_registry import load_pipeline_config, load_sources
from crawler.domain.errors import ConfigError

FIXTURE_ROOT = Path("tests/crawler/fixtures")


class SourceRegistryTests(unittest.TestCase):
    def test_load_sources_and_sort_by_priority(self) -> None:
        content = textwrap.dedent(
            """
            sources:
              - id: b_source
                type: rss
                name: B
                url: https://example.com/b.xml
                priority: 20
              - id: a_source
                type: rss
                name: A
                url: https://example.com/a.xml
                priority: 10
            """
        ).strip()
        FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
        path = FIXTURE_ROOT / "_tmp_sources.yaml"
        path.write_text(content, encoding="utf-8")
        try:
            sources = load_sources(path)
        finally:
            if path.exists():
                path.unlink()
        self.assertEqual([s.source_id for s in sources], ["a_source", "b_source"])

    def test_load_pipeline_config(self) -> None:
        content = textwrap.dedent(
            """
            pipeline:
              max_content_length: 1234
              min_content_length: 66
              compress_max_chars: 100
              relevance_mode: high_precision
              gray_mode: true
              schedule_hours: 4
            """
        ).strip()
        FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
        path = FIXTURE_ROOT / "_tmp_pipeline.yaml"
        path.write_text(content, encoding="utf-8")
        try:
            cfg = load_pipeline_config(path)
        finally:
            if path.exists():
                path.unlink()
        self.assertEqual(cfg.max_content_length, 1234)
        self.assertEqual(cfg.min_content_length, 66)
        self.assertEqual(cfg.compress_max_chars, 100)
        self.assertEqual(cfg.relevance_mode, "high_precision")
        self.assertTrue(cfg.gray_mode)
        self.assertEqual(cfg.schedule_hours, 4)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ConfigError):
            load_sources("not_exists_sources.yaml")


if __name__ == "__main__":
    unittest.main()
