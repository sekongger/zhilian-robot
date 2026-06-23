#!/usr/bin/env python3
"""Import a GraphImportBatch JSON file into Neo4j for visual inspection."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable


NODE_BUCKETS = ("concept_nodes", "entity_nodes", "event_nodes", "document_nodes", "chunk_nodes")


@dataclass
class Neo4jImportNode:
    graph_id: str
    type_name: str
    name: str | None
    labels: list[str]
    properties: dict[str, Any]
    is_stub: bool = False


@dataclass
class Neo4jImportEdge:
    subject_graph_id: str
    object_graph_id: str
    rel_type: str
    properties: dict[str, Any]


@dataclass
class Neo4jImportPayload:
    nodes: list[Neo4jImportNode]
    edges: list[Neo4jImportEdge]


def load_batch(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_import_payload(batch: dict[str, Any]) -> Neo4jImportPayload:
    nodes_by_id: dict[str, Neo4jImportNode] = {}
    for bucket in NODE_BUCKETS:
        for raw_node in batch.get(bucket, []) or []:
            node = _build_node(raw_node, batch_id=str(batch.get("batch_id") or ""))
            if node.graph_id not in nodes_by_id:
                nodes_by_id[node.graph_id] = node

    edges: list[Neo4jImportEdge] = []
    for raw_edge in batch.get("edges", []) or []:
        subject_id = str(raw_edge.get("subject_graph_id") or "")
        object_id = str(raw_edge.get("object_graph_id") or "")
        if not subject_id or not object_id:
            continue
        if subject_id not in nodes_by_id:
            nodes_by_id[subject_id] = _build_stub_node(subject_id, batch_id=str(batch.get("batch_id") or ""))
        if object_id not in nodes_by_id:
            nodes_by_id[object_id] = _build_stub_node(object_id, batch_id=str(batch.get("batch_id") or ""))
        edges.append(
            Neo4jImportEdge(
                subject_graph_id=subject_id,
                object_graph_id=object_id,
                rel_type=_sanitize_relationship_type(str(raw_edge.get("predicate") or "RELATED_TO")),
                properties=_sanitize_properties(
                    {
                        **(raw_edge.get("properties") or {}),
                        "predicate": raw_edge.get("predicate"),
                        "batchId": batch.get("batch_id"),
                    }
                ),
            )
        )

    return Neo4jImportPayload(nodes=list(nodes_by_id.values()), edges=edges)


def import_payload(
    payload: Neo4jImportPayload,
    *,
    uri: str,
    user: str,
    password: str,
    database: str | None = None,
    clear_batch_id: str | None = None,
) -> None:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            _ensure_constraint(session)
            if clear_batch_id:
                session.execute_write(_delete_batch, clear_batch_id)
            for node in payload.nodes:
                session.execute_write(_merge_node_or_reuse_existing, node)
            for edge in payload.edges:
                session.execute_write(_merge_edge, edge)
    finally:
        driver.close()


def _build_node(raw_node: dict[str, Any], *, batch_id: str) -> Neo4jImportNode:
    type_name = str(raw_node.get("type_name") or _type_from_graph_id(str(raw_node.get("graph_id") or "")))
    graph_id = str(raw_node.get("graph_id") or "")
    properties = _sanitize_properties(
        {
            **(raw_node.get("properties") or {}),
            "id": graph_id,
            "graph_id": graph_id,
            "type_name": type_name,
            "name": raw_node.get("name"),
            "batchId": batch_id,
            "isStub": False,
        }
    )
    return Neo4jImportNode(
        graph_id=graph_id,
        type_name=type_name,
        name=str(raw_node.get("name")) if raw_node.get("name") not in (None, "") else None,
        labels=_build_labels(type_name),
        properties=properties,
        is_stub=False,
    )


def _build_stub_node(graph_id: str, *, batch_id: str) -> Neo4jImportNode:
    type_name = _type_from_graph_id(graph_id)
    return Neo4jImportNode(
        graph_id=graph_id,
        type_name=type_name,
        name=graph_id,
        labels=_build_labels(type_name),
        properties=_sanitize_properties(
            {
                "id": graph_id,
                "graph_id": graph_id,
                "type_name": type_name,
                "name": graph_id,
                "batchId": batch_id,
                "isStub": True,
                "sourceSystem": "fusion_batch_stub",
            }
        ),
        is_stub=True,
    )


def _merge_node(tx, node: Neo4jImportNode) -> None:
    labels = "".join(f":`{label}`" for label in node.labels)
    query = f"""
    MERGE (n:IncoreFusionNode {{id: $id}})
    SET n{labels}
    SET n += $properties
    """
    tx.run(query, id=node.graph_id, properties=node.properties).consume()


def _merge_node_or_reuse_existing(tx, node: Neo4jImportNode) -> None:
    if not node.is_stub:
        _merge_node(tx, node)
        return
    existing = tx.run(
        """
        MATCH (n)
        WHERE n.id = $id OR n.graph_id = $id
        RETURN count(n) AS count
        """,
        id=node.graph_id,
    ).single()
    if existing and int(existing["count"]) > 0:
        return
    _merge_node(tx, node)


def _merge_edge(tx, edge: Neo4jImportEdge) -> None:
    query = f"""
    MATCH (s)
    WHERE s.id = $subject_id OR s.graph_id = $subject_id
    WITH s
    LIMIT 1
    MATCH (o)
    WHERE o.id = $object_id OR o.graph_id = $object_id
    WITH s, o
    LIMIT 1
    MERGE (s)-[r:`{edge.rel_type}`]->(o)
    SET r += $properties
    """
    tx.run(
        query,
        subject_id=edge.subject_graph_id,
        object_id=edge.object_graph_id,
        properties=edge.properties,
    ).consume()


def _delete_batch(tx, batch_id: str) -> None:
    tx.run(
        """
        MATCH (n:IncoreFusionNode {batchId: $batch_id})
        DETACH DELETE n
        """,
        batch_id=batch_id,
    ).consume()


def _ensure_constraint(session) -> None:
    session.run(
        """
        CREATE CONSTRAINT incore_fusion_node_id IF NOT EXISTS
        FOR (n:IncoreFusionNode)
        REQUIRE n.id IS UNIQUE
        """
    ).consume()


def _build_labels(type_name: str) -> list[str]:
    labels = ["IncoreFusionNode", _sanitize_label(type_name)]
    if type_name == "NewsEntityProfile":
        labels.append("NewsEntityProfile")
    return _unique(labels)


def _sanitize_label(value: str) -> str:
    sanitized = re.sub(r"[^0-9A-Za-z_]", "_", value.strip())
    if not sanitized:
        return "Unknown"
    if sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized


def _sanitize_relationship_type(value: str) -> str:
    sanitized = re.sub(r"[^0-9A-Za-z_]", "_", value.strip())
    if not sanitized:
        sanitized = "RELATED_TO"
    if sanitized[0].isdigit():
        sanitized = f"REL_{sanitized}"
    return sanitized


def _sanitize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in properties.items():
        if value in (None, ""):
            continue
        result[str(key)] = _sanitize_property_value(value)
    return result


def _sanitize_property_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _type_from_graph_id(graph_id: str) -> str:
    if ":" not in graph_id:
        return "Unknown"
    return graph_id.split(":", 1)[0]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a fusion GraphImportBatch JSON file into Neo4j.")
    parser.add_argument("--batch", required=True, help="Path to fusion_batch.json.")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "password123"))
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE") or None)
    parser.add_argument("--clear-batch", action="store_true", help="Delete existing IncoreFusionNode nodes from the same batch first.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batch = load_batch(args.batch)
    payload = build_import_payload(batch)
    batch_id = str(batch.get("batch_id") or "")
    print(f"Prepared Neo4j fusion graph: batch_id={batch_id} nodes={len(payload.nodes)} edges={len(payload.edges)}")
    if args.dry_run:
        return 0
    import_payload(
        payload,
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
        clear_batch_id=batch_id if args.clear_batch else None,
    )
    print(f"Imported Neo4j fusion graph: batch_id={batch_id} nodes={len(payload.nodes)} edges={len(payload.edges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
