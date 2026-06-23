from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict
from datetime import datetime

router = APIRouter(prefix="/document-pipeline", tags=["文档管道"])

LEGACY_SOURCE_NEWS_COLLECTION = "news_pipeline_source_news"
LEGACY_REPORT_COLLECTION = "report_pipeline_reports"
LEGACY_NEWS_ENTITY_COLLECTION = "news_pipeline_entity_instances"
LEGACY_NEWS_STATEMENT_COLLECTION = "news_pipeline_statements"
DOC_TYPE_ALIASES = {
    "news": "news",
    "report": "report",
    "资讯": "news",
    "研报": "report",
}


def _list_collections(db, prefix: str):
    try:
        names = db.list_collection_names()
    except Exception:
        names = []
    return sorted([name for name in names if name.startswith(prefix)])


def _collection_exists(db, name: str) -> bool:
    try:
        return name in db.list_collection_names()
    except Exception:
        return False


def _ensure_db(conn):
    if conn._db is None:
        conn.connect()
    return conn._db


def _count_prefixed(db, prefix: str) -> int:
    total = 0
    for name in _list_collections(db, prefix):
        total += db.get_collection(name).count_documents({})
    return total


def _count_prefixed_by_status(db, prefix: str, statuses) -> int:
    if isinstance(statuses, str):
        statuses = [statuses]
    total = 0
    for name in _list_collections(db, prefix):
        total += db.get_collection(name).count_documents({"status": {"$in": statuses}})
    return total


def _count_legacy_by_status(db, collection_name: str, statuses) -> int:
    if isinstance(statuses, str):
        statuses = [statuses]
    return db.get_collection(collection_name).count_documents({
        "$or": [
            {"status": {"$in": statuses}},
            {"process_status": {"$in": statuses}},
        ]
    })


def _normalize_legacy_source(doc: Dict) -> Dict:
    return {
        "resource_doc_id": doc.get("resource_doc_id") or doc.get("doc_id") or str(doc.get("_id")),
        "title_raw": doc.get("title") or doc.get("title_raw"),
        "data_source": doc.get("source_name") or doc.get("source") or doc.get("data_source"),
        "url": doc.get("source_url") or doc.get("url"),
        "publish_time": doc.get("publish_time") or doc.get("crawl_time") or doc.get("created_at"),
        "status": doc.get("status") or doc.get("process_status"),
    }


def _legacy_statement_query(doc_type: Optional[str]) -> Dict:
    if doc_type:
        return {"context_scenario": doc_type}
    return {}


def _count_legacy_statements(db, doc_type: Optional[str]) -> int:
    return db.get_collection(LEGACY_NEWS_STATEMENT_COLLECTION).count_documents(
        _legacy_statement_query(doc_type)
    )


def _get_legacy_entity_ids_by_statements(db, doc_type: Optional[str]):
    pipeline = []
    query = _legacy_statement_query(doc_type)
    if query:
        pipeline.append({"$match": query})
    pipeline.extend([
        {"$project": {"ids": ["$subject_id", "$object_entity_id"]}},
        {"$unwind": "$ids"},
        {"$match": {"ids": {"$ne": None}}},
        {"$group": {"_id": "$ids"}},
    ])
    return [item.get("_id") for item in db.get_collection(LEGACY_NEWS_STATEMENT_COLLECTION).aggregate(pipeline)]


def _normalize_legacy_entity(doc: Dict) -> Dict:
    entity_id = doc.get("entity_id") or doc.get("_id")
    if entity_id is not None:
        entity_id = str(entity_id)
    return {
        "entity_id": entity_id,
        "class_id": doc.get("class_id") or doc.get("class"),
        "entity_category": doc.get("entity_category") or doc.get("category"),
        "name": doc.get("name") or doc.get("canonical_name"),
        "status": doc.get("status") or doc.get("state"),
    }


def _normalize_doc_type(doc_type: Optional[str]) -> Optional[str]:
    if not doc_type:
        return None
    doc_type = doc_type.strip()
    if not doc_type:
        return None
    return DOC_TYPE_ALIASES.get(doc_type) or DOC_TYPE_ALIASES.get(doc_type.lower()) or doc_type


def _build_doc_type_filter(doc_type: Optional[str]) -> Dict:
    if not doc_type:
        return {}
    return {"$or": [{"resource_type": doc_type}, {"doc_type": doc_type}]}


def _count_microcontent_by_doc_type(db, doc_type: str) -> int:
    doc_ids = [doc.get("doc_id") for doc in db.get_collection("inc_document").find(
        {"resource_type": doc_type},
        {"doc_id": 1},
    )]
    doc_ids = [doc_id for doc_id in doc_ids if doc_id]
    if not doc_ids:
        return 0
    return db.get_collection("inc_microcontent").count_documents({"doc_id": {"$in": doc_ids}})


def _get_doc_ids_by_doc_type(db, doc_type: str):
    doc_ids = [doc.get("doc_id") for doc in db.get_collection("inc_document").find(
        {"resource_type": doc_type},
        {"doc_id": 1},
    )]
    return [doc_id for doc_id in doc_ids if doc_id]


def _count_entities_by_doc_type(db, doc_type: str) -> int:
    pipeline = [
        {"$match": {"context_scenario": doc_type}},
        {"$project": {"ids": ["$subject_id", "$object_entity_id"]}},
        {"$unwind": "$ids"},
        {"$match": {"ids": {"$ne": None}}},
        {"$group": {"_id": "$ids"}},
        {"$count": "count"},
    ]
    result = list(db.get_collection("inc_statement").aggregate(pipeline))
    if not result:
        return 0
    return result[0].get("count", 0) or 0


@router.get("/stats")
async def stats(
    doc_type: Optional[str] = Query(default=None, description="文档类型过滤"),
    knowledge_scope: Optional[str] = Query(default=None, description="知识网络统计范围"),
):
    from app.database.mongodb import mongodb_conn
    from app.database.mysql_ontology_db import ontology_db
    from app.database.neo4j_db import neo4j_conn

    normalized_doc_type = _normalize_doc_type(doc_type)
    normalized_knowledge_scope = (knowledge_scope or "").strip().lower()
    knowledge_doc_type = None if normalized_knowledge_scope == "all" else normalized_doc_type
    raw_filter = _build_doc_type_filter(normalized_doc_type)

    raw_documents_count = mongodb_conn.get_collection("raw_documents").count_documents(raw_filter)
    if normalized_doc_type and normalized_doc_type != "news":
        crawled_count = 0
    else:
        crawled_count = mongodb_conn.get_collection("crawled_articles").count_documents({})
    ds_basic_info_count = mongodb_conn.get_collection("ds_basic_info").count_documents({})
    ds_access_task_count = mongodb_conn.get_collection("ds_access_task").count_documents({})
    ds_access_record_count = mongodb_conn.get_collection("ds_access_record").count_documents({})
    minio_file_index_count = mongodb_conn.get_collection("minio_file_index").count_documents({})
    if normalized_doc_type:
        inc_document_count = mongodb_conn.get_collection("inc_document").count_documents(
            {"resource_type": normalized_doc_type}
        )
        inc_microcontent_count = _count_microcontent_by_doc_type(mongodb_conn, normalized_doc_type)
    else:
        inc_document_count = mongodb_conn.get_collection("inc_document").count_documents({})
        inc_microcontent_count = mongodb_conn.get_collection("inc_microcontent").count_documents({})

    db = _ensure_db(mongodb_conn)
    source_news_count = 0
    source_report_count = 0
    pending_count = 0
    completed_count = 0
    if db:
        if not normalized_doc_type or normalized_doc_type == "news":
            source_news_count = _count_prefixed(db, "resource_news_")
            if source_news_count > 0:
                pending_count += _count_prefixed_by_status(db, "resource_news_", ["pending"])
                completed_count += _count_prefixed_by_status(db, "resource_news_", ["completed", "processed"])
            elif _collection_exists(db, LEGACY_SOURCE_NEWS_COLLECTION):
                source_news_count = db.get_collection(LEGACY_SOURCE_NEWS_COLLECTION).count_documents({})
                pending_count += _count_legacy_by_status(db, LEGACY_SOURCE_NEWS_COLLECTION, ["pending"])
                completed_count += _count_legacy_by_status(db, LEGACY_SOURCE_NEWS_COLLECTION, ["completed", "processed"])
        if not normalized_doc_type or normalized_doc_type == "report":
            source_report_count = _count_prefixed(db, "resource_report_")
            if source_report_count > 0:
                pending_count += _count_prefixed_by_status(db, "resource_report_", ["pending"])
                completed_count += _count_prefixed_by_status(db, "resource_report_", ["completed", "processed"])
            elif _collection_exists(db, LEGACY_REPORT_COLLECTION):
                source_report_count = db.get_collection(LEGACY_REPORT_COLLECTION).count_documents({})
                pending_count += _count_legacy_by_status(db, LEGACY_REPORT_COLLECTION, ["pending"])
                completed_count += _count_legacy_by_status(db, LEGACY_REPORT_COLLECTION, ["completed", "processed"])

    if knowledge_doc_type:
        knowledge_entities = _count_entities_by_doc_type(mongodb_conn, knowledge_doc_type)
        knowledge_statements = mongodb_conn.get_collection("inc_statement").count_documents(
            {"context_scenario": knowledge_doc_type}
        )
        knowledge_contexts = mongodb_conn.get_collection("inc_context").count_documents(
            {"context_scenario": knowledge_doc_type}
        )
        if knowledge_doc_type == "news" and db:
            if knowledge_statements == 0 and _collection_exists(db, LEGACY_NEWS_STATEMENT_COLLECTION):
                knowledge_statements = _count_legacy_statements(db, knowledge_doc_type)
            if knowledge_entities == 0 and _collection_exists(db, LEGACY_NEWS_STATEMENT_COLLECTION):
                legacy_entity_ids = _get_legacy_entity_ids_by_statements(db, knowledge_doc_type)
                knowledge_entities = len([entity_id for entity_id in legacy_entity_ids if entity_id])
                if knowledge_entities == 0 and _collection_exists(db, LEGACY_NEWS_ENTITY_COLLECTION):
                    knowledge_entities = db.get_collection(LEGACY_NEWS_ENTITY_COLLECTION).count_documents({})
    else:
        knowledge_entities = mongodb_conn.get_collection("entity_instances").count_documents({})
        if knowledge_entities == 0:
            knowledge_entities = mongodb_conn.get_collection("canonical_entities").count_documents({})
        knowledge_statements = mongodb_conn.get_collection("inc_statement").count_documents({})
        knowledge_contexts = mongodb_conn.get_collection("inc_context").count_documents({})

    if knowledge_doc_type:
        knowledge_micro_documents = _count_microcontent_by_doc_type(mongodb_conn, knowledge_doc_type)
    else:
        knowledge_micro_documents = mongodb_conn.get_collection("inc_microcontent").count_documents({})

    # 本体模型（MySQL）
    ontology_counts = {
        "total_classes": 0,
        "total_properties": 0,
        "total_relations": 0,
        "total_axioms": 0,
        "total_versions": 0,
    }
    try:
        ontology_db.connect()
        ontology_counts["total_classes"] = len(ontology_db.get_classes())
        ontology_counts["total_properties"] = len(ontology_db.get_properties())
        ontology_counts["total_relations"] = len(ontology_db.get_relations())
        ontology_counts["total_axioms"] = len(ontology_db.get_axioms())
        # 版本表未独立建表，暂以本体元信息是否存在作为版本数
        ontology_counts["total_versions"] = 1 if ontology_db.get_ontology_meta() else 0
    except Exception:
        pass

    # 图谱库（Neo4j）
    graph_nodes = 0
    graph_relations = 0
    try:
        neo4j_conn.connect()
        nodes = neo4j_conn.execute_query("MATCH (n) RETURN count(n) AS c")
        rels = neo4j_conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS c")
        if nodes:
            graph_nodes = nodes[0].get("c", 0) or 0
        if rels:
            graph_relations = rels[0].get("c", 0) or 0
    except Exception:
        pass

    return {
        "raw_layer": {
            "raw_documents": raw_documents_count,
            "crawled_articles": crawled_count,
        },
        "resource_layer": {
            "ds_basic_info": ds_basic_info_count,
            "ds_access_task": ds_access_task_count,
            "ds_access_record": ds_access_record_count,
            "minio_file_index": minio_file_index_count,
            "source_news": source_news_count,
            "source_report": source_report_count,
            "inc_document": inc_document_count,
            "inc_microcontent": inc_microcontent_count,
            "pending": pending_count,
            "completed": completed_count,
        },
        "ontology_layer": ontology_counts,
        "knowledge_layer": {
            "entities": knowledge_entities,
            "statements": knowledge_statements,
            "contexts": knowledge_contexts,
            "micro_documents": knowledge_micro_documents,
        },
        "graph_layer": {"nodes": graph_nodes, "relations": graph_relations},
        "vector_layer": {"entity_vectors": knowledge_entities, "document_vectors": inc_document_count},
        "warehouse_layer": {"indicators": 0, "indicator_mappings": 0, "entity_mappings": 0},
    }


@router.get("/records")
async def records(
    layer: str = Query("", description="层级标识"),
    limit: int = 20,
    offset: int = 0,
    doc_type: Optional[str] = Query(default=None, description="文档类型过滤"),
):
    from app.database.mongodb import mongodb_conn

    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    normalized_doc_type = _normalize_doc_type(doc_type)
    doc_type_filter = _build_doc_type_filter(normalized_doc_type)

    def _serialize_value(value):
        if hasattr(value, "iso_format"):
            return value.iso_format()
        if isinstance(value, dict):
            return {k: _serialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_serialize_value(v) for v in value]
        return value

    mongo_layers = {
        "raw.raw_documents": {
            "collection": "raw_documents",
            "fields": ["doc_id", "doc_type", "title", "url", "publish_time", "crawl_time", "status"],
            "sort": [("publish_time", -1), ("crawl_time", -1)],
        },
        "raw.crawled_articles": {
            "collection": "crawled_articles",
            "fields": ["doc_id", "title", "source", "url", "publish_time", "crawled_at", "process_status"],
            "sort": [("crawled_at", -1)],
        },
        "resource.ds_basic_info": {
            "collection": "ds_basic_info",
            "fields": ["ds_id", "name", "ds_type", "data_category", "ds_source", "is_valid"],
            "sort": [("update_time", -1)],
        },
        "resource.ds_access_task": {
            "collection": "ds_access_task",
            "fields": ["task_id", "ds_id", "task_name", "access_mode", "schedule_config"],
            "sort": [("update_time", -1)],
        },
        "resource.ds_access_record": {
            "collection": "ds_access_record",
            "fields": ["record_id", "task_id", "ds_id", "exec_status", "total_count", "start_time"],
            "sort": [("start_time", -1)],
        },
        "resource.minio_file_index": {
            "collection": "minio_file_index",
            "fields": ["file_id", "file_name", "file_type", "minio_bucket", "minio_path", "file_size"],
            "sort": [("upload_time", -1)],
        },
        "resource.inc_document": {
            "collection": "inc_document",
            "fields": ["doc_id", "title", "summary", "resource_type", "data_source", "publish_time"],
            "sort": [("publish_time", -1)],
        },
        "resource.inc_microcontent": {
            "collection": "inc_microcontent",
            "fields": ["microcontent_id", "doc_id", "block_type", "block", "created_at"],
            "sort": [("created_at", -1)],
        },
        "knowledge.entities": {
            "collection": "entity_instances",
            "fields": ["entity_id", "class_id", "entity_category", "name", "status"],
            "sort": [("created_at", -1)],
        },
        "knowledge.statements": {
            "collection": "inc_statement",
            "fields": ["statement_id", "subject_id", "predicate_id", "object_type", "confidence"],
            "sort": [("created_at", -1)],
        },
        "knowledge.contexts": {
            "collection": "inc_context",
            "fields": ["context_id", "context_type", "begin_time", "end_time", "doc_id"],
            "sort": [("created_at", -1)],
        },
    }

    if layer == "knowledge.entities":
        collection = mongodb_conn.get_collection("entity_instances")
        if normalized_doc_type:
            pipeline = [
                {"$match": {"context_scenario": normalized_doc_type}},
                {"$project": {"ids": ["$subject_id", "$object_entity_id"]}},
                {"$unwind": "$ids"},
                {"$match": {"ids": {"$ne": None}}},
                {"$group": {"_id": "$ids"}},
            ]
            entity_ids = [item.get("_id") for item in mongodb_conn.get_collection("inc_statement").aggregate(pipeline)]
            entity_ids = [entity_id for entity_id in entity_ids if entity_id is not None]
            total = len(entity_ids)
            if total == 0 and normalized_doc_type == "news":
                db = _ensure_db(mongodb_conn)
                if db and _collection_exists(db, LEGACY_NEWS_STATEMENT_COLLECTION):
                    legacy_entity_ids = _get_legacy_entity_ids_by_statements(db, normalized_doc_type)
                    legacy_entity_ids = [entity_id for entity_id in legacy_entity_ids if entity_id is not None]
                    if legacy_entity_ids:
                        total = len(legacy_entity_ids)
                        page_ids = legacy_entity_ids[offset: offset + limit]
                        legacy_collection = mongodb_conn.get_collection(LEGACY_NEWS_ENTITY_COLLECTION)
                        cursor = legacy_collection.find({"_id": {"$in": page_ids}})
                        doc_map = {doc.get("_id"): doc for doc in cursor}
                        data = []
                        for entity_id in page_ids:
                            doc = doc_map.get(entity_id)
                            if not doc:
                                continue
                            data.append(_normalize_legacy_entity(doc))
                        data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
                        fields = ["entity_id", "class_id", "entity_category", "name", "status"]
                        return {"layer": layer, "fields": fields, "data": data, "total": total}

                if db and _collection_exists(db, LEGACY_NEWS_ENTITY_COLLECTION):
                    legacy_collection = mongodb_conn.get_collection(LEGACY_NEWS_ENTITY_COLLECTION)
                    total = legacy_collection.count_documents({})
                    cursor = legacy_collection.find({}).skip(offset).limit(limit)
                    data = [_normalize_legacy_entity(doc) for doc in cursor]
                    data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
                    fields = ["entity_id", "class_id", "entity_category", "name", "status"]
                    return {"layer": layer, "fields": fields, "data": data, "total": total}

            if total == 0:
                return {"layer": layer, "fields": ["entity_id", "class_id", "entity_category", "name", "status"], "data": [], "total": 0}
            entity_ids = sorted([str(entity_id) for entity_id in entity_ids])
            page_ids = entity_ids[offset: offset + limit]
            cursor = collection.find({"_id": {"$in": page_ids}})
            doc_map = {}
            for doc in cursor:
                doc_map[str(doc.get("_id"))] = doc
            data = []
            for entity_id in page_ids:
                doc = doc_map.get(entity_id)
                if not doc:
                    continue
                doc = dict(doc)
                doc["entity_id"] = str(doc.get("_id"))
                doc.pop("_id", None)
                data.append(doc)
            data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
            fields = ["entity_id", "class_id", "entity_category", "name", "status"]
            return {"layer": layer, "fields": fields, "data": data, "total": total}

        total = collection.count_documents({})
        if total == 0:
            fallback = mongodb_conn.get_collection("canonical_entities")
            total = fallback.count_documents({})
            fields = ["entity_id", "entity_type", "name", "reference_count", "current_momentum"]
            cursor = fallback.find({}, {"_id": 1, "type": 1, "names": 1, "reference_count": 1, "current_momentum": 1}) \
                .skip(offset).limit(limit)
            data = []
            for doc in cursor:
                name = None
                if isinstance(doc.get("names"), list) and doc.get("names"):
                    name = doc.get("names")[0]
                data.append({
                    "entity_id": str(doc.get("_id")),
                    "entity_type": doc.get("type"),
                    "name": name,
                    "reference_count": doc.get("reference_count", 0),
                    "current_momentum": doc.get("current_momentum", 0.0),
                })
            data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
            return {"layer": layer, "fields": fields, "data": data, "total": total}

    if layer == "knowledge.statements" and normalized_doc_type == "news":
        collection = mongodb_conn.get_collection("inc_statement")
        query = {"context_scenario": normalized_doc_type}
        total = collection.count_documents(query)
        if total == 0:
            db = _ensure_db(mongodb_conn)
            if db and _collection_exists(db, LEGACY_NEWS_STATEMENT_COLLECTION):
                legacy_collection = mongodb_conn.get_collection(LEGACY_NEWS_STATEMENT_COLLECTION)
                legacy_query = _legacy_statement_query(normalized_doc_type)
                total = legacy_collection.count_documents(legacy_query)
                cursor = legacy_collection.find(legacy_query).sort([("created_at", -1)]).skip(offset).limit(limit)
                data = []
                for doc in cursor:
                    doc = dict(doc)
                    doc["id"] = str(doc.get("_id"))
                    doc.pop("_id", None)
                    data.append(doc)
                fields = []
                for item in data:
                    for key in item.keys():
                        if key not in fields:
                            fields.append(key)
                data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
                return {"layer": layer, "fields": fields, "data": data, "total": total}

    if layer in ("resource.source_news", "resource.source_report"):
        if normalized_doc_type:
            if layer == "resource.source_news" and normalized_doc_type != "news":
                return {"layer": layer, "fields": ["resource_doc_id", "title_raw", "data_source", "url", "publish_time", "status"], "data": [], "total": 0}
            if layer == "resource.source_report" and normalized_doc_type != "report":
                return {"layer": layer, "fields": ["resource_doc_id", "title_raw", "data_source", "url", "publish_time", "status"], "data": [], "total": 0}
        prefix = "resource_news_" if layer == "resource.source_news" else "resource_report_"
        db = _ensure_db(mongodb_conn)
        collections = _list_collections(db, prefix) if db else []
        fields = ["resource_doc_id", "title_raw", "data_source", "url", "publish_time", "status"]
        data = []
        if collections:
            for name in collections:
                collection = mongodb_conn.get_collection(name)
                projection = {field: 1 for field in fields}
                projection["_id"] = 1
                cursor = collection.find({}, projection).limit(limit)
                for doc in cursor:
                    doc = dict(doc)
                    doc["id"] = str(doc.get("_id"))
                    doc.pop("_id", None)
                    data.append(doc)
                    if len(data) >= limit:
                        break
                if len(data) >= limit:
                    break
            data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
            return {"layer": layer, "fields": fields, "data": data, "total": len(data)}

        legacy_collection = LEGACY_SOURCE_NEWS_COLLECTION if layer == "resource.source_news" else LEGACY_REPORT_COLLECTION
        if db and _collection_exists(db, legacy_collection):
            collection = mongodb_conn.get_collection(legacy_collection)
            cursor = collection.find({}, {"_id": 1, "title": 1, "title_raw": 1, "source_name": 1, "source": 1, "data_source": 1, "source_url": 1, "url": 1, "publish_time": 1, "crawl_time": 1, "created_at": 1, "status": 1, "process_status": 1}).limit(limit)
            for doc in cursor:
                normalized = _normalize_legacy_source(doc)
                normalized["id"] = str(doc.get("_id"))
                data.append(normalized)
            data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
            return {"layer": layer, "fields": fields, "data": data, "total": len(data)}

        return {"layer": layer, "fields": fields, "data": [], "total": 0}

    if layer in mongo_layers:
        cfg = mongo_layers[layer]
        collection = mongodb_conn.get_collection(cfg["collection"])
        projection = {field: 1 for field in cfg["fields"]}
        projection["_id"] = 1
        query = {}
        if normalized_doc_type:
            if layer == "raw.raw_documents":
                query = doc_type_filter
            elif layer == "raw.crawled_articles":
                if normalized_doc_type != "news":
                    return {"layer": layer, "fields": cfg["fields"], "data": [], "total": 0}
            elif layer == "resource.inc_document":
                query = {"resource_type": normalized_doc_type}
            elif layer == "resource.inc_microcontent":
                doc_ids = _get_doc_ids_by_doc_type(mongodb_conn, normalized_doc_type)
                if not doc_ids:
                    return {"layer": layer, "fields": cfg["fields"], "data": [], "total": 0}
                query = {"doc_id": {"$in": doc_ids}}
            elif layer in ("knowledge.statements", "knowledge.contexts"):
                query = {"context_scenario": normalized_doc_type}

        cursor = collection.find(query, projection).sort(cfg["sort"]).skip(offset).limit(limit)
        data = []
        for doc in cursor:
            doc = dict(doc)
            doc["id"] = str(doc.get("_id"))
            doc.pop("_id", None)
            data.append(doc)
        total = collection.count_documents(query)
        data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
        return {"layer": layer, "fields": cfg["fields"], "data": data, "total": total}

    if layer in ("knowledge.standard_document", "knowledge.micro_document"):
        collection_name = "inc_document" if layer == "knowledge.standard_document" else "inc_microcontent"
        collection = mongodb_conn.get_collection(collection_name)
        sort = [("publish_time", -1), ("created_at", -1), ("_id", -1)]
        query = {}
        if normalized_doc_type:
            if layer == "knowledge.standard_document":
                query = {"resource_type": normalized_doc_type}
            else:
                doc_ids = _get_doc_ids_by_doc_type(mongodb_conn, normalized_doc_type)
                if not doc_ids:
                    return {"layer": layer, "fields": [], "data": [], "total": 0}
                query = {"doc_id": {"$in": doc_ids}}
        cursor = collection.find(query).sort(sort).skip(offset).limit(limit)
        data = []
        for doc in cursor:
            doc = dict(doc)
            doc["id"] = str(doc.get("_id"))
            doc.pop("_id", None)
            if layer == "knowledge.micro_document" and "microcontent_id" in doc:
                doc["micro_document_id"] = doc.pop("microcontent_id")
            data.append(doc)
        total = collection.count_documents(query)
        fields = []
        for item in data:
            for key in item.keys():
                if key not in fields:
                    fields.append(key)
        data = [{k: _serialize_value(v) for k, v in item.items()} for item in data]
        return {"layer": layer, "fields": fields, "data": data, "total": total}

    if layer in ("vector.entity_vectors", "vector.document_vectors"):
        if layer == "vector.entity_vectors":
            fields = ["id", "entity_id", "embedding"]
        else:
            fields = ["id", "doc_id", "embedding"]
        return {"layer": layer, "fields": fields, "data": [], "total": 0}

    if layer in ("warehouse.indicators", "warehouse.indicator_mappings", "warehouse.entity_mappings"):
        if layer == "warehouse.indicators":
            fields = ["indicator_id", "indicator_name", "indicator_type", "calculation_formula", "data_source"]
        elif layer == "warehouse.indicator_mappings":
            fields = ["mapping_id", "indicator_id", "property_id", "mapping_rule"]
        else:
            fields = ["mapping_id", "entity_id", "warehouse_id", "entity_type"]
        return {"layer": layer, "fields": fields, "data": [], "total": 0}

    if layer.startswith("ontology."):
        from app.database.mysql_ontology_db import ontology_db

        def _slice(items):
            total_items = len(items)
            return items[offset: offset + limit], total_items

        if layer == "ontology.classes":
            items = ontology_db.get_classes()
        elif layer == "ontology.properties":
            items = ontology_db.get_properties()
        elif layer == "ontology.relations":
            items = ontology_db.get_relations()
        elif layer == "ontology.axioms":
            items = ontology_db.get_axioms(enabled_only=False)
        elif layer == "ontology.versions":
            meta = ontology_db.get_ontology_meta()
            items = [meta] if meta else []
        else:
            items = []

        page, total = _slice(items)
        data = [{k: _serialize_value(v) for k, v in item.items()} for item in page]
        fields = list(page[0].keys()) if page else []
        return {"layer": layer, "fields": fields, "data": data, "total": total}

    raise HTTPException(status_code=400, detail="invalid layer")


@router.get("/scenarios/collaboration")
async def scenario_collaboration(company: str):
    if not company:
        raise HTTPException(status_code=400, detail="company is required")
    return {"company": company, "relations": [], "total": 0}


@router.get("/scenarios/tech-match")
async def scenario_tech_match(keyword: str):
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")
    return {"keyword": keyword, "matched_elements": [], "matched_subjects": []}


@router.get("/scenarios/provenance")
async def scenario_provenance(title: str):
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    return {"title": title, "matched": False, "provenance": []}
