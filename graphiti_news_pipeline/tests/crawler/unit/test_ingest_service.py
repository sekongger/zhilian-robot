import unittest
from unittest.mock import patch

import requests

from crawler.services.ingest_service import GraphitiIngestClient


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error", response=self)

    def json(self):  # type: ignore[no-untyped-def]
        return self._body


class IngestServiceTests(unittest.TestCase):
    @patch("crawler.services.ingest_service.requests.post")
    def test_http_error_message_contains_detail(self, post_mock) -> None:  # type: ignore[no-untyped-def]
        post_mock.return_value = _FakeResponse(
            500,
            {"detail": "1 validation error for ExtractedEntities: extracted_entities required"},
        )
        client = GraphitiIngestClient()

        with self.assertRaises(Exception) as ctx:
            client.ingest({"text": "abc"})

        msg = str(ctx.exception)
        self.assertIn("Server Error", msg)
        self.assertIn("detail=", msg)
        self.assertIn("ExtractedEntities", msg)


if __name__ == "__main__":
    unittest.main()
