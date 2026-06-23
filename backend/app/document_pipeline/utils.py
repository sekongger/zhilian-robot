import hashlib
import re
import time
from typing import List


_def_seq = 0


def _next_seq() -> str:
    global _def_seq
    _def_seq = (_def_seq + 1) % 1000
    return f"{_def_seq:03d}"


def generate_doc_id() -> str:
    ts = time.strftime("%Y%m%d%H%M%S")
    return f"DOC{ts}{_next_seq()}"


def generate_microcontent_id() -> str:
    ts = time.strftime("%Y%m%d%H%M%S")
    return f"MC{ts}{_next_seq()}"


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_source_name(source: str) -> str:
    if not source:
        return "unknown"
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", source.strip().lower())
    return normalized.strip("_") or "unknown"


def split_microcontent(text: str, max_len: int = 500) -> List[str]:
    if not text:
        return []
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    results = []
    for block in blocks:
        if len(block) <= max_len:
            results.append(block)
            continue
        for i in range(0, len(block), max_len):
            results.append(block[i:i + max_len])
    return results
