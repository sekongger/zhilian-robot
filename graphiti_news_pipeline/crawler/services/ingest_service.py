from __future__ import annotations

import logging
import os
from typing import Any

import requests

from crawler.domain.errors import IngestError

logger = logging.getLogger(__name__)


class GraphitiIngestClient:
    def __init__(self):
        base = os.getenv("CRAWLER_GRAPHITI_API_BASE", "http://localhost:8000/api").strip().rstrip("/")
        self.endpoint = f"{base}/add-text"
        self.timeout_seconds = int(os.getenv("CRAWLER_INGEST_TIMEOUT_SECONDS", "600"))

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            # Keep server-side detail to make INGEST_FAILED root-cause diagnosable.
            detail = ""
            try:
                body = exc.response.json() if exc.response is not None else {}
                if isinstance(body, dict):
                    detail = str(body.get("detail") or "").strip()
            except Exception:
                detail = ""
            message = str(exc)
            if detail:
                message = f"{message}; detail={detail}"
            raise IngestError(message) from exc
        except requests.RequestException as exc:
            raise IngestError(str(exc)) from exc
