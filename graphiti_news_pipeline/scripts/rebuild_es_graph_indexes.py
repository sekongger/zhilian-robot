from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers
from neo4j import GraphDatabase


def _env_required(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "iso_format"):  # neo4j temporal types
        return value.iso_format()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _build_es_client() -> Elasticsearch:
    host = _env_required("ES_HOST")
    port = int(os.getenv("ES_PORT", "9200"))
    user = _env_required("ES_USER")
    password = _env_required("ES_PASS")
    scheme = "https" if "aliyuncs.com" in host else "http"
    return Elasticsearch(
        [f"{scheme}://{host}:{port}"],
        basic_auth=(user, password),
        verify_certs=False,
        request_timeout=60,
    )


def _build_neo4j_driver():
    uri = _env_required("NEO4J_URI")
    user = _env_required("NEO4J_USER")
    password = _env_required("NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))


def _create_index_if_needed(es: Elasticsearch, index_name: str, mappings: dict) -> None:
    exists = es.indices.exists(index=index_name)
    if bool(exists):
        return
    es.indices.create(index=index_name, mappings=mappings)


def _count_nodes(driver) -> int:
    records, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS c")
    return int(records[0]["c"] or 0) if records else 0


def _count_edges(driver) -> int:
    records, _, _ = driver.execute_query("MATCH ()-[r]->() RETURN count(r) AS c")
    return int(records[0]["c"] or 0) if records else 0


def _index_nodes(
    driver,
    es: Elasticsearch,
    index_name: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    total = _count_nodes(driver)
    indexed = 0
    skip = 0
    while skip < total:
        query = """
        MATCH (n)
        RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS props
        ORDER BY elementId(n)
        SKIP $skip
        LIMIT $limit
        """
        records, _, _ = driver.execute_query(query, skip=skip, limit=batch_size)
        if not records:
            break

        actions = []
        for record in records:
            props = dict(record["props"] or {})
            labels = [str(x) for x in list(record["labels"] or [])]
            doc_uuid = str(props.get("uuid") or "").strip()
            doc_id = doc_uuid or f"neo4j-node:{record['element_id']}"
            doc = _jsonable(props)
            doc["labels"] = labels
            if not doc.get("uuid"):
                doc["uuid"] = doc_id
            actions.append(
                {
                    "_op_type": "index",
                    "_index": index_name,
                    "_id": doc_id,
                    "_source": doc,
                }
            )

        if not dry_run and actions:
            helpers.bulk(es, actions, chunk_size=batch_size, request_timeout=120)

        indexed += len(actions)
        skip += len(records)
        print(f"[nodes] processed={indexed}/{total}")

    return indexed


def _index_edges(
    driver,
    es: Elasticsearch,
    index_name: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    total = _count_edges(driver)
    indexed = 0
    skip = 0
    while skip < total:
        query = """
        MATCH (s)-[r]->(t)
        RETURN
            elementId(r) AS rel_id,
            type(r) AS rel_type,
            properties(r) AS rel_props,
            coalesce(s.uuid, elementId(s)) AS source_node_uuid,
            coalesce(t.uuid, elementId(t)) AS target_node_uuid
        ORDER BY elementId(r)
        SKIP $skip
        LIMIT $limit
        """
        records, _, _ = driver.execute_query(query, skip=skip, limit=batch_size)
        if not records:
            break

        actions = []
        for record in records:
            source_uuid = str(record["source_node_uuid"])
            target_uuid = str(record["target_node_uuid"])
            rel_type = str(record["rel_type"])
            rel_props = _jsonable(dict(record["rel_props"] or {}))
            edge_doc_id = f"{source_uuid}|{rel_type}|{target_uuid}|{record['rel_id']}"
            doc = {
                "source_node_uuid": source_uuid,
                "target_node_uuid": target_uuid,
                "relationship_type": rel_type,
                "name": rel_props.get("name") or rel_type,
                "edge_doc_id": edge_doc_id,
                **rel_props,
            }
            actions.append(
                {
                    "_op_type": "index",
                    "_index": index_name,
                    "_id": edge_doc_id,
                    "_source": doc,
                }
            )

        if not dry_run and actions:
            helpers.bulk(es, actions, chunk_size=batch_size, request_timeout=120)

        indexed += len(actions)
        skip += len(records)
        print(f"[edges] processed={indexed}/{total}")

    return indexed


def _count_index_docs(es: Elasticsearch, index_name: str) -> int:
    resp = es.count(index=index_name, query={"match_all": {}})
    return int(resp.get("count", 0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild graph_nodes/graph_edges indexes from Neo4j.")
    parser.add_argument("--nodes-index", default="graph_nodes")
    parser.add_argument("--edges-index", default="graph_edges")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--target", choices=["all", "nodes", "edges"], default="all")
    parser.add_argument("--reset", action="store_true", help="Delete target indexes before indexing.")
    parser.add_argument("--dry-run", action="store_true", help="Only scan counts and batches; do not write.")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    es = _build_es_client()
    if not es.ping():
        raise RuntimeError("Elasticsearch is not reachable.")

    with _build_neo4j_driver() as driver:
        if args.reset and not args.dry_run:
            if args.target in ("all", "nodes"):
                es.indices.delete(index=args.nodes_index, ignore_unavailable=True)
            if args.target in ("all", "edges"):
                es.indices.delete(index=args.edges_index, ignore_unavailable=True)

        if args.target in ("all", "nodes") and not args.dry_run:
            _create_index_if_needed(
                es,
                args.nodes_index,
                mappings={
                    "dynamic": True,
                    "properties": {
                        "uuid": {"type": "keyword"},
                        "labels": {"type": "keyword"},
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    },
                },
            )
        if args.target in ("all", "edges") and not args.dry_run:
            _create_index_if_needed(
                es,
                args.edges_index,
                mappings={
                    "dynamic": True,
                    "properties": {
                        "source_node_uuid": {"type": "keyword"},
                        "target_node_uuid": {"type": "keyword"},
                        "relationship_type": {"type": "keyword"},
                        "name": {"type": "keyword"},
                        "edge_doc_id": {"type": "keyword"},
                    },
                },
            )

        node_indexed = 0
        edge_indexed = 0
        if args.target in ("all", "nodes"):
            node_indexed = _index_nodes(driver, es, args.nodes_index, args.batch_size, args.dry_run)
        if args.target in ("all", "edges"):
            edge_indexed = _index_edges(driver, es, args.edges_index, args.batch_size, args.dry_run)

    if not args.dry_run:
        if args.target in ("all", "nodes"):
            es.indices.refresh(index=args.nodes_index)
        if args.target in ("all", "edges"):
            es.indices.refresh(index=args.edges_index)

    result = {
        "dry_run": bool(args.dry_run),
        "target": args.target,
        "node_indexed": node_indexed,
        "edge_indexed": edge_indexed,
    }
    if not args.dry_run:
        if args.target in ("all", "nodes"):
            result["nodes_index_count"] = _count_index_docs(es, args.nodes_index)
        if args.target in ("all", "edges"):
            result["edges_index_count"] = _count_index_docs(es, args.edges_index)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
