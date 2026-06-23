from datetime import datetime

from app.document_pipeline.repository import DocumentRepository
from app.document_pipeline.utils import normalize_source_name
from app.database.mongodb import mongodb_conn

DS_ID = "DS_NEWS_MIGRATION"
TASK_ID = "TASK_DS_NEWS_MIGRATION_0001"


def map_news_doc(src: dict):
    repo = DocumentRepository(db=None)
    return repo.build_resource_doc(
        resource_type="news",
        source=src.get("source") or src.get("source_name") or "unknown",
        title=src.get("title"),
        content=src.get("content") or src.get("summary"),
        url=src.get("url") or src.get("source_url"),
    )


def _ensure_ds_meta(db):
    db.get_collection("ds_basic_info").update_one(
        {"ds_id": DS_ID},
        {
            "$setOnInsert": {
                "ds_id": DS_ID,
                "name": "资讯迁移",
                "ds_type": "INTERNET",
                "data_category": "资讯",
                "ds_source": "migration",
                "is_valid": True,
                "create_time": datetime.utcnow(),
                "update_time": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    db.get_collection("ds_access_task").update_one(
        {"task_id": TASK_ID},
        {
            "$setOnInsert": {
                "task_id": TASK_ID,
                "ds_id": DS_ID,
                "task_name": "资讯迁移",
                "access_mode": "FULL",
                "schedule_config": "manual",
                "storage_config": {"storage_type": "MONGO"},
                "is_valid": True,
                "create_time": datetime.utcnow(),
                "update_time": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def _iter_sources(db):
    for doc in db.get_collection("crawled_articles").find({}):
        yield doc
    for doc in db.get_collection("news_pipeline_source_news").find({}):
        yield doc
    for doc in db.get_collection("raw_documents").find({}):
        yield doc


def migrate(limit: int = 0):
    _ensure_ds_meta(mongodb_conn)
    repo = DocumentRepository(db=mongodb_conn)
    migrated = 0
    for src in _iter_sources(mongodb_conn):
        resource_doc = map_news_doc(src)
        source_raw = src.get("source") or src.get("source_name") or "unknown"
        source_key = normalize_source_name(source_raw)
        if source_key == "unknown":
            source_key = "crawler"
        collection_name = f"resource_news_{source_key}"
        resource_doc.update({
            "ds_id": DS_ID,
            "task_id": TASK_ID,
            "task_runtime_id": f"RECORD_{TASK_ID}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "publish_time": src.get("publish_time"),
            "process_batch_id": f"BATCH_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        })

        collection = mongodb_conn.get_collection(collection_name)
        if collection.find_one({"content_hash": resource_doc["content_hash"]}):
            continue

        collection.insert_one(resource_doc)
        inc_doc = repo.build_inc_document(resource_doc, summary=src.get("summary"))
        mongodb_conn.update_one(
            "inc_document",
            {"doc_id": inc_doc["doc_id"]},
            {"$setOnInsert": inc_doc},
            upsert=True,
        )
        micro_list = repo.build_microcontent(inc_doc["doc_id"], inc_doc.get("content"))
        if micro_list:
            mongodb_conn.get_collection("inc_microcontent").insert_many(micro_list)

        migrated += 1
        if limit and migrated >= limit:
            break

    mongodb_conn.get_collection("ds_access_record").insert_one({
        "record_id": f"RECORD_{TASK_ID}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "task_id": TASK_ID,
        "ds_id": DS_ID,
        "exec_status": "SUCCESS",
        "total_count": migrated,
        "valid_count": migrated,
        "invalid_count": 0,
        "start_time": datetime.utcnow(),
        "end_time": datetime.utcnow(),
        "exec_time": 0,
        "error_msg": "",
    })
    return migrated


if __name__ == "__main__":
    migrated = migrate()
    print(f"migrated: {migrated}")
