import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import urlopen

from config.settings import settings
from app.database.mongodb import mongodb_conn
from app.database.minio_db import minio_conn
from app.document_pipeline.repository import DocumentRepository

RESOURCE_COLLECTION = "resource_report_eastmoney"
ODS_COLLECTION = "eastmoney_report"
DS_ID = "DS_REPORT_EASTMONEY"
TASK_ID = "TASK_DS_REPORT_EASTMONEY_0001"


def _ensure_ds_meta(db):
    db.get_collection("ds_basic_info").update_one(
        {"ds_id": DS_ID},
        {
            "$setOnInsert": {
                "ds_id": DS_ID,
                "name": "东方财富研报",
                "ds_type": "INTERNET",
                "data_category": "研报",
                "ds_source": "eastmoney",
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
                "task_name": "东方财富研报迁移",
                "access_mode": "FULL",
                "schedule_config": "manual",
                "storage_config": {"storage_type": "MONGO", "storage_addr": RESOURCE_COLLECTION},
                "is_valid": True,
                "create_time": datetime.utcnow(),
                "update_time": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def _download_pdf(pdf_url: str):
    if not pdf_url:
        return None
    with urlopen(pdf_url) as resp:
        data = resp.read()
    file_id = hashlib.sha256(data).hexdigest()
    filename = os.path.basename(urlparse(pdf_url).path) or f"{file_id}.pdf"
    object_name = minio_conn.generate_object_name("report", original_filename=filename, content=data)
    minio_path = minio_conn.upload_bytes(
        settings.MINIO_BUCKET_RAW,
        object_name,
        data,
        content_type="application/pdf",
        metadata={"source": "eastmoney"},
    )
    return {
        "file_id": file_id,
        "file_name": filename,
        "file_size": len(data),
        "minio_path": minio_path,
    }


def map_report_doc(src: dict):
    repo = DocumentRepository(db=None)
    doc = repo.build_resource_doc(
        resource_type="report",
        source="eastmoney",
        title=src.get("title"),
        content=src.get("content"),
        url=src.get("url"),
    )
    doc["extra_meta"] = {
        "author": src.get("author"),
        "institution_name": src.get("institution_name"),
        "channel": src.get("channel"),
        "publish_time": src.get("publish_time"),
        "pdf_url": src.get("pdf_url"),
    }
    return doc


def migrate(limit: int = 0):
    if not settings.ODS_MONGODB_URI or not settings.ODS_MONGODB_DATABASE:
        raise RuntimeError("ODS_MONGODB_URI/ODS_MONGODB_DATABASE 未配置")

    ods_db = mongodb_conn.connect_ods(settings.ODS_MONGODB_URI, settings.ODS_MONGODB_DATABASE)
    _ensure_ds_meta(mongodb_conn)

    cursor = ods_db[ODS_COLLECTION].find({})
    if limit:
        cursor = cursor.limit(limit)

    repo = DocumentRepository(db=mongodb_conn)
    migrated = 0
    for src in cursor:
        resource_doc = map_report_doc(src)
        resource_doc.update({
            "ds_id": DS_ID,
            "task_id": TASK_ID,
            "task_runtime_id": f"RECORD_{TASK_ID}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "publish_time": src.get("publish_time"),
            "process_batch_id": f"BATCH_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        })

        collection = mongodb_conn.get_collection(RESOURCE_COLLECTION)
        if collection.find_one({"content_hash": resource_doc["content_hash"]}):
            continue

        file_meta = None
        if src.get("pdf_url"):
            file_meta = _download_pdf(src.get("pdf_url"))
            if file_meta:
                mongodb_conn.get_collection("minio_file_index").update_one(
                    {"file_id": file_meta["file_id"]},
                    {
                        "$setOnInsert": {
                            "file_id": file_meta["file_id"],
                            "content_hash": file_meta["file_id"],
                            "ds_id": DS_ID,
                            "task_id": TASK_ID,
                            "record_id": resource_doc["task_runtime_id"],
                            "file_name": file_meta["file_name"],
                            "file_type": "PDF",
                            "minio_bucket": settings.MINIO_BUCKET_RAW,
                            "minio_path": file_meta["minio_path"],
                            "file_size": file_meta["file_size"],
                            "upload_time": datetime.utcnow(),
                            "is_valid": True,
                        }
                    },
                    upsert=True,
                )

        if file_meta:
            resource_doc["resource_file_id"] = file_meta["file_id"]

        collection.insert_one(resource_doc)

        inc_doc = repo.build_inc_document(
            resource_doc,
            resource_file_id=resource_doc.get("resource_file_id"),
            extra_meta=resource_doc.get("extra_meta"),
        )
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
