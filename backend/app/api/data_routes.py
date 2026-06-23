"""
API路由 - 数据管理接口
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.tasks.crawl_tasks import crawl_single_keyword, fetch_rss_updates
from app.tasks.data_tasks import get_crawl_statistics
from app.database.mongodb import mongodb_conn
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["Data Management"])


def _process_crawled_article_record(article: dict, article_id: str):
    from app.news_pipeline.service import news_pipeline_service

    return news_pipeline_service.process_crawled_article(article, external_id=article_id)


class CrawlRequest(BaseModel):
    """爬取请求"""
    keyword: str


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    article_ids: list[str]


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    article_ids: list[str]


@router.post("/crawl")
async def trigger_crawl(keyword: str, background_tasks: BackgroundTasks):
    """
    手动触发爬取任务
    
    Args:
        keyword: 爬取关键词
    """
    try:
        logger.info(f"收到手动爬取请求: {keyword}")
        
        # 使用Celery异步任务
        task = crawl_single_keyword.delay(keyword)
        
        return {
            "message": f"爬取任务已启动: {keyword}",
            "task_id": task.id,
            "keyword": keyword,
            "status": "running"
        }
    except Exception as e:
        logger.error(f"启动爬取任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rss/update")
async def trigger_rss_update(background_tasks: BackgroundTasks):
    """
    手动触发RSS更新
    """
    try:
        logger.info("收到手动RSS更新请求")
        
        # 使用Celery异步任务
        task = fetch_rss_updates.delay()
        
        return {
            "message": "RSS更新任务已启动",
            "task_id": task.id,
            "status": "running"
        }
    except Exception as e:
        logger.error(f"启动RSS更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/batch")
async def process_articles_batch(request: BatchProcessRequest):
    """
    批量处理文章 - 提取实体和关系
    
    Args:
        request: 包含文章ID列表的请求
        
    Returns:
        处理结果统计
    """
    try:
        from bson import ObjectId
        
        article_ids = request.article_ids
        
        if not article_ids:
            raise HTTPException(status_code=400, detail="文章ID列表不能为空")
        
        if len(article_ids) > 100:
            raise HTTPException(status_code=400, detail="单次最多处理100篇文章")
        
        logger.info(f"开始批量处理{len(article_ids)}篇文章")
        
        collection = mongodb_conn.get_collection('crawled_articles')
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        total_entities = 0
        total_relations = 0
        errors = []
        
        for article_id in article_ids:
            try:
                # 验证ID格式
                if not ObjectId.is_valid(article_id):
                    errors.append({"article_id": article_id, "error": "无效的文章ID"})
                    failed_count += 1
                    continue
                
                # 获取文章
                article = collection.find_one({'_id': ObjectId(article_id)})
                
                if not article:
                    errors.append({"article_id": article_id, "error": "文章不存在"})
                    failed_count += 1
                    continue
                
                if article.get('processed'):
                    skipped_count += 1
                    continue
                
                # 提取实体和关系
                content = article.get('content', '') or article.get('summary', '')
                if not content:
                    errors.append({"article_id": article_id, "error": "文章内容为空"})
                    failed_count += 1
                    continue

                pipeline_result = _process_crawled_article_record(article, article_id)
                process_summary = pipeline_result.get('process_result') or {}
                entities_count = int(process_summary.get('entities') or 0)
                relations_count = int(process_summary.get('relations') or 0)
                
                success_count += 1
                total_entities += entities_count
                total_relations += relations_count
                
            except Exception as e:
                logger.error(f"处理文章{article_id}失败: {e}")
                errors.append({"article_id": article_id, "error": str(e)})
                failed_count += 1
        
        return {
            "message": "批量处理完成",
            "total": len(article_ids),
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "entities_extracted": total_entities,
            "relations_extracted": total_relations,
            "errors": errors[:10]  # 只返回前10个错误
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/{article_id}")
async def process_article(article_id: str, background_tasks: BackgroundTasks):
    """
    处理文章 - 提取实体和关系
    
    Args:
        article_id: 文章ID
    """
    try:
        from bson import ObjectId
        
        logger.info(f"开始处理文章: {article_id}")
        
        # 获取文章
        collection = mongodb_conn.get_collection('crawled_articles')
        article = collection.find_one({'_id': ObjectId(article_id)})
        
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")
        
        if article.get('processed'):
            return {
                "message": "文章已处理过",
                "article_id": article_id
            }
        
        # 提取实体和关系
        content = article.get('content', '') or article.get('summary', '')
        if not content:
            raise HTTPException(status_code=400, detail="文章内容为空")

        pipeline_result = _process_crawled_article_record(article, article_id)
        process_summary = pipeline_result.get('process_result') or {}
        entities_count = int(process_summary.get('entities') or 0)
        relations_count = int(process_summary.get('relations') or 0)
        
        return {
            "message": "文章处理成功",
            "article_id": article_id,
            "entities_count": entities_count,
            "relations_count": relations_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文章失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """
    获取爬取统计信息（优化版，使用缓存）
    """
    try:
        from app.database.redis_db import redis_conn
        
        # 尝试从缓存获取
        cache_key = "data:statistics"
        cached_stats = redis_conn.get(cache_key)
        if cached_stats:
            logger.info("返回缓存的数据统计")
            return cached_stats
        
        # 缓存未命中，查询数据库
        stats = get_crawl_statistics()
        
        # 缓存3分钟
        redis_conn.set(cache_key, stats, expire=180)
        
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles")
async def get_recent_articles(limit: int = 20, skip: int = 0):
    """
    获取最近爬取的文章（优化版，只返回必要字段）
    
    Args:
        limit: 返回数量
        skip: 跳过数量
    """
    try:
        collection = mongodb_conn.get_collection('crawled_articles')
        
        # 只查询必要的字段，减少数据传输
        projection = {
            '_id': 1,
            'title': 1,
            'source': 1,
            'url': 1,
            'crawled_at': 1,
            'processed': 1,
            'processed_at': 1,
            'entities_count': 1,
            'relations_count': 1
        }
        
        articles = list(
            collection.find({}, projection)
            .sort('crawled_at', -1)
            .skip(skip)
            .limit(limit)
        )
        
        # 转换ObjectId为字符串
        for article in articles:
            article['_id'] = str(article['_id'])
            if 'crawled_at' in article:
                article['crawled_at'] = article['crawled_at'].isoformat()
            if 'processed_at' in article:
                article['processed_at'] = article['processed_at'].isoformat()
        
        # 使用count_documents的estimated版本提高性能
        total = collection.estimated_document_count()
        
        return {
            "articles": articles,
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logger.error(f"获取文章列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/history")
async def get_task_history(limit: int = 10):
    """
    获取任务执行历史
    
    Args:
        limit: 返回数量
    """
    try:
        collection = mongodb_conn.get_collection('task_history')
        
        tasks = list(
            collection.find()
            .sort('completed_at', -1)
            .limit(limit)
        )
        
        # 转换ObjectId和日期
        for task in tasks:
            task['_id'] = str(task['_id'])
            if 'completed_at' in task:
                task['completed_at'] = task['completed_at'].isoformat()
        
        return {
            "tasks": tasks,
            "total": collection.count_documents({})
        }
    except Exception as e:
        logger.error(f"获取任务历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str):
    """
    删除指定文章
    
    Args:
        article_id: 文章ID
    """
    try:
        from bson import ObjectId
        
        collection = mongodb_conn.get_collection('crawled_articles')
        result = collection.delete_one({'_id': ObjectId(article_id)})
        
        if result.deleted_count > 0:
            return {"message": "文章删除成功", "deleted_count": 1}
        else:
            raise HTTPException(status_code=404, detail="文章不存在")
    except Exception as e:
        logger.error(f"删除文章失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/delete/batch")
async def delete_articles_batch(request: BatchDeleteRequest):
    """
    批量删除文章
    
    Args:
        request: 包含文章ID列表的请求
        
    Returns:
        删除结果统计
    """
    try:
        from bson import ObjectId
        
        article_ids = request.article_ids
        
        if not article_ids:
            raise HTTPException(status_code=400, detail="文章ID列表不能为空")
        
        if len(article_ids) > 100:
            raise HTTPException(status_code=400, detail="单次最多删除100篇文章")
        
        logger.info(f"开始批量删除{len(article_ids)}篇文章")
        
        collection = mongodb_conn.get_collection('crawled_articles')
        
        # 转换为ObjectId
        object_ids = []
        for article_id in article_ids:
            if ObjectId.is_valid(article_id):
                object_ids.append(ObjectId(article_id))
        
        # 批量删除
        result = collection.delete_many({'_id': {'$in': object_ids}})
        
        return {
            "message": "批量删除完成",
            "deleted_count": result.deleted_count,
            "requested_count": len(article_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_old_data_route(days: int = 30):
    """
    清理旧数据
    
    Args:
        days: 保留最近多少天的数据 (1-365)
    """
    try:
        # 验证天数范围
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400, 
                detail="天数必须在1-365之间"
            )
        
        logger.info(f"开始清理{days}天前的数据")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        collection = mongodb_conn.get_collection('crawled_articles')
        result = collection.delete_many({
            'crawled_at': {'$lt': cutoff_date}
        })
        
        return {
            "message": f"清理完成",
            "deleted_count": result.deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "days": days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_data_sources():
    """
    获取所有数据源及其统计
    """
    try:
        collection = mongodb_conn.get_collection('crawled_articles')
        
        # 按数据源统计
        pipeline = [
            {
                '$group': {
                    '_id': '$source',
                    'count': {'$sum': 1},
                    'latest': {'$max': '$crawled_at'}
                }
            },
            {'$sort': {'count': -1}}
        ]
        
        sources = list(collection.aggregate(pipeline))
        
        # 转换日期
        for source in sources:
            if 'latest' in source and source['latest']:
                source['latest'] = source['latest'].isoformat()
        
        return {
            "sources": sources,
            "total_sources": len(sources)
        }
    except Exception as e:
        logger.error(f"获取数据源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/merge-duplicates")
async def merge_duplicate_entities():
    """
    合并重复的实体（手动触发）
    """
    try:
        logger.info("收到合并重复实体请求")
        
        from app.tasks.data_tasks import merge_duplicate_entities as merge_task
        
        # 使用Celery异步任务
        task = merge_task.delay()
        
        return {
            "message": "实体去重任务已启动",
            "task_id": task.id,
            "status": "running"
        }
    except Exception as e:
        logger.error(f"启动去重任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/update-momentum")
async def update_all_momentum():
    """
    手动更新所有实体的动量值
    """
    try:
        logger.info("收到更新动量请求")
        
        from app.tasks.data_tasks import update_all_entity_momentum as update_task
        
        # 使用Celery异步任务
        task = update_task.delay()
        
        return {
            "message": "动量更新任务已启动",
            "task_id": task.id,
            "status": "running"
        }
    except Exception as e:
        logger.error(f"启动动量更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
