from __future__ import annotations

import hashlib


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_article_id(source_id: str, canonical_url: str, title: str, publish_time_key: str) -> str:
    raw = "|".join([source_id.strip(), canonical_url.strip(), title.strip(), publish_time_key.strip()])
    return sha1_hex(raw)

