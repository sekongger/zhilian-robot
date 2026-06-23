from __future__ import annotations

import json
import logging
import os

import requests

from crawler.domain.errors import CompressionError
from crawler.utils.text_utils import clip_text

logger = logging.getLogger(__name__)


class LLMCompressor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.api_base = os.getenv("OPENAI_API_BASE", "").strip().rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "").strip()
        self.timeout_seconds = int(os.getenv("CRAWLER_COMPRESS_TIMEOUT_SECONDS", "60"))
        self.output_mode = os.getenv("CRAWLER_COMPRESS_OUTPUT_MODE", "text").strip().lower()

    def compress(self, *, title: str, text: str, max_chars: int) -> dict:
        if not text.strip():
            return {
                "graphiti_text": "",
                "structured_facts": {
                    "title": title.strip(),
                    "entities": [],
                    "events": [],
                    "numbers": [],
                },
            }

        if not (self.api_key and self.api_base and self.model):
            clipped = clip_text(text, max_chars)
            return {
                "graphiti_text": clipped,
                "structured_facts": None,
            }

        endpoint = f"{self.api_base}/chat/completions"
        if self.output_mode == "dual":
            payload = {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You transform Chinese robotics industry news into extraction-friendly structured data. "
                            "Return strict JSON with keys: graphiti_text, structured_facts. "
                            "graphiti_text must be concise Chinese plain text for KG extraction, "
                            "containing entities, events, time, place, key numbers, and relations. "
                            "Do not hallucinate. Keep graphiti_text within char limit."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Output JSON only. graphiti_text <= {max_chars} Chinese characters.\n"
                            "structured_facts should include: title, entities, events, numbers.\n"
                            "Each entity should include name and type when possible.\n"
                            "Each event should include subject, predicate, object, time when possible.\n"
                            f"Title: {title}\n"
                            f"Body:\n{text}"
                        ),
                    },
                ],
            }
        else:
            payload = {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You compress Chinese robotics industry news for knowledge graph extraction. "
                            "Keep only grounded facts: entities, events, time, place, key numbers, and explicit relations. "
                            "No hallucination, no commentary, no markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Compress to <= {max_chars} Chinese characters.\n"
                            f"Title: {title}\n"
                            f"Body:\n{text}"
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
            output = data["choices"][0]["message"]["content"]
            structured_facts = None
            if self.output_mode == "dual":
                parsed = json.loads(str(output))
                graphiti_text = clip_text(str(parsed.get("graphiti_text", "")), max_chars)
                sf = parsed.get("structured_facts")
                if isinstance(sf, dict):
                    structured_facts = sf
            else:
                graphiti_text = clip_text(str(output), max_chars)
            if not graphiti_text:
                raise CompressionError("LLM returned empty compressed text.")
            return {
                "graphiti_text": graphiti_text,
                "structured_facts": structured_facts,
            }
        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Compression failed, fallback to clipping: %s", exc)
            fallback = clip_text(text, max_chars)
            if fallback:
                return {
                    "graphiti_text": fallback,
                    "structured_facts": None,
                }
            raise CompressionError(str(exc)) from exc
