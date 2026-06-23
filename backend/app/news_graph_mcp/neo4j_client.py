"""Small Neo4j client used by the news graph MCP sidecar."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


class Neo4jGraphClient:
    """Execute read-only Cypher queries against the fused big graph."""

    def __init__(
        self,
        *,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.getenv("NEWS_GRAPH_NEO4J_URI") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEWS_GRAPH_NEO4J_USER") or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEWS_GRAPH_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD", "password123")
        self.database = database or os.getenv("NEWS_GRAPH_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE") or None

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        try:
            with driver.session(database=self.database) as session:
                return [dict(record) for record in session.run(query, parameters or {})]
        finally:
            driver.close()

