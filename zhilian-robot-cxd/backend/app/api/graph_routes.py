"""
API路由 - 图谱查询接口
"""
from fastapi import APIRouter, HTTPException, Query, Body
from app.models.schemas import GraphData, IndustryChainQuery, EntityTimelineResponse, MomentumTrend
from app.services.graph_service import graph_service
from app.analytics.momentum import momentum_engine
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])


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
    depth: int = Query(default=2, ge=1, le=5)
):
    """
    获取企业的产业链关系
    """
    try:
        result = graph_service.query_industry_chain(company_name, depth)
        return result
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
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
