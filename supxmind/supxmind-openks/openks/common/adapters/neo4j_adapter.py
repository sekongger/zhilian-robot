from __future__ import annotations

from typing import Any, Dict, List


class Neo4jGraphAdapter:
    def __init__(self, graph_service: Any | None = None):
        self._graph_service = graph_service

    def _service(self):
        if self._graph_service is not None:
            return self._graph_service
        from app.services.graph_service import graph_service

        return graph_service

    def save_structured_data(self, entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._service().save_structured_data(entities, relations)
