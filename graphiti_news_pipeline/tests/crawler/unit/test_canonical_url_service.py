import unittest

from crawler.services.canonical_url_service import canonicalize_url


class CanonicalUrlServiceTests(unittest.TestCase):
    def test_removes_tracking_params(self) -> None:
        url = "https://example.com/a?utm_source=x&keep=1&spm=abc&utm_campaign=y"
        self.assertEqual(canonicalize_url(url), "https://example.com/a?keep=1")

    def test_adds_scheme_when_missing(self) -> None:
        self.assertEqual(canonicalize_url("example.com/a?id=1"), "https://example.com/a?id=1")

    def test_handles_blank_url(self) -> None:
        self.assertEqual(canonicalize_url(""), "")


if __name__ == "__main__":
    unittest.main()
