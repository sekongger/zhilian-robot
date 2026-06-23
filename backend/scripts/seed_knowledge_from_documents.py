"""从标准化文档生成最小 Statement/Context（用于展示与验证）。"""

import sys
import os
import argparse
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.mongodb import mongodb_conn


def _make_id(prefix: str, value: str) -> str:
    raw = value or ""
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}{digest}"


def seed(limit: int = 0) -> int:
    inc_doc = mongodb_conn.get_collection("inc_document")
    inc_stmt = mongodb_conn.get_collection("inc_statement")
    inc_ctx = mongodb_conn.get_collection("inc_context")

    projection = {
        "doc_id": 1,
        "title": 1,
        "data_source": 1,
        "resource_type": 1,
        "publish_time": 1,
        "created_at": 1,
    }
    cursor = inc_doc.find({}, projection).sort([("publish_time", -1), ("created_at", -1)])
    if limit and limit > 0:
        cursor = cursor.limit(limit)

    created = 0
    for doc in cursor:
        doc_id = doc.get("doc_id")
        if not doc_id:
            continue

        context_id = _make_id("KC", doc_id)
        statement_id = _make_id("ST", doc_id)

        begin_time = doc.get("publish_time") or doc.get("created_at") or datetime.utcnow()
        context_doc = {
            "context_id": context_id,
            "context_type": "document",
            "begin_time": begin_time,
            "end_time": None,
            "doc_id": doc_id,
            "context_source_id": doc.get("data_source"),
            "context_scenario": doc.get("resource_type") or "document",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        statement_doc = {
            "statement_id": statement_id,
            "statement_type": "type",
            "subject_id": doc_id,
            "predicate_id": "ont:Document",
            "object_type": "class",
            "object_value": doc.get("resource_type") or "document",
            "confidence": 0.6,
            "doc_id": doc_id,
            "context_id": context_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        ctx_result = inc_ctx.update_one(
            {"context_id": context_id},
            {"$setOnInsert": context_doc},
            upsert=True,
        )
        stmt_result = inc_stmt.update_one(
            {"statement_id": statement_id},
            {"$setOnInsert": statement_doc},
            upsert=True,
        )

        if ctx_result.upserted_id or stmt_result.upserted_id:
            created += 1

    return created


def main():
    parser = argparse.ArgumentParser(description="Seed minimal Statement/Context from inc_document")
    parser.add_argument("--limit", type=int, default=0, help="limit documents to process (0 = all)")
    args = parser.parse_args()

    created = seed(args.limit)
    print(f"seeded: {created}")


if __name__ == "__main__":
    main()
