from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase


def _env_required(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


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
        request_timeout=30,
    )


def _build_neo4j_driver():
    uri = _env_required("NEO4J_URI")
    user = _env_required("NEO4J_USER")
    password = _env_required("NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))


def _sample_node_uuids(driver, sample_size: int) -> list[str]:
    records, _, _ = driver.execute_query(
        """
        MATCH (n)
        WHERE n.uuid IS NOT NULL
        RETURN n.uuid AS uuid
        LIMIT $limit
        """,
        limit=max(sample_size * 5, sample_size),
    )
    uuids = [str(r["uuid"]) for r in records if r.get("uuid")]
    if len(uuids) <= sample_size:
        return uuids
    random.shuffle(uuids)
    return uuids[:sample_size]


def _sample_edges(driver, sample_size: int) -> list[dict]:
    records, _, _ = driver.execute_query(
        """
        MATCH (s)-[r]->(t)
        WHERE s.uuid IS NOT NULL AND t.uuid IS NOT NULL
        RETURN s.uuid AS source_uuid, t.uuid AS target_uuid, type(r) AS rel_type
        LIMIT $limit
        """,
        limit=max(sample_size * 5, sample_size),
    )
    triples = [
        {
            "source_uuid": str(r["source_uuid"]),
            "target_uuid": str(r["target_uuid"]),
            "rel_type": str(r["rel_type"]),
        }
        for r in records
    ]
    if len(triples) <= sample_size:
        return triples
    random.shuffle(triples)
    return triples[:sample_size]


def _es_has_node(es: Elasticsearch, index_name: str, uuid: str) -> bool:
    resp = es.search(
        index=index_name,
        body={
            "query": {"term": {"uuid": uuid}},
            "size": 1,
            "_source": False,
        },
    )
    return int(resp.get("hits", {}).get("total", {}).get("value", 0)) > 0


def _es_has_edge(es: Elasticsearch, index_name: str, source_uuid: str, target_uuid: str, rel_type: str) -> bool:
    resp = es.search(
        index=index_name,
        body={
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"source_node_uuid": source_uuid}},
                        {"term": {"target_node_uuid": target_uuid}},
                        {"term": {"relationship_type": rel_type}},
                    ]
                }
            },
            "size": 1,
            "_source": False,
        },
    )
    return int(resp.get("hits", {}).get("total", {}).get("value", 0)) > 0


def _count_neo4j(driver) -> dict[str, int]:
    n, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS c")
    r, _, _ = driver.execute_query("MATCH ()-[rel]->() RETURN count(rel) AS c")
    return {
        "neo4j_nodes": int(n[0]["c"] or 0) if n else 0,
        "neo4j_edges": int(r[0]["c"] or 0) if r else 0,
    }


def _count_es(es: Elasticsearch, nodes_index: str, edges_index: str) -> dict[str, int]:
    nodes_count = int(es.count(index=nodes_index, query={"match_all": {}}).get("count", 0))
    edges_count = int(es.count(index=edges_index, query={"match_all": {}}).get("count", 0))
    return {"es_nodes": nodes_count, "es_edges": edges_count}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample-based consistency check between Neo4j and ES indexes.")
    parser.add_argument("--nodes-index", default="graph_nodes")
    parser.add_argument("--edges-index", default="graph_edges")
    parser.add_argument("--node-sample", type=int, default=50)
    parser.add_argument("--edge-sample", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    es = _build_es_client()
    if not es.ping():
        raise RuntimeError("Elasticsearch is not reachable.")

    with _build_neo4j_driver() as driver:
        count_summary: dict[str, Any] = {}
        count_summary.update(_count_neo4j(driver))
        count_summary.update(_count_es(es, args.nodes_index, args.edges_index))

        node_uuids = _sample_node_uuids(driver, args.node_sample)
        missing_nodes: list[str] = []
        for uuid in node_uuids:
            if not _es_has_node(es, args.nodes_index, uuid):
                missing_nodes.append(uuid)

        edge_triples = _sample_edges(driver, args.edge_sample)
        missing_edges: list[dict] = []
        for item in edge_triples:
            if not _es_has_edge(
                es,
                args.edges_index,
                item["source_uuid"],
                item["target_uuid"],
                item["rel_type"],
            ):
                missing_edges.append(item)

    report = {
        "counts": count_summary,
        "node_sample_size": len(node_uuids),
        "edge_sample_size": len(edge_triples),
        "missing_nodes": missing_nodes,
        "missing_edges": missing_edges,
        "node_pass": len(missing_nodes) == 0,
        "edge_pass": len(missing_edges) == 0,
    }
    report["ok"] = bool(report["node_pass"] and report["edge_pass"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
