"""Load Graphiti news graph output into the IncCore fusion DTO shape."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import (
    Neo4jV2ExportPackageDTO,
    V2SourceEdgeDTO,
    V2SourceNodeDTO,
)


class GraphitiNewsNeo4jLoader:
    """Read extracted Graphiti nodes/edges from Neo4j.

    Graphiti remains the dynamic news extraction system. This loader only
    translates its graph output into the generic fusion DTOs consumed by
    ``WikidataV2FusionRunner``.
    """

    BASE_LABELS = {"Entity"}
    TYPE_ALIASES = {
        "Company": "Enterprise",
        "ProductObject": "Product",
    }

    def load_from_neo4j(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        database: str | None = None,
        group_id: str | None = None,
        limit: int = 1000,
        edge_limit: int | None = None,
        source_system: str = "graphiti_news",
    ) -> Neo4jV2ExportPackageDTO:
        """Load Graphiti graph output through a Neo4j Bolt connection."""

        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            with driver.session(database=database) as session:
                if group_id:
                    node_records = session.run(
                        """
                        MATCH (seed)
                        WHERE (seed:Entity OR seed:Episodic)
                          AND (properties(seed).group_id = $group_id OR properties(seed).fusion_batch_id = $group_id)
                        WITH collect(seed) AS seed_nodes
                        UNWIND seed_nodes AS seed
                        OPTIONAL MATCH (seed)-[]-(neighbor)
                        WITH seed_nodes, collect(neighbor) AS neighbors
                        WITH seed_nodes + neighbors AS candidates
                        UNWIND candidates AS n
                        WITH DISTINCT n
                        WHERE n IS NOT NULL AND (n:Entity OR n:Episodic)
                        RETURN elementId(n) AS node_id, labels(n) AS labels, properties(n) AS properties
                        LIMIT $limit
                        """,
                        group_id=group_id,
                        limit=int(limit),
                    ).data()
                else:
                    node_records = session.run(
                        """
                        MATCH (n)
                        WHERE n:Entity OR n:Episodic
                        RETURN elementId(n) AS node_id, labels(n) AS labels, properties(n) AS properties
                        LIMIT $limit
                        """,
                        limit=int(limit),
                    ).data()
                node_ids = [str(record["node_id"]) for record in node_records]
                edge_records = []
                if node_ids:
                    edge_records = session.run(
                        """
                        MATCH (s)-[r]->(t)
                        WHERE elementId(s) IN $node_ids AND elementId(t) IN $node_ids
                        RETURN
                            elementId(r) AS edge_id,
                            type(r) AS type,
                            properties(r) AS properties,
                            elementId(s) AS source_node_id,
                            elementId(t) AS target_node_id
                        LIMIT $limit
                        """,
                        node_ids=node_ids,
                        limit=int(edge_limit or max(limit * 10, 1000)),
                    ).data()
        finally:
            driver.close()

        return self.load_from_records(
            node_records=node_records,
            edge_records=edge_records,
            package_name=f"graphiti_news_neo4j:{group_id or 'all'}",
            source_system=source_system,
            export_dir=f"neo4j://{uri}",
        )

    def load_from_records(
        self,
        *,
        node_records: Iterable[dict[str, Any]],
        edge_records: Iterable[dict[str, Any]],
        package_name: str = "graphiti_news_records",
        source_system: str = "graphiti_news",
        export_dir: str = "memory://graphiti_news",
    ) -> Neo4jV2ExportPackageDTO:
        """Build a package from Neo4j-like records.

        This method exists so tests and offline exports can use the same
        normalization as the live Neo4j loader.
        """

        node_lookup: dict[str, V2SourceNodeDTO] = {}
        for raw_node in node_records:
            node_id = str(raw_node.get("node_id") or raw_node.get("element_id") or raw_node.get("id") or "")
            if not node_id:
                continue
            labels = [str(item) for item in raw_node.get("labels") or [] if item]
            properties = self._sanitize_mapping(raw_node.get("properties") or {})
            source_label = self._select_source_label(labels, properties)
            source_uuid = str(properties.get("uuid") or properties.get("id") or node_id)
            name = self._first_non_empty(
                properties.get("name"),
                properties.get("title"),
                properties.get("label"),
                source_uuid,
            )
            summary = self._first_non_empty(
                properties.get("summary"),
                properties.get("content"),
                properties.get("raw_text"),
                properties.get("description"),
            )
            node_lookup[node_id] = V2SourceNodeDTO(
                source_system=source_system,
                source_label=source_label,
                source_uuid=source_uuid,
                name=name,
                summary=summary,
                properties={
                    **properties,
                    "graphiti_labels": labels,
                    "source_system": source_system,
                },
            )

        edges: list[V2SourceEdgeDTO] = []
        for raw_edge in edge_records:
            source_node_id = str(raw_edge.get("source_node_id") or raw_edge.get("start_node_id") or "")
            target_node_id = str(raw_edge.get("target_node_id") or raw_edge.get("end_node_id") or "")
            source_node = node_lookup.get(source_node_id)
            target_node = node_lookup.get(target_node_id)
            if source_node is None or target_node is None:
                continue
            properties = self._sanitize_mapping(raw_edge.get("properties") or {})
            predicate = self._normalize_edge_predicate(
                edge_type=str(raw_edge.get("type") or raw_edge.get("label") or ""),
                relation_name=str(properties.get("name") or properties.get("predicate") or ""),
            )
            edges.append(
                V2SourceEdgeDTO(
                    source_system=source_system,
                    source_edge_uuid=str(properties.get("uuid") or raw_edge.get("edge_id") or ""),
                    predicate=predicate,
                    subject_source_uuid=source_node.source_uuid,
                    object_source_uuid=target_node.source_uuid,
                    subject_source_type=source_node.source_label,
                    object_source_type=target_node.source_label,
                    properties={
                        **properties,
                        "source_node_id": source_node_id,
                        "target_node_id": target_node_id,
                    },
                )
            )

        return Neo4jV2ExportPackageDTO(
            package_name=package_name,
            manifest={"source_system": source_system, "node_count": len(node_lookup), "edge_count": len(edges)},
            export_dir=str(Path(export_dir)) if "://" not in export_dir else export_dir,
            nodes=list(node_lookup.values()),
            edges=edges,
        )

    def _select_source_label(self, labels: list[str], properties: dict[str, Any]) -> str:
        if "Episodic" in labels:
            return "Episodic"
        for label in reversed(labels):
            if label in self.BASE_LABELS:
                continue
            return self.TYPE_ALIASES.get(label, label)
        raw_type = str(properties.get("entity_type") or properties.get("type") or "").strip()
        return self.TYPE_ALIASES.get(raw_type, raw_type) if raw_type else "Unknown"

    def _normalize_edge_predicate(self, *, edge_type: str, relation_name: str) -> str:
        normalized_type = edge_type.strip().upper()
        if normalized_type == "MENTIONS":
            return "mentions"
        if relation_name:
            return self._to_predicate(relation_name)
        return self._to_predicate(edge_type) or "unknown"

    @staticmethod
    def _to_predicate(value: str) -> str:
        text = value.strip()
        if not text:
            return ""
        if re.fullmatch(r"[A-Z0-9_\-\s]+", text):
            text = text.lower()
        text = re.sub(r"\s+", "_", text)
        text = text.replace("-", "_")
        return text

    def _sanitize_mapping(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {str(key): self._sanitize_value(item) for key, item in value.items()}

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    @staticmethod
    def _first_non_empty(*values: Any) -> str | None:
        for value in values:
            if value in (None, "", []):
                continue
            return str(value)
        return None
