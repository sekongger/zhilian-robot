from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class KgContext:
    """Runtime context shared by schema, builder, reasoner and solver."""

    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    upstream: Sequence[str] = field(default_factory=tuple)


class BaseSchema:
    """Minimal schema contract for a knowledge graph."""

    def describe(self) -> Dict[str, List[Dict[str, Any]]]:
        return {"entities": [], "relations": [], "fields": []}


class BaseBuilder:
    stage = "builder"

    def build(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return list(records)


class BaseReasoner:
    stage = "reasoner"

    def infer(self, facts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return list(facts)


class BaseSolver:
    stage = "solver"

    def solve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return {"query": query, "results": []}
