from __future__ import annotations

import re
from html import unescape


_WS_PATTERN = re.compile(r"\s+")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return _HTML_TAG_PATTERN.sub(" ", text or "")


def normalize_text(text: str) -> str:
    raw = unescape(text or "")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = strip_html(raw)
    raw = _WS_PATTERN.sub(" ", raw)
    return raw.strip()


def clip_text(text: str, max_chars: int) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()

