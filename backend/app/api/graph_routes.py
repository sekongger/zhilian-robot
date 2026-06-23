"""
API路由 - 图谱查询接口
"""
from fastapi import APIRouter, HTTPException, Query, Body
from app.models.schemas import GraphData, IndustryChainQuery, EntityTimelineResponse, MomentumTrend
from app.services.graph_service import graph_service
from app.analytics.momentum import momentum_engine
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


def _build_artifact_scoped_graph(company_name: str, artifact_id: str) -> Dict:
    mongo = _get_mongo_conn()
    entity_rows = mongo.find_many("entity_instances", query={"artifact_id": artifact_id}, limit=1000)
    statement_rows = mongo.find_many("inc_statement", query={"artifact_id": artifact_id}, limit=1000)

    entity_index = {
        str(item.get("entity_id") or item.get("_id") or ""): item
        for item in entity_rows
        if str(item.get("entity_id") or item.get("_id") or "").strip()
    }
    anchor_ids = {
        entity_id
        for entity_id, item in entity_index.items()
        if company_name in str(item.get("canonical_name") or item.get("name") or "")
    }
    if not anchor_ids:
        return _build_artifact_scoped_graph_from_batch(company_name, artifact_id)

    nodes = {}
    edges = []
    for row in statement_rows:
        subject_id = str(row.get("subject_id") or "").strip()
        object_id = str(row.get("object_entity_id") or "").strip()
        if subject_id not in anchor_ids and object_id not in anchor_ids:
            continue
        subject = entity_index.get(subject_id) or {}
        obj = entity_index.get(object_id) or {}
        if subject_id and subject_id not in nodes:
            nodes[subject_id] = {
                "id": subject_id,
                "name": str(subject.get("canonical_name") or subject.get("name") or subject_id),
                "type": str(subject.get("entity_type") or "entity"),
            }
        if object_id and object_id not in nodes:
            nodes[object_id] = {
                "id": object_id,
                "name": str(obj.get("canonical_name") or obj.get("name") or object_id),
                "type": str(obj.get("entity_type") or "entity"),
            }
        if subject_id and object_id:
            edges.append(
                {
                    "source": subject_id,
                    "target": object_id,
                    "relation": str(row.get("predicate_label") or row.get("predicate_id") or "相关"),
                    "confidence": float(row.get("confidence") or 0.0),
                }
            )

    return {"nodes": list(nodes.values()), "edges": edges}


_PREVIEW_COMPANY_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9·]{2,24}(?:机器人|车企|科技|智能|集团|股份|公司|厂|研究院))"
)
_COMPANY_SPLIT_PATTERN = re.compile(r"[与和及、/]")
_COMPANY_TRIM_SUFFIXES = (
    "合作",
    "推进",
    "布局",
    "研究",
    "研发",
    "发布",
    "推出",
    "生产",
    "打造",
    "具身智能",
    "控制器",
)
_COMPANY_SPLIT_MARKERS = ("推进", "合作", "布局", "研究", "研发", "发布", "推出", "打造", "生产")
_COMPANY_IGNORE_NAMES = {"机器人", "具身智能", "控制器"}
_COMPANY_INVALID_MARKERS = ("目标是", "将", "从", "到", "配备", "支持", "提升", "实现", "用于", "可以")


def _bridge_batches_dir() -> Path:
    from app.openspg_demo.bridge_runner import BridgeRunner

    return BridgeRunner().batches_dir


def _artifact_bridge_batch_records(artifact_id: str, limit: int = 100) -> List[Dict]:
    mongo = _get_mongo_conn()
    artifact = mongo.find_one("knowledge_artifacts", {"artifact_id": artifact_id}) or {}
    bridge_run_id = str(artifact.get("bridge_run_id") or "").strip()
    if not bridge_run_id:
        return []
    batch_file = _bridge_batches_dir() / f"{bridge_run_id}.jsonl"
    if not batch_file.exists():
        return []
    rows = []
    try:
        for line in batch_file.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
            if len(rows) >= limit:
                break
    except Exception:
        return []
    return rows


def _is_queryable_company_name(name: str) -> bool:
    text = str(name or "").strip()
    if len(text) < 2 or text in _COMPANY_IGNORE_NAMES:
        return False
    if len(text) > 12 and not any(text.endswith(suffix) for suffix in ("科技", "集团", "股份", "公司", "机器人", "车企", "研究院", "厂")):
        return False
    if any(marker in text for marker in _COMPANY_INVALID_MARKERS):
        return False
    return True


def _extract_batch_companies(record: Dict) -> List[str]:
    text = f"{record.get('title') or ''} {record.get('content') or record.get('summary') or ''}".strip()
    names = []
    for match in _PREVIEW_COMPANY_PATTERN.findall(text):
        raw_name = str(match).strip("，。；：、()（）[]【】 ")
        candidates = [raw_name]
        if _COMPANY_SPLIT_PATTERN.search(raw_name):
            candidates = [part.strip() for part in _COMPANY_SPLIT_PATTERN.split(raw_name) if part.strip()]
        for candidate in candidates:
            name = candidate
            for marker in _COMPANY_SPLIT_MARKERS:
                if marker in name:
                    name = name.split(marker, 1)[0].strip()
            for suffix in _COMPANY_TRIM_SUFFIXES:
                if name.endswith(suffix) and len(name) > len(suffix) + 1:
                    name = name[: -len(suffix)].strip()
            if not _is_queryable_company_name(name) or name in names:
                continue
            names.append(name)
    return names


def _list_artifact_company_names(artifact_id: str, limit: int = 8) -> List[str]:
    mongo = _get_mongo_conn()
    entity_rows = mongo.find_many(
        "entity_instances",
        query={"artifact_id": artifact_id},
        limit=1000,
    )
    names = []
    for item in entity_rows:
        entity_type = str(item.get("entity_type") or "").strip().lower()
        if entity_type != "company":
            continue
        name = str(item.get("canonical_name") or item.get("name") or "").strip()
        if not _is_queryable_company_name(name) or name in names:
            continue
        names.append(name)
        if len(names) >= max(int(limit or 8), 1):
            return names

    for record in _artifact_bridge_batch_records(artifact_id, limit=200):
        for name in _extract_batch_companies(record):
            if name in names:
                continue
            names.append(name)
            if len(names) >= max(int(limit or 8), 1):
                return names
    return names


def _build_artifact_scoped_graph_from_batch(company_name: str, artifact_id: str) -> Dict:
    records = _artifact_bridge_batch_records(artifact_id, limit=100)
    if not records:
        return {"nodes": [], "edges": []}

    normalized_company = str(company_name or "").strip()
    nodes = {}
    edges = []
    for record in records:
        doc_id = str(record.get("doc_id") or "").strip()
        title = str(record.get("title") or doc_id or "文档").strip()
        companies = _extract_batch_companies(record)
        if normalized_company and normalized_company not in companies:
            continue
        if doc_id:
            nodes.setdefault(doc_id, {"id": doc_id, "name": title, "type": "document"})
        for company in companies:
            company_id = f"company::{company}"
            nodes.setdefault(company_id, {"id": company_id, "name": company, "type": "company"})
            if doc_id:
                edges.append({"source": doc_id, "target": company_id, "relation": "同批次共现", "confidence": 1.0})

    return {"nodes": list(nodes.values()), "edges": edges}


@router.post("/build")
async def build_graph(text: str, use_llm: bool = False):
    """
    从文本构建产业链图谱(会重新进行文本分析)
    """
    try:
        result = graph_service.build_graph_from_text(text, use_llm)
        return result
    except Exception as e:
        logger.error(f"图谱构建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_to_graph(
    entities: Dict = Body(...),
    relations: List[Dict] = Body(...)
):
    """
    保存已分析的实体和关系到图谱(不重新分析)
    """
    try:
        result = graph_service.save_analyzed_data(entities, relations)
        return result
    except Exception as e:
        logger.error(f"保存到图谱失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=GraphData)
async def query_industry_chain(query: IndustryChainQuery):
    """
    查询企业产业链关系
    """
    try:
        result = graph_service.query_industry_chain(
            query.company_name,
            query.depth
        )
        return result
    except Exception as e:
        logger.error(f"图谱查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_name}")
async def get_company_relations(
    company_name: str,
    depth: int = Query(default=2, ge=1, le=5),
    artifact_id: str | None = Query(default=None),
):
    """
    获取企业的产业链关系
    """
    try:
        if artifact_id:
            return _build_artifact_scoped_graph(company_name, artifact_id)
        result = graph_service.query_industry_chain(company_name, depth)
        return result
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_id}/companies")
async def get_artifact_companies(
    artifact_id: str,
    limit: int = Query(default=8, ge=1, le=20),
):
    try:
        return {
            "artifact_id": artifact_id,
            "items": _list_artifact_company_names(artifact_id, limit=limit),
        }
    except Exception as e:
        logger.error(f"读取 artifact 可查询企业失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_graph_statistics():
    """
    获取图谱统计信息（优化版，使用缓存）
    """
    try:
        from app.database.redis_db import redis_conn
        
        # 尝试从缓存获取
        cache_key = "graph:statistics"
        cached_stats = redis_conn.get(cache_key)
        if cached_stats:
            logger.info("返回缓存的图谱统计数据")
            return cached_stats
        
        # 缓存未命中，查询数据库
        stats = graph_service.get_graph_statistics()
        
        # 缓存5分钟
        redis_conn.set(cache_key, stats, expire=300)
        
        return stats
    except Exception as e:
        logger.error(f"统计查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_graph():
    """
    清空图谱数据(谨慎使用)
    """
    try:
        query = "MATCH (n) DETACH DELETE n"
        graph_service.neo4j.execute_write(query)
        return {"message": "图谱已清空"}
    except Exception as e:
        logger.error(f"清空失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 新增：时间分析相关API ====================

@router.get("/entities/{entity_id}/timeline")
async def get_entity_timeline(entity_id: str):
    """
    获取实体时间轴（历史事件+动量趋势）
    
    Args:
        entity_id: 规范实体ID (如 CANONICAL_COMPANY_华为)
    
    Returns:
        实体信息、历史事件、动量趋势
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 获取实体信息
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
        
        # 获取动量趋势（最近30天）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        momentum_trend = momentum_engine.get_momentum_trend(
            entity_id, 
            start_time, 
            end_time,
            interval_days=1
        )
        
        # 获取相关文档作为事件
        documents = mongodb_conn.find_many(
            'document_instances',
            {'entity_references.entity_id': entity_id},
            limit=50
        )
        
        events = []
        for doc in documents:
            events.append({
                'event_id': str(doc['_id']),
                'event_type': '文档引用',
                'entity_ids': [entity_id],
                'description': doc.get('title', ''),
                'timestamp': doc.get('created_at'),
                'is_future': False,
                'confidence': 1.0,
                'source_count': 1
            })
        
        return {
            'entity': entity,
            'events': events,
            'momentum_trend': {
                'entity_id': entity_id,
                'entity_name': entity['names'][0] if entity.get('names') else entity_id,
                'data_points': momentum_trend,
                'trend_direction': 'stable',
                'change_rate': 0.0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取时间轴失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/momentum")
async def get_entity_momentum(
    entity_id: str,
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取实体动量趋势
    
    Args:
        entity_id: 规范实体ID
        start_date: 开始日期（可选，默认30天前）
        end_date: 结束日期（可选，默认今天）
    
    Returns:
        动量趋势数据
    """
    try:
        # 解析日期（结束日期设为23:59:59包含全天数据）
        if end_date:
            end_time = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        else:
            end_time = datetime.now()
        
        if start_date:
            start_time = datetime.fromisoformat(start_date)
        else:
            start_time = end_time - timedelta(days=30)
        
        logger.info(f"查询实体 {entity_id} 动量趋势: {start_time} 到 {end_time}")
        
        # 获取动量趋势
        trend_data = momentum_engine.get_momentum_trend(
            entity_id,
            start_time,
            end_time,
            interval_days=1
        )
        
        # 计算趋势方向
        if len(trend_data) >= 2:
            first_value = trend_data[0]['value']
            last_value = trend_data[-1]['value']
            change_rate = (last_value - first_value) / first_value if first_value > 0 else 0
            
            if change_rate > 0.1:
                trend_direction = "上升"
            elif change_rate < -0.1:
                trend_direction = "下降"
            else:
                trend_direction = "稳定"
        else:
            trend_direction = "未知"
            change_rate = 0.0
        
        from app.database.mongodb import mongodb_conn
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        entity_name = entity['names'][0] if entity and entity.get('names') else entity_id
        
        return {
            'entity_id': entity_id,
            'entity_name': entity_name,
            'data_points': trend_data,
            'trend_direction': trend_direction,
            'change_rate': change_rate
        }
        
    except Exception as e:
        logger.error(f"获取动量趋势失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum/top")
async def get_top_momentum_entities(
    limit: int = Query(default=10, ge=1, le=100),
    entity_type: str = Query(None, description="实体类型过滤"),
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取动量最高的实体排行榜（优化版，使用缓存）
    
    Args:
        limit: 返回数量
        entity_type: 实体类型（COMPANY/PRODUCT/TECHNOLOGY等）
        start_date: 开始日期，用于筛选该时间段内的实体
        end_date: 结束日期
    
    Returns:
        高动量实体列表及统计信息
    """
    try:
        from app.database.redis_db import redis_conn
        
        # 解析时间范围
        time_start = None
        time_end = None
        if start_date:
            try:
                time_start = datetime.fromisoformat(start_date)
                logger.info(f"解析start_date: {start_date} -> {time_start}")
            except ValueError:
                logger.warning(f"无效的start_date格式: {start_date}")
                pass
        if end_date:
            try:
                # 结束日期设置为当天的23:59:59，包含整天数据
                time_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
                logger.info(f"解析end_date: {end_date} -> {time_end}")
            except ValueError:
                logger.warning(f"无效的end_date格式: {end_date}")
                pass
        
        # 构建缓存key
        cache_key = f"momentum:top:{limit}:{entity_type or 'all'}:{start_date or 'none'}:{end_date or 'none'}"
        
        # 尝试从缓存获取
        cached_result = redis_conn.get(cache_key)
        if cached_result:
            logger.info(f"返回缓存的Top动量数据: {cache_key}")
            return cached_result
        
        logger.info(f"调用get_top_momentum_entities: limit={limit}, type={entity_type}, start={time_start}, end={time_end}")
        
        # 获取top实体
        top_entities = momentum_engine.get_top_momentum_entities(
            limit=limit, 
            entity_type=entity_type,
            start_date=time_start,
            end_date=time_end
        )
        
        # 格式化实体数据
        formatted_entities = []
        for entity in top_entities:
            # 计算动量变化（基于历史数据）
            momentum_change = None
            momentum_history = entity.get('momentum_history', [])
            if len(momentum_history) >= 2:
                current_value = momentum_history[-1].get('value', 0)
                previous_value = momentum_history[-2].get('value', 0)
                if previous_value > 0:
                    momentum_change = (current_value - previous_value) / previous_value
                else:
                    momentum_change = current_value if current_value > 0 else 0
            
            # 格式化last_updated为ISO字符串
            last_updated = entity.get('last_updated')
            if last_updated and isinstance(last_updated, datetime):
                last_updated = last_updated.isoformat()
            
            formatted_entities.append({
                'id': entity.get('id'),
                'name': entity.get('names', ['未知'])[0] if entity.get('names') else '未知',
                'type': entity.get('type'),
                'current_momentum': entity.get('current_momentum', 0),
                'momentum_change': momentum_change,
                'reference_count': entity.get('reference_count', 0),
                'last_updated': last_updated
            })
        
        # 获取统计信息
        stats = momentum_engine.get_momentum_statistics(
            entity_type=entity_type,
            start_date=time_start,
            end_date=time_end
        )
        
        result = {
            'entities': formatted_entities,
            'stats': stats
        }
        
        # 缓存结果2分钟
        redis_conn.set(cache_key, result, expire=120)
        
        return result
    except Exception as e:
        logger.error(f"获取top动量实体失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum/trend")
async def get_momentum_trend(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    entity_type: str = Query(None, description="实体类型过滤")
):
    """
    获取聚合动量趋势
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        entity_type: 实体类型（可选）
    
    Returns:
        时间范围内的平均动量趋势
    """
    try:
        # 解析日期（结束日期设为23:59:59包含全天数据）
        start_time = datetime.fromisoformat(start_date)
        end_time = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        
        logger.info(f"查询聚合趋势: {start_time} 到 {end_time}")
        
        # 检查Redis缓存
        from app.database.redis_db import redis_conn
        cache_key = f"momentum:trend:{start_date}:{end_date}:{entity_type or 'all'}"
        
        # 尝试从缓存获取（RedisConnection.get会自动反序列化）
        cached_data = redis_conn.get(cache_key)
        if cached_data:
            logger.info(f"返回缓存的趋势数据: {cache_key}")
            return cached_data
        
        # 获取趋势数据
        trend_data = momentum_engine.get_momentum_trend_aggregate(
            start_time,
            end_time,
            interval_days=1,
            entity_type=entity_type
        )
        
        result = {
            'trend': trend_data,
            'start_date': start_date,
            'end_date': end_date,
            'entity_type': entity_type or 'all'
        }
        
        # 缓存结果（缓存1小时）- RedisConnection会自动处理dict序列化
        redis_conn.set(cache_key, result, expire=3600)
        logger.info(f"已缓存趋势数据: {cache_key}")
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"获取动量趋势失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/momentum/update")
async def update_momentum(entity_type: str = Query(None)):
    """
    手动触发动量更新
    
    Args:
        entity_type: 只更新特定类型，默认全部
    
    Returns:
        更新统计
    """
    try:
        result = momentum_engine.update_all_momentum(entity_type)
        return result
    except Exception as e:
        logger.error(f"动量更新失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/neo4j-to-mongodb")
async def sync_neo4j_to_mongodb():
    """
    同步 Neo4j 实体到 MongoDB canonical_entities 集合
    用于修复历史数据或手动同步
    
    Returns:
        同步统计
    """
    try:
        from app.database.mongodb import canonical_entity_manager
        
        # 1. 从 Neo4j 获取所有实体
        query = "MATCH (n:Entity) RETURN n.name as name, n.type as type"
        entities = graph_service.neo4j.execute_query(query)
        
        logger.info(f"从 Neo4j 找到 {len(entities)} 个实体")
        
        # 2. 保存到 MongoDB
        success_count = 0
        failed_count = 0
        
        for entity in entities:
            name = entity.get('name')
            entity_type = entity.get('type')
            
            if not name or not entity_type:
                failed_count += 1
                continue
            
            try:
                entity_id = f"CANONICAL_{entity_type}_{name}"
                canonical_entity_manager.create_or_update_entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    names=[name],
                    momentum=0.0
                )
                success_count += 1
            except Exception as e:
                logger.error(f"同步实体失败 {name}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "total_entities": len(entities),
            "synced": success_count,
            "failed": failed_count,
            "message": f"成功同步 {success_count} 个实体到 MongoDB"
        }
    except Exception as e:
        logger.error(f"同步失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/sync/create-document-instances")
async def create_document_instances_for_articles():
    """
    为所有文章创建文档实例
    """
    try:
        from app.database.mongodb import mongodb_conn, document_instance_manager
        
        articles = list(mongodb_conn.get_collection('crawled_articles').find({'processed': True}))
        logger.info(f"找到 {len(articles)} 篇已处理文章")
        
        success_count = 0
        skipped_count = 0
        
        for article in articles:
            try:
                article_id = str(article['_id'])
                entities = article.get('entities', {})
                
                if not entities or all(len(v) == 0 for v in entities.values()):
                    skipped_count += 1
                    continue
                
                entity_references = []
                for category, items in entities.items():
                    entity_type = category.upper().rstrip('S')
                    for item_name in items:
                        entity_id = f"CANONICAL_{entity_type}_{item_name}"
                        entity_references.append({
                            'entity_id': entity_id,
                            'entity_name': item_name,
                            'entity_type': entity_type
                        })
                
                if entity_references:
                    document_instance_manager.save_document_instance(
                        source_id=article.get('source', 'unknown'),
                        title=article.get('title', ''),
                        content=article.get('content', ''),
                        extracted_time=article.get('published_at') or article.get('crawled_at'),
                        entity_references=entity_references
                    )
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"处理文章失败: {e}")
        
        return {
            "success": True,
            "total_articles": len(articles),
            "created": success_count,
            "skipped": skipped_count,
            "message": f"成功为 {success_count} 篇文章创建文档实例"
        }
    except Exception as e:
        logger.error(f"创建文档实例失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
