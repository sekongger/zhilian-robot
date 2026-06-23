"""Entity resolver helpers for the wiki industry pipeline MVP."""

from __future__ import annotations


def wiki_graph_id(category: str, entity_id: str) -> str:
    return f"{category}:wiki:{entity_id}"
