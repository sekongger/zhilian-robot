from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

V2_LABELS = [
    "EconomicSector",
    "IndustryGroup",
    "Industry",
    "ProductTerm",
    "Product",
    "ProductModel",
    "Enterprise",
    "Technology",
    "Patent",
    "Organization",
    "Person",
    "Region",
    "Policy",
    "Index",
    "DataSource",
    "Document",
    "Chunk",
    "EnterpriseEvent",
    "OrganizationEvent",
]

RUNTIME_LABELS = ["Episodic", "StoryThread"]

# Keep node samples readable and stable.
PREFERRED_KEYS = [
    "uuid",
    "name",
    "labels",
    "created_at",
    "updated_at",
    "ingested_at",
    "publish_time",
    "news_source",
    "news_hotness_score",
    "momentum_score",
    "pageRank",
    "communityId",
]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return value
    return value


def pick_sample_props(props: dict[str, Any]) -> dict[str, Any]:
    sample: dict[str, Any] = {}
    for key in PREFERRED_KEYS:
        if key in props:
            sample[key] = props[key]

    # Add a few business keys when available.
    for key in ("description", "mainBusiness", "status", "belongsToProduct"):
        if key in props and key not in sample:
            sample[key] = props[key]

    # Fallback: keep first 8 non-large keys if preferred keys are too sparse.
    if len(sample) < 4:
        for key, value in props.items():
            if key in sample:
                continue
            if key.endswith("_embedding") or key == "embedding":
                continue
            if isinstance(value, list) and len(value) > 50:
                continue
            if isinstance(value, str) and len(value) > 300:
                continue
            sample[key] = value
            if len(sample) >= 8:
                break

    return to_jsonable(sample)


def count_query(label: str) -> str:
    return f"MATCH (n:{label}) RETURN count(n) AS c"


def sample_query(label: str) -> str:
    return f"""
    MATCH (n:{label})
    RETURN properties(n) AS props
    ORDER BY coalesce(n.ingested_at, n.created_at, n.updated_at, n.momentum_updated_at) DESC
    LIMIT 1
    """


def build_section(session, label: str, level: int = 2) -> list[str]:
    lines: list[str] = []
    count = int(session.run(count_query(label)).single()["c"])
    prefix = "#" * level
    lines.append(f"{prefix} {label} (count={count})")
    lines.append("")
    if count == 0:
        lines.append("No sample")
        lines.append("")
        return lines

    rec = session.run(sample_query(label)).single()
    props = dict(rec["props"]) if rec and rec.get("props") else {}
    sample = pick_sample_props(props)
    lines.append("```json")
    lines.append(json.dumps(sample, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    return lines


def main() -> int:
    load_dotenv(".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687").strip().strip('"')
    user = os.getenv("NEO4J_USER", "neo4j").strip().strip('"')
    password = os.getenv("NEO4J_PASSWORD", "password123").strip().strip('"')

    output_lines: list[str] = []
    output_lines.append("# Neo4j v2 Node Samples")
    output_lines.append("")
    output_lines.append("One latest sample node per type in the v2 schema.")
    output_lines.append("Large vectors and long text fields are intentionally omitted for readability.")
    output_lines.append("")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            for label in V2_LABELS:
                output_lines.extend(build_section(session, label, level=2))

            output_lines.append("## Runtime Nodes (Non-v2 Entity Types)")
            output_lines.append("")
            for label in RUNTIME_LABELS:
                output_lines.extend(build_section(session, label, level=3))

    out_path = Path("docs/neo4j_v2_node_samples.md")
    out_path.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"updated: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
