#!/usr/bin/env python3
"""Import Wikidata graph_batch JSON files as stable common-sense Neo4j nodes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable


NODE_BUCKETS = ("concept_nodes", "entity_nodes")


@dataclass
class CommonGraphNode:
    graph_id: str
    type_name: str
    name: str
    labels: list[str]
    properties: dict[str, Any]


@dataclass
class CommonGraphEdge:
    subject_graph_id: str
    object_graph_id: str
    rel_type: str
    properties: dict[str, Any]


@dataclass
class CommonGraphImportPayload:
    nodes: list[CommonGraphNode]
    edges: list[CommonGraphEdge]


def load_batch(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_batches(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    return [load_batch(path) for path in paths]


def discover_batch_files(*, batch: str | None = None, batch_dir: str | None = None, limit: int | None = None) -> list[Path]:
    files: list[Path] = []
    if batch:
        files.append(Path(batch).expanduser().resolve())
    if batch_dir:
        files.extend(sorted(Path(batch_dir).expanduser().resolve().glob("graph_batch_*.json")))
    if limit is not None:
        files = files[: max(0, int(limit))]
    return files


def build_import_payload(
    batches: Iterable[dict[str, Any]],
    *,
    include_edges: bool = False,
    include_stubs: bool = False,
) -> CommonGraphImportPayload:
    nodes_by_id: dict[str, CommonGraphNode] = {}
    for batch in batches:
        batch_id = str(batch.get("batch_id") or "")
        for bucket in NODE_BUCKETS:
            for raw_node in batch.get(bucket, []) or []:
                node = _build_node(raw_node, batch_id=batch_id, include_stubs=include_stubs)
                if node is None:
                    continue
                existing = nodes_by_id.get(node.graph_id)
                nodes_by_id[node.graph_id] = _merge_nodes(existing, node) if existing else node

    edges: list[CommonGraphEdge] = []
    if include_edges:
        for batch in batches:
            batch_id = str(batch.get("batch_id") or "")
            for raw_edge in batch.get("edges", []) or []:
                edge = _build_edge(raw_edge, batch_id=batch_id, known_node_ids=set(nodes_by_id))
                if edge is not None:
                    edges.append(edge)

    return CommonGraphImportPayload(nodes=list(nodes_by_id.values()), edges=_dedupe_edges(edges))


def import_payload(
    payload: CommonGraphImportPayload,
    *,
    uri: str,
    user: str,
    password: str,
    database: str | None = None,
    clear_batch_ids: Iterable[str] = (),
) -> None:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            _ensure_constraints(session)
            for batch_id in clear_batch_ids:
                if batch_id:
                    session.execute_write(_delete_batch, batch_id)
            for node in payload.nodes:
                session.execute_write(_merge_node, node)
            for edge in payload.edges:
                session.execute_write(_merge_edge, edge)
    finally:
        driver.close()


def _build_node(raw_node: dict[str, Any], *, batch_id: str, include_stubs: bool) -> CommonGraphNode | None:
    graph_id = str(raw_node.get("graph_id") or "").strip()
    type_name = str(raw_node.get("type_name") or _type_from_graph_id(graph_id)).strip()
    properties = dict(raw_node.get("properties") or {})
    name = str(raw_node.get("name") or properties.get("name") or "").strip()
    if not graph_id or not type_name or not name:
        return None
    if _is_stub(raw_node, properties) and not include_stubs:
        return None
    if name == graph_id:
        return None
    if str(properties.get("_source") or "").strip() not in {"", "wikidata"}:
        return None

    merged_properties = _sanitize_properties(
        {
            **properties,
            "id": graph_id,
            "graph_id": graph_id,
            "canonicalGraphId": graph_id,
            "type_name": type_name,
            "name": name,
            "batchId": batch_id,
            "sourceSystem": "wikidata_graph_batch",
            "sourceVersion": batch_id,
            "isStub": False,
        }
    )
    return CommonGraphNode(
        graph_id=graph_id,
        type_name=type_name,
        name=name,
        labels=_build_labels(type_name),
        properties=merged_properties,
    )


def _build_edge(raw_edge: dict[str, Any], *, batch_id: str, known_node_ids: set[str]) -> CommonGraphEdge | None:
    subject_id = str(raw_edge.get("subject_graph_id") or "").strip()
    object_id = str(raw_edge.get("object_graph_id") or "").strip()
    if not subject_id or not object_id:
        return None
    if subject_id not in known_node_ids or object_id not in known_node_ids:
        return None
    predicate = _sanitize_relationship_type(str(raw_edge.get("predicate") or "RELATED_TO"))
    properties = _sanitize_properties(
        {
            **(raw_edge.get("properties") or {}),
            "predicate": raw_edge.get("predicate"),
            "batchId": batch_id,
            "sourceSystem": "wikidata_graph_batch",
        }
    )
    return CommonGraphEdge(
        subject_graph_id=subject_id,
        object_graph_id=object_id,
        rel_type=predicate,
        properties=properties,
    )


def _merge_nodes(left: CommonGraphNode | None, right: CommonGraphNode) -> CommonGraphNode:
    if left is None:
        return right
    properties = dict(left.properties)
    for key, value in right.properties.items():
        if key not in properties or properties[key] in (None, "", [], {}):
            properties[key] = value
    aliases = _merge_list_property(properties.get("alias"), right.properties.get("alias"))
    if aliases:
        properties["alias"] = aliases
    return CommonGraphNode(
        graph_id=left.graph_id,
        type_name=left.type_name or right.type_name,
        name=left.name or right.name,
        labels=_unique([*left.labels, *right.labels]),
        properties=properties,
    )


def _merge_list_property(left: Any, right: Any) -> list[str]:
    values: list[str] = []
    for value in (left, right):
        if isinstance(value, list):
            values.extend(str(item) for item in value if item not in (None, ""))
        elif value not in (None, ""):
            values.append(str(value))
    return _unique(values)


def _merge_node(tx, node: CommonGraphNode) -> None:
    labels = "".join(f":`{label}`" for label in node.labels)
    query = f"""
    MERGE (n:CommonSenseNode {{id: $id}})
    SET n{labels}
    SET n += $properties
    """
    tx.run(query, id=node.graph_id, properties=node.properties).consume()


def _merge_edge(tx, edge: CommonGraphEdge) -> None:
    query = f"""
    MATCH (s:CommonSenseNode {{id: $subject_id}})
    MATCH (o:CommonSenseNode {{id: $object_id}})
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
        MATCH (n:CommonSenseNode {batchId: $batch_id})
        DETACH DELETE n
        """,
        batch_id=batch_id,
    ).consume()


def _ensure_constraints(session) -> None:
    session.run(
        """
        CREATE CONSTRAINT common_sense_node_id IF NOT EXISTS
        FOR (n:CommonSenseNode)
        REQUIRE n.id IS UNIQUE
        """
    ).consume()


def _is_stub(raw_node: dict[str, Any], properties: dict[str, Any]) -> bool:
    if _is_truthy(raw_node.get("is_stub") or raw_node.get("isStub") or properties.get("isStub") or properties.get("is_stub")):
        return True
    return str(properties.get("_semanticType") or "").strip().lower() == "stub"


def _build_labels(type_name: str) -> list[str]:
    return _unique(["CommonSenseNode", f"IncCore.{_sanitize_label(type_name)}", _sanitize_label(type_name)])


def _type_from_graph_id(graph_id: str) -> str:
    if ":" not in graph_id:
        return "Unknown"
    return graph_id.split(":", 1)[0]


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
    if isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _dedupe_edges(edges: Iterable[CommonGraphEdge]) -> list[CommonGraphEdge]:
    seen: set[tuple[str, str, str]] = set()
    result: list[CommonGraphEdge] = []
    for edge in edges:
        key = (edge.subject_graph_id, edge.rel_type, edge.object_graph_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Wikidata graph_batch JSON files into the common Neo4j graph.")
    parser.add_argument("--batch", help="Path to one graph_batch_*.json file.")
    parser.add_argument("--batch-dir", help="Directory containing graph_batch_*.json files.")
    parser.add_argument("--limit-files", type=int, default=None, help="Only import the first N graph batch files.")
    parser.add_argument("--include-edges", action="store_true", help="Import relationships whose endpoints are imported stable nodes.")
    parser.add_argument("--include-stubs", action="store_true", help="Import stub nodes as anchors. Off by default.")
    parser.add_argument("--uri", default=os.getenv("COMMON_GRAPH_NEO4J_URI") or os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("COMMON_GRAPH_NEO4J_USER") or os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("COMMON_GRAPH_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD", "password123"))
    parser.add_argument("--database", default=os.getenv("COMMON_GRAPH_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE") or None)
    parser.add_argument("--clear-batch", action="store_true", help="Delete CommonSenseNode nodes for imported batch ids before import.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = discover_batch_files(batch=args.batch, batch_dir=args.batch_dir, limit=args.limit_files)
    if not files:
        raise SystemExit("No graph_batch files found. Provide --batch or --batch-dir.")
    batches = load_batches(files)
    payload = build_import_payload(batches, include_edges=args.include_edges, include_stubs=args.include_stubs)
    batch_ids = [str(batch.get("batch_id") or "") for batch in batches]
    print(
        "Prepared Wikidata common graph: "
        f"files={len(files)} nodes={len(payload.nodes)} edges={len(payload.edges)}"
    )
    if args.dry_run:
        return 0
    import_payload(
        payload,
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
        clear_batch_ids=batch_ids if args.clear_batch else (),
    )
    print(
        "Imported Wikidata common graph: "
        f"files={len(files)} nodes={len(payload.nodes)} edges={len(payload.edges)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
