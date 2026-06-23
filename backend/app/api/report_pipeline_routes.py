"""
研报处理管道 API 路由
提供研报列表、创建、处理、知识抽取等功能
"""
from fastapi import APIRouter, Query, HTTPException, UploadFile, File
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel
import hashlib
import logging
import re

from app.database.mongodb import mongodb_conn
from app.nlp.llm import LLMProcessor
from app.services.graph_service import graph_service
from app.news_pipeline.constants import (
    ENTITY_CATEGORY_MAP,
    ENTITY_TYPE_MAP,
    ENTITY_CLASS_MAP,
    PREDICATE_MAP,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report-pipeline", tags=["研报处理管道"])

REPORT_COLLECTION = "report_pipeline_reports"
REPORT_ENTITY_COLLECTION = "entity_instances"
REPORT_STATEMENT_COLLECTION = "inc_statement"
REPORT_CONTEXT_COLLECTION = "inc_context"


class ReportCreateRequest(BaseModel):
    """研报创建请求"""
    title: str
    institution: Optional[str] = None
    analyst: Optional[str] = None
    industry: Optional[str] = None
    rating: Optional[str] = None
    publish_date: Optional[str] = None
    core_viewpoint: Optional[str] = None
    investment_advice: Optional[str] = None
    content: Optional[str] = None


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    limit: int = 10


class ReportPipelineService:
    """研报处理管道服务"""

    def __init__(self):
        self.db = mongodb_conn
        self.llm = LLMProcessor()

    def _generate_hash(self, value: str, length: int = 16) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:length]

    def _generate_doc_id(self, report: Dict[str, Any]) -> str:
        title = (report.get("title") or "").strip()
        institution = (report.get("institution") or "").strip()
        publish_date = report.get("publish_date") or ""
        key = f"report:{title}|{institution}|{publish_date}"
        return f"doc:{self._generate_hash(key, 12)}"

    def _generate_entity_id(self, class_id: str, name: str) -> str:
        key = f"{class_id}:{name}".lower().strip()
        return f"EN{self._generate_hash(key, 16)}"

    def _normalize_predicate(self, predicate_raw: Optional[str]) -> tuple:
        if not predicate_raw:
            return "rel:related_to", None
        if predicate_raw in PREDICATE_MAP:
            return PREDICATE_MAP[predicate_raw], predicate_raw
        if predicate_raw.startswith(("rel:", "prop:")):
            return predicate_raw, None
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", str(predicate_raw)).strip("_").lower()
        if not slug:
            slug = f"rel_{self._generate_hash(str(predicate_raw), 8)}"
        return f"rel:{slug}", predicate_raw

    def list_reports(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
        """获取研报列表"""
        collection = self.db.get_collection(REPORT_COLLECTION)
        query = {}
        if status:
            query["process_status"] = status

        total = collection.count_documents(query)
        cursor = collection.find(query).sort([("created_at", -1)]).skip(offset).limit(limit)

        data = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            data.append(doc)

        return {"data": data, "total": total}

    def create_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """创建研报记录"""
        doc_id = self._generate_doc_id(payload)
        now = datetime.utcnow()

        report_doc = {
            "doc_id": doc_id,
            "title": payload.get("title"),
            "institution": payload.get("institution"),
            "analyst": payload.get("analyst"),
            "industry": payload.get("industry"),
            "rating": payload.get("rating"),
            "publish_date": payload.get("publish_date"),
            "core_viewpoint": payload.get("core_viewpoint"),
            "investment_advice": payload.get("investment_advice"),
            "content": payload.get("content") or payload.get("core_viewpoint") or "",
            "process_status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        collection = self.db.get_collection(REPORT_COLLECTION)
        result = collection.insert_one(report_doc)
        report_doc["id"] = str(result.inserted_id)
        report_doc.pop("_id", None)

        return report_doc

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """获取单个研报"""
        from bson import ObjectId
        if not ObjectId.is_valid(report_id):
            return None
        collection = self.db.get_collection(REPORT_COLLECTION)
        doc = collection.find_one({"_id": ObjectId(report_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    def process_report(self, report_id: str) -> Dict[str, Any]:
        """处理单个研报，执行知识抽取"""
        report = self.get_report(report_id)
        if not report:
            return {"success": False, "error": "report_not_found"}

        if report.get("process_status") == "processing":
            return {"success": False, "error": "already_processing"}

        # 更新状态为处理中
        self._update_report(report_id, {"process_status": "processing"})

        try:
            # 构建待分析内容
            content = self._build_content(report)

            # 调用 LLM 进行实体和关系抽取
            extraction = self._extract_knowledge(content)

            # 创建实体
            entity_map = self._create_entities(extraction.get("entities", {}))

            # 创建文档实体
            document_entity_id = self._create_document_entity(report)

            # 创建陈述
            statements_created = self._create_statements(
                report_id,
                report,
                extraction,
                entity_map,
                document_entity_id,
            )

            # 创建上下文
            contexts_created = self._create_contexts(report, statements_created)

            # 同步到图谱
            self._sync_graph(extraction.get("entities", {}), extraction.get("relations", []))

            # 提取观点和建议
            viewpoints = self._extract_viewpoints(content)
            recommendations = self._extract_recommendations(report)
            predictions = self._extract_predictions(content)

            process_result = {
                "entities": sum(len(v) for v in extraction.get("entities", {}).values()),
                "relations": len(extraction.get("relations", [])),
                "statements": statements_created,
                "contexts": contexts_created,
                "viewpoints": len(viewpoints),
                "recommendations": len(recommendations),
                "predictions": len(predictions),
                "model": extraction.get("model"),
            }

            # 更新研报状态
            self._update_report(report_id, {
                "process_status": "completed",
                "process_result": process_result,
                "viewpoints": viewpoints,
                "recommendations": recommendations,
                "predictions": predictions,
                "processed_at": datetime.utcnow(),
            })

            return {"success": True, "report_id": report_id, "process_result": process_result}

        except Exception as e:
            logger.error(f"研报处理失败: {e}", exc_info=True)
            self._update_report(report_id, {"process_status": "failed", "error": str(e)})
            return {"success": False, "error": str(e)}

    def _update_report(self, report_id: str, update_fields: Dict[str, Any]):
        """更新研报"""
        from bson import ObjectId
        if not ObjectId.is_valid(report_id):
            return
        collection = self.db.get_collection(REPORT_COLLECTION)
        update_fields["updated_at"] = datetime.utcnow()
        collection.update_one({"_id": ObjectId(report_id)}, {"$set": update_fields})

    def _build_content(self, report: Dict[str, Any]) -> str:
        """构建待分析内容"""
        parts = []
        if report.get("title"):
            parts.append(f"标题：{report['title']}")
        if report.get("institution"):
            parts.append(f"机构：{report['institution']}")
        if report.get("analyst"):
            parts.append(f"分析师：{report['analyst']}")
        if report.get("industry"):
            parts.append(f"行业：{report['industry']}")
        if report.get("rating"):
            parts.append(f"评级：{report['rating']}")
        if report.get("core_viewpoint"):
            parts.append(f"核心观点：{report['core_viewpoint']}")
        if report.get("investment_advice"):
            parts.append(f"投资建议：{report['investment_advice']}")
        if report.get("content"):
            parts.append(f"正文：{report['content']}")
        return "\n".join(parts)

    def _extract_knowledge(self, content: str) -> Dict[str, Any]:
        """调用 LLM 进行知识抽取"""
        if not content:
            return {"entities": {}, "relations": [], "summary": ""}

        result = self.llm.analyze_industry_chain(content)
        return {
            "entities": result.get("entities", {}),
            "relations": result.get("relations", []),
            "summary": result.get("summary"),
            "model": settings.OPENAI_MODEL,
        }

    def _create_document_entity(self, report: Dict[str, Any]) -> str:
        """创建文档实体"""
        doc_id = report.get("doc_id") or self._generate_doc_id(report)
        entity_id = self._generate_entity_id("ont:Document", doc_id)
        entity_doc = {
            "_id": entity_id,
            "entity_id": entity_id,
            "entity_category": "document",
            "entity_type": "report",
            "class_id": "ont:Document",
            "canonical_name": report.get("title") or "未命名研报",
            "name": report.get("title") or "未命名研报",
            "status": "active",
            "metadata": {
                "doc_id": doc_id,
                "institution": report.get("institution"),
                "analyst": report.get("analyst"),
                "industry": report.get("industry"),
                "rating": report.get("rating"),
                "publish_date": report.get("publish_date"),
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        collection = self.db.get_collection(REPORT_ENTITY_COLLECTION)
        collection.update_one(
            {"_id": entity_id},
            {"$setOnInsert": entity_doc},
            upsert=True,
        )
        return entity_id

    def _create_entities(self, entities: Dict[str, List[str]]) -> Dict[str, str]:
        """创建实体并返回名称到ID的映射"""
        entity_map: Dict[str, str] = {}
        collection = self.db.get_collection(REPORT_ENTITY_COLLECTION)

        for category, items in entities.items():
            entity_category = ENTITY_CATEGORY_MAP.get(category)
            entity_type = ENTITY_TYPE_MAP.get(category)
            class_id = ENTITY_CLASS_MAP.get(category) or "ont:Entity"
            if not entity_category:
                continue

            for name in items:
                if not name:
                    continue
                entity_id = self._generate_entity_id(class_id, name)
                entity_doc = {
                    "_id": entity_id,
                    "entity_id": entity_id,
                    "entity_category": entity_category,
                    "entity_type": entity_type or category,
                    "class_id": class_id,
                    "canonical_name": name,
                    "name": name,
                    "status": "active",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                collection.update_one(
                    {"_id": entity_id},
                    {"$setOnInsert": entity_doc},
                    upsert=True,
                )
                entity_map[name] = entity_id

        return entity_map

    def _create_statements(
        self,
        report_id: str,
        report: Dict[str, Any],
        extraction: Dict[str, Any],
        entity_map: Dict[str, str],
        document_entity_id: str,
    ) -> int:
        """创建陈述"""
        relations = extraction.get("relations", [])
        collection = self.db.get_collection(REPORT_STATEMENT_COLLECTION)
        count = 0

        for relation in relations:
            subject_name = relation.get("subject")
            object_name = relation.get("object")
            subject_id = entity_map.get(subject_name)
            object_id = entity_map.get(object_name)
            if not subject_id or not object_id:
                continue

            predicate_raw = relation.get("relation") or relation.get("predicate") or "related_to"
            predicate_id, predicate_label = self._normalize_predicate(predicate_raw)

            statement_hash = self._generate_hash(f"{subject_id}|{predicate_id}|{object_id}|{report.get('doc_id')}")
            statement_id = f"ST{statement_hash[:16]}"

            statement_doc = {
                "statement_id": statement_id,
                "statement_hash": statement_hash,
                "subject_id": subject_id,
                "predicate_id": predicate_id,
                "predicate_label": predicate_label,
                "object_type": "entity_ref",
                "object_entity_id": object_id,
                "doc_id": report.get("doc_id"),
                "source_report_id": report_id,
                "evidence_type": "extraction",
                "evidence_text": relation.get("evidence"),
                "extraction_method": "llm_extraction",
                "extraction_model": extraction.get("model"),
                "context_time_value": report.get("publish_date"),
                "context_source_id": report.get("institution"),
                "context_scenario": "report",
                "audit_status": "pending",
                "is_current": True,
                "status": "validated",
                "confidence": relation.get("confidence", 0.8),
                "source_document_id": document_entity_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            collection.update_one(
                {"statement_id": statement_id},
                {"$setOnInsert": statement_doc},
                upsert=True,
            )
            count += 1

        return count

    def _create_contexts(self, report: Dict[str, Any], statement_count: int) -> int:
        """创建上下文"""
        if statement_count == 0:
            return 0

        collection = self.db.get_collection(REPORT_CONTEXT_COLLECTION)
        doc_id = report.get("doc_id")
        context_id = f"KC{self._generate_hash(doc_id, 16)}"

        context_doc = {
            "context_id": context_id,
            "context_type": "document",
            "begin_time": report.get("publish_date"),
            "end_time": None,
            "doc_id": doc_id,
            "context_source_id": report.get("institution"),
            "context_scenario": "report",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        collection.update_one(
            {"context_id": context_id},
            {"$setOnInsert": context_doc},
            upsert=True,
        )
        return 1

    def _sync_graph(self, entities: Dict[str, List[str]], relations: List[Dict[str, Any]]):
        """同步到图谱"""
        if not entities and not relations:
            return
        try:
            structured_entities: List[Dict[str, Any]] = []
            name_to_id: Dict[str, str] = {}

            for category, items in entities.items():
                entity_type = ENTITY_TYPE_MAP.get(category) or category
                class_id = ENTITY_CLASS_MAP.get(category) or "ont:Entity"
                for name in items:
                    entity_id = self._generate_entity_id(class_id, name)
                    name_to_id[name] = entity_id
                    structured_entities.append({
                        "entity_id": entity_id,
                        "name": name,
                        "type": entity_type,
                        "confidence": 0.9,
                    })

            structured_relations: List[Dict[str, Any]] = []
            for relation in relations:
                subject_name = relation.get("subject")
                object_name = relation.get("object")
                subject_id = name_to_id.get(subject_name)
                object_id = name_to_id.get(object_name)
                if not subject_id or not object_id:
                    continue
                predicate_id, predicate_label = self._normalize_predicate(
                    relation.get("relation") or relation.get("predicate")
                )
                structured_relations.append({
                    "subject_id": subject_id,
                    "object_id": object_id,
                    "predicate_id": predicate_id,
                    "label": predicate_label,
                    "confidence": relation.get("confidence", 0.9),
                })

            if structured_entities or structured_relations:
                graph_service.save_structured_data(structured_entities, structured_relations)
            else:
                graph_service.save_analyzed_data(entities, relations)
        except Exception as exc:
            logger.warning(f"图谱同步失败: {exc}")

    def _extract_viewpoints(self, content: str) -> List[Dict[str, Any]]:
        """提取核心观点"""
        viewpoints = []
        if not content or not self.llm.client:
            return viewpoints

        try:
            prompt = f"""
请从以下研报内容中提取核心观点，返回JSON数组格式：
{content[:3000]}

要求：
- 每个观点包含 content（观点内容）和 confidence（置信度0-1）
- 最多提取5个核心观点
只返回JSON数组。
"""
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "你是研报分析助手，只返回JSON数组。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result
            if result.endswith("```"):
                result = result.rsplit("\n", 1)[0] if "\n" in result else result
            result = result.strip()
            import json
            viewpoints = json.loads(result)
        except Exception as e:
            logger.warning(f"观点提取失败: {e}")

        return viewpoints

    def _extract_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取投资建议"""
        recommendations = []
        if report.get("rating"):
            recommendations.append({
                "target": report.get("title", "").split("：")[0] if "：" in report.get("title", "") else None,
                "rating": report.get("rating"),
                "target_price": None,
            })
        return recommendations

    def _extract_predictions(self, content: str) -> List[Dict[str, Any]]:
        """提取指标预测"""
        predictions = []
        if not content or not self.llm.client:
            return predictions

        try:
            prompt = f"""
请从以下研报内容中提取指标预测，返回JSON数组格式：
{content[:3000]}

要求：
- 每个预测包含 indicator（指标名）、value（预测值）、period（时间周期）
- 最多提取5个指标预测
只返回JSON数组。
"""
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "你是研报分析助手，只返回JSON数组。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result
            if result.endswith("```"):
                result = result.rsplit("\n", 1)[0] if "\n" in result else result
            result = result.strip()
            import json
            predictions = json.loads(result)
        except Exception as e:
            logger.warning(f"指标预测提取失败: {e}")

        return predictions

    def get_knowledge(self, report_id: str) -> Dict[str, Any]:
        """获取研报抽取的知识"""
        report = self.get_report(report_id)
        if not report:
            return {"entities": [], "statements": [], "viewpoints": [], "recommendations": [], "predictions": []}

        # 获取相关陈述
        doc_id = report.get("doc_id")
        statements = []
        if doc_id:
            stmt_collection = self.db.get_collection(REPORT_STATEMENT_COLLECTION)
            stmt_cursor = stmt_collection.find({"doc_id": doc_id})
            for stmt in stmt_cursor:
                stmt["id"] = str(stmt.pop("_id", None))
                statements.append(stmt)

        # 获取相关实体
        entity_ids = set()
        for stmt in statements:
            if stmt.get("subject_id"):
                entity_ids.add(stmt["subject_id"])
            if stmt.get("object_entity_id"):
                entity_ids.add(stmt["object_entity_id"])

        entities = []
        if entity_ids:
            entity_collection = self.db.get_collection(REPORT_ENTITY_COLLECTION)
            entity_cursor = entity_collection.find({"_id": {"$in": list(entity_ids)}})
            for entity in entity_cursor:
                entities.append({
                    "id": str(entity.get("_id")),
                    "name": entity.get("name") or entity.get("canonical_name"),
                    "type": entity.get("entity_type"),
                })

        return {
            "entities": entities,
            "statements": statements,
            "viewpoints": report.get("viewpoints", []),
            "recommendations": report.get("recommendations", []),
            "predictions": report.get("predictions", []),
        }

    def batch_process(self, limit: int = 10) -> Dict[str, Any]:
        """批量处理待处理研报"""
        limit = min(max(limit, 1), 50)
        collection = self.db.get_collection(REPORT_COLLECTION)
        cursor = collection.find({"process_status": "pending"}).sort([("created_at", 1)]).limit(limit)

        queued = 0
        results = []
        for doc in cursor:
            report_id = str(doc.get("_id"))
            result = self.process_report(report_id)
            results.append({"report_id": report_id, "result": result})
            if result.get("success"):
                queued += 1

        return {"queued": queued, "total": len(results), "results": results}

    def get_stats(self) -> Dict[str, Any]:
        """获取研报统计"""
        collection = self.db.get_collection(REPORT_COLLECTION)
        total = collection.count_documents({})
        pending = collection.count_documents({"process_status": "pending"})
        completed = collection.count_documents({"process_status": "completed"})
        failed = collection.count_documents({"process_status": "failed"})

        # 统计抽取的知识
        stmt_collection = self.db.get_collection(REPORT_STATEMENT_COLLECTION)
        statements = stmt_collection.count_documents({"context_scenario": "report"})

        entity_collection = self.db.get_collection(REPORT_ENTITY_COLLECTION)
        entities = entity_collection.count_documents({"entity_type": "report"})

        # 统计观点和预测
        viewpoints = 0
        predictions = 0
        for doc in collection.find({"process_status": "completed"}, {"viewpoints": 1, "predictions": 1}):
            viewpoints += len(doc.get("viewpoints", []))
            predictions += len(doc.get("predictions", []))

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "report_layer": {
                "entities": entities,
                "statements": statements,
                "viewpoints": viewpoints,
                "predictions": predictions,
            },
        }


# 创建服务实例
report_pipeline_service = ReportPipelineService()


# ========== API 路由 ==========

@router.get("/list")
async def list_reports(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="状态筛选"),
):
    """获取研报列表"""
    return report_pipeline_service.list_reports(limit=limit, offset=offset, status=status)


@router.post("/create")
async def create_report(request: ReportCreateRequest):
    """创建研报记录"""
    return report_pipeline_service.create_report(request.model_dump())


@router.post("/upload")
async def upload_report(file: UploadFile = File(...)):
    """上传研报PDF"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    try:
        content = await file.read()
        # TODO: 实现PDF解析逻辑
        # 目前先创建一个待处理的研报记录
        report_doc = report_pipeline_service.create_report({
            "title": file.filename.replace(".pdf", ""),
            "content": f"[PDF文件待解析: {file.filename}]",
            "process_status": "pending",
        })
        return {"success": True, "report": report_doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/{report_id}")
async def process_report(report_id: str):
    """处理单个研报"""
    result = report_pipeline_service.process_report(report_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "处理失败"))
    return result


@router.post("/batch-process")
async def batch_process(request: BatchProcessRequest):
    """批量处理研报"""
    return report_pipeline_service.batch_process(request.limit)


@router.get("/knowledge/{report_id}")
async def get_knowledge(report_id: str):
    """获取研报抽取的知识"""
    return report_pipeline_service.get_knowledge(report_id)


@router.get("/detail/{report_id}")
async def get_detail(report_id: str):
    """获取研报详情"""
    report = report_pipeline_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="研报不存在")
    return report


@router.get("/stats")
async def get_stats():
    """获取研报统计"""
    return report_pipeline_service.get_stats()


@router.post("/import")
async def import_reports(limit: int = Query(default=50, ge=1, le=500)):
    """从ODS导入研报"""
    try:
        from app.database.mongodb import mongodb_conn
        from config.settings import settings

        if not settings.ODS_MONGODB_URI or not settings.ODS_MONGODB_DATABASE:
            raise HTTPException(status_code=400, detail="ODS_MONGODB_URI/ODS_MONGODB_DATABASE 未配置")

        ods_db = mongodb_conn.connect_ods(settings.ODS_MONGODB_URI, settings.ODS_MONGODB_DATABASE)
        cursor = ods_db["eastmoney_report"].find({}).limit(limit)

        imported = 0
        skipped = 0
        for src in cursor:
            # 检查是否已存在
            existing = mongodb_conn.get_collection(REPORT_COLLECTION).find_one({
                "title": src.get("title"),
                "institution": src.get("institution_name"),
            })
            if existing:
                skipped += 1
                continue

            report_pipeline_service.create_report({
                "title": src.get("title"),
                "institution": src.get("institution_name"),
                "analyst": src.get("author"),
                "industry": src.get("channel"),
                "content": src.get("content"),
                "publish_date": str(src.get("publish_time"))[:10] if src.get("publish_time") else None,
            })
            imported += 1

        return {"imported": imported, "skipped": skipped}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
