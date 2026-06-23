"""导出并写入固定 OpenSPG 演示图谱样例。"""

from __future__ import annotations

import argparse
import json
import hashlib
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.openspg_demo.bridge import export_news_batch_to_jsonl_lines
from app.openspg_demo.bridge import normalize_news_record
from app.openspg_demo.graph_materializer import materialize_bridge_batch
from app.openspg_demo.headlines_service import get_demo_news_samples
from app.database.mongodb import mongodb_conn


SOURCE_NEWS_COLLECTION = "news_pipeline_source_news"
ENTITY_COLLECTION = "news_pipeline_entity_instances"
STATEMENT_COLLECTION = "news_pipeline_statements"
EVIDENCE_COLLECTION = "news_pipeline_statement_evidences"

ENTITY_CATEGORY_MAP = {
    "companies": "subject",
    "products": "element",
    "technologies": "element",
}

ENTITY_TYPE_MAP = {
    "companies": "company",
    "products": "product",
    "technologies": "technology",
}

ENTITY_CLASS_MAP = {
    "companies": "ont:Company",
    "products": "ont:Product",
    "technologies": "ont:Technology",
}

PREDICATE_MAP = {
    "合作": "rel:collaborates_with",
    "研发技术": "rel:develops",
    "发布产品": "rel:produces",
}


DEMO_RELATION_FIXTURES: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "DEMO_DOC_ZLR_PARTNER": {
        "entities": {
            "companies": ["智链机器人", "宇树科技"],
            "technologies": ["具身智能", "机器视觉"],
        },
        "relations": [
            {"subject": "智链机器人", "relation": "合作", "object": "宇树科技", "confidence": 0.95, "evidence": "双方将围绕具身智能、机器视觉协同优化柔性制造。"},
            {"subject": "智链机器人", "relation": "研发技术", "object": "机器视觉", "confidence": 0.92, "evidence": "双方将围绕具身智能、机器视觉协同优化柔性制造。"},
        ],
    },
    "DEMO_DOC_ZLR_PRODUCT": {
        "entities": {
            "companies": ["智链机器人"],
            "products": ["FlexArm 协作机械臂"],
            "technologies": ["机器视觉", "控制器"],
        },
        "relations": [
            {"subject": "智链机器人", "relation": "发布产品", "object": "FlexArm 协作机械臂", "confidence": 0.96, "evidence": "FlexArm 协作机械臂集成机器视觉与控制器。"},
            {"subject": "智链机器人", "relation": "研发技术", "object": "机器视觉", "confidence": 0.9, "evidence": "FlexArm 协作机械臂集成机器视觉与控制器。"},
        ],
    },
    "DEMO_DOC_ZLR_PLATFORM": {
        "entities": {
            "companies": ["智链机器人", "先导智能"],
            "products": ["RoboOS 控制平台"],
            "technologies": ["路径规划", "控制器", "机器视觉"],
        },
        "relations": [
            {"subject": "智链机器人", "relation": "合作", "object": "先导智能", "confidence": 0.93, "evidence": "智链机器人携手先导智能发布 RoboOS 控制平台。"},
            {"subject": "智链机器人", "relation": "发布产品", "object": "RoboOS 控制平台", "confidence": 0.94, "evidence": "RoboOS 控制平台进一步强化路径规划、控制器和机器视觉能力。"},
        ],
    },
    "DEMO_DOC_ZLR_COOP": {
        "entities": {
            "companies": ["智链机器人", "宇树科技"],
            "products": ["协作机器人"],
            "technologies": ["具身智能", "机器视觉"],
        },
        "relations": [
            {"subject": "智链机器人", "relation": "合作", "object": "宇树科技", "confidence": 0.95, "evidence": "合作方案将把协作机器人、具身智能和机器视觉能力整合到智能制造产线。"},
            {"subject": "智链机器人", "relation": "发布产品", "object": "协作机器人", "confidence": 0.88, "evidence": "合作方案将把协作机器人、具身智能和机器视觉能力整合到智能制造产线。"},
        ],
    },
}


def _hash(value: str, length: int = 16) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def _make_entity_id(class_id: str, name: str) -> str:
    key = f"{class_id}:{name}".lower().strip()
    return f"EN{_hash(key, 16)}"


def _make_statement_id(doc_id: str, subject_id: str, predicate_id: str, object_id: str) -> str:
    key = f"{doc_id}|{subject_id}|{predicate_id}|{object_id}"
    return f"ST{_hash(key, 16)}"


def _normalize_predicate(predicate_raw: str) -> tuple[str, str]:
    text = str(predicate_raw or "").strip()
    if text in PREDICATE_MAP:
        return PREDICATE_MAP[text], text
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", text).strip("_").lower()
    slug = slug or f"rel_{_hash(text or 'related_to', 8)}"
    return f"rel:{slug}", text or "关联"


def _build_entity_docs(entities: Dict[str, List[str]]) -> List[Dict]:
    docs: List[Dict] = []
    seen = set()
    for category, items in (entities or {}).items():
        entity_category = ENTITY_CATEGORY_MAP.get(category)
        if not entity_category:
            continue
        class_id = ENTITY_CLASS_MAP.get(category) or "ont:Entity"
        for name in items or []:
            cleaned = str(name or "").strip()
            if not cleaned or (category, cleaned) in seen:
                continue
            seen.add((category, cleaned))
            docs.append(
                {
                    "entity_id": _make_entity_id(class_id, cleaned),
                    "class_id": class_id,
                    "entity_category": entity_category,
                    "entity_type": ENTITY_TYPE_MAP.get(category) or category,
                    "name": cleaned,
                    "canonical_name": cleaned,
                    "status": "active",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
    return docs


def _build_statement_docs(
    doc_id: str,
    relations: List[Dict],
    entity_map: Dict[str, str],
    *,
    data_source: str,
    publish_time: str,
) -> List[Dict]:
    docs: List[Dict] = []
    for relation in relations or []:
        subject_name = str(relation.get("subject") or "").strip()
        object_name = str(relation.get("object") or "").strip()
        subject_id = entity_map.get(subject_name)
        object_id = entity_map.get(object_name)
        if not subject_id or not object_id:
            continue
        predicate_id, predicate_label = _normalize_predicate(str(relation.get("relation") or relation.get("predicate") or "关联"))
        statement_id = _make_statement_id(doc_id, subject_id, predicate_id, object_id)
        docs.append(
            {
                "_id": statement_id,
                "statement_id": statement_id,
                "statement_type": "relation",
                "subject_id": subject_id,
                "predicate_id": predicate_id,
                "predicate_label": predicate_label,
                "object_type": "entity_ref",
                "object_entity_id": object_id,
                "doc_id": doc_id,
                "confidence": relation.get("confidence", 0.9),
                "context_source_id": data_source,
                "context_scenario": "news",
                "context_time_value": publish_time,
                "evidence_text": relation.get("evidence"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
    return docs


def build_demo_batch_lines() -> List[str]:
    rows = get_demo_news_samples()
    return export_news_batch_to_jsonl_lines(rows)


def build_demo_fact_payloads() -> Dict[str, List[Dict]]:
    rows = get_demo_news_samples()
    normalized_rows = [normalize_news_record(row) for row in rows]

    source_news = []
    entity_docs = []
    statement_docs = []
    evidence_docs = []

    for row in normalized_rows:
        source_news.append(
            {
                **row,
                "process_status": "completed",
                "source_id": row.get("source_id") or f"DEMO_SRC_{row['doc_id']}",
            }
        )
        fixture = DEMO_RELATION_FIXTURES.get(str(row.get("doc_id") or ""))
        if not fixture:
            continue
        current_entity_docs = _build_entity_docs(fixture["entities"])
        entity_docs.extend(current_entity_docs)
        entity_map = {
            str(item.get("name") or item.get("canonical_name") or ""): str(item.get("entity_id") or "")
            for item in current_entity_docs
            if str(item.get("name") or item.get("canonical_name") or "").strip()
        }
        current_statement_docs = _build_statement_docs(
            row["doc_id"],
            fixture["relations"],
            entity_map,
            data_source=row.get("source_name"),
            publish_time=row.get("publish_time"),
        )
        statement_docs.extend(current_statement_docs)
        for statement in current_statement_docs:
            relation = next(
                (item for item in fixture["relations"] if item["subject"] in entity_map and item["object"] in entity_map and item.get("relation") == statement.get("predicate_label")),
                fixture["relations"][0],
            )
            evidence_docs.append(
                {
                    "statement_id": statement["statement_id"],
                    "doc_id": row["doc_id"],
                    "title": row.get("title"),
                    "snippet": relation.get("evidence") or row.get("summary") or row.get("content"),
                    "source_name": row.get("source_name"),
                    "source_url": row.get("source_url"),
                    "publish_time": row.get("publish_time"),
                }
            )

    deduped_entities = {}
    for item in entity_docs:
        deduped_entities[str(item.get("entity_id") or item.get("name"))] = item

    return {
        "source_news": source_news,
        "entity_docs": list(deduped_entities.values()),
        "statement_docs": statement_docs,
        "evidence_docs": evidence_docs,
    }


def write_demo_batch(output_path: Path) -> Path:
    lines = build_demo_batch_lines()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def seed_demo_fact_documents() -> Dict[str, int]:
    payload = build_demo_fact_payloads()
    source_news = payload["source_news"]
    entity_docs = payload["entity_docs"]
    statement_docs = payload["statement_docs"]
    evidence_docs = payload["evidence_docs"]

    doc_ids = [str(item.get("doc_id") or "") for item in source_news if str(item.get("doc_id") or "").strip()]
    statement_ids = [str(item.get("statement_id") or "") for item in statement_docs if str(item.get("statement_id") or "").strip()]

    if doc_ids:
        mongodb_conn.delete_many(SOURCE_NEWS_COLLECTION, {"doc_id": {"$in": doc_ids}})
        mongodb_conn.delete_many(STATEMENT_COLLECTION, {"doc_id": {"$in": doc_ids}})
        mongodb_conn.delete_many(EVIDENCE_COLLECTION, {"doc_id": {"$in": doc_ids}})

    for row in source_news:
        mongodb_conn.update_one(
            SOURCE_NEWS_COLLECTION,
            {"doc_id": row["doc_id"]},
            {"$set": row},
            upsert=True,
        )
    for item in entity_docs:
        mongodb_conn.update_one(
            ENTITY_COLLECTION,
            {"_id": item["entity_id"]},
            {"$set": item},
            upsert=True,
        )
    for item in statement_docs:
        mongodb_conn.update_one(
            STATEMENT_COLLECTION,
            {"_id": item["statement_id"]},
            {"$set": item},
            upsert=True,
        )
    for item in evidence_docs:
        mongodb_conn.update_one(
            EVIDENCE_COLLECTION,
            {"statement_id": item["statement_id"], "doc_id": item["doc_id"]},
            {"$set": item},
            upsert=True,
        )

    return {
        "source_news": len(source_news),
        "entities": len(entity_docs),
        "statements": len(statement_docs),
        "evidences": len(evidence_docs),
        "statement_ids": len(statement_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="写入固定 OpenSPG 演示图谱样例")
    parser.add_argument("--project-id", type=int, default=1, help="OpenSPG project id")
    parser.add_argument("--openspg-base-url", default="", help="OpenSPG base url，可为空使用环境变量")
    parser.add_argument("--output", default="", help="可选：保留导出的 JSONL 文件路径")
    parser.add_argument("--write-only", action="store_true", help="仅导出 JSONL，不执行入图")
    args = parser.parse_args()

    if args.output:
        batch_file = write_demo_batch(Path(args.output))
    else:
        tmp_dir = Path(tempfile.mkdtemp(prefix="openspg-demo-graph-"))
        batch_file = write_demo_batch(tmp_dir / "stable_demo_batch.jsonl")

    result = {
        "batch_file_path": str(batch_file),
        "records": len(build_demo_batch_lines()),
    }

    if not args.write_only:
        fact_result = seed_demo_fact_documents()
        materialize_result = materialize_bridge_batch(
            batch_file_path=str(batch_file),
            project_id=max(1, int(args.project_id)),
            openspg_base_url=args.openspg_base_url or None,
        )
        result["fact_sync"] = fact_result
        result.update(materialize_result)

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
