from __future__ import annotations

import logging
import os

import requests

from crawler.utils.text_utils import clip_text, normalize_text

logger = logging.getLogger(__name__)


class OctopusLLMCleaner:
    """Pre-clean octopus content before crawler pipeline compression."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.api_base = os.getenv("OPENAI_API_BASE", "").strip().rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "").strip()
        self.timeout_seconds = int(os.getenv("CRAWLER_OCTOPUS_CLEAN_TIMEOUT_SECONDS", "60"))
        self.max_chars = int(os.getenv("CRAWLER_OCTOPUS_CLEAN_MAX_CHARS", "1600"))

    def clean(self, *, title: str, raw_text: str) -> tuple[str, bool]:
        """
        Returns (cleaned_text, used_llm).
        Falls back to deterministic clean if LLM is unavailable/fails.
        """
        normalized = normalize_text(raw_text)
        if not normalized:
            return "", False

        fallback = clip_text(normalized, self.max_chars)
        if not (self.api_key and self.api_base and self.model):
            return fallback, False

        endpoint = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You pre-clean Chinese industry news text for downstream KG compression. "
                        "Remove template noise, disclaimers, boilerplate, and duplicated fragments. "
                        "Keep factual content only: entities, events, time, place, key numbers, and explicit relations. "
                        "No hallucination. Output plain Chinese text only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Please clean the news body while preserving facts.\n"
                        f"Output <= {self.max_chars} Chinese characters.\n"
                        f"Title: {title}\n"
                        f"Body:\n{normalized}"
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = str(data["choices"][0]["message"]["content"])
            cleaned = clip_text(content, self.max_chars)
            if cleaned:
                return cleaned, True
        except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
            logger.warning("Octopus LLM pre-clean failed, fallback to rule clean: %s", exc)

        return fallback, False
