"""
数据管理任务
"""
from celery import shared_task
from app.database.mongodb import mongodb_conn
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='app.tasks.data_tasks.cleanup_old_crawl_data')
def cleanup_old_crawl_data(days: int = 30):
    """
    清理旧的爬取数据
    
    Args:
        days: 保留最近多少天的数据
    """
    logger.info(f"🧹 开始清理 {days} 天前的爬取数据")
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 删除旧文章
        result = mongodb_conn.get_collection('crawled_articles').delete_many({
            'crawled_at': {'$lt': cutoff_date}
        })
        
        deleted_count = result.deleted_count
        
        logger.info(f"✅ 清理完成! 删除了 {deleted_count} 条旧数据")
        
        # 记录清理任务
        mongodb_conn.get_collection('task_history').insert_one({
            'task': 'cleanup_old_crawl_data',
            'status': 'completed',
            'days': days,
            'deleted_count': deleted_count,
            'completed_at': datetime.now()
        })
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date
        }
        
    except Exception as e:
        logger.error(f"❌ 清理数据失败: {e}", exc_info=True)
        raise


@shared_task(name='app.tasks.data_tasks.get_crawl_statistics')
def get_crawl_statistics():
    """
    获取爬取统计信息
    """
    try:
        collection = mongodb_conn.get_collection('crawled_articles')
        
        # 总文章数
        total_articles = collection.count_documents({})
        
        # 按来源统计
        source_stats = list(collection.aggregate([
            {'$group': {
                '_id': '$source',
                'count': {'$sum': 1}
            }}
        ]))
        
        # 最近7天的文章数
        week_ago = datetime.now() - timedelta(days=7)
        recent_articles = collection.count_documents({
            'crawled_at': {'$gte': week_ago}
        })
        
        # 最近的任务执行记录
        recent_tasks = list(
            mongodb_conn.get_collection('task_history')
            .find()
            .sort('completed_at', -1)
            .limit(10)
        )
        
        # 转换ObjectId为字符串
        for task in recent_tasks:
            task['_id'] = str(task['_id'])
            if 'completed_at' in task:
                task['completed_at'] = task['completed_at'].isoformat()
        
        return {
            'total_articles': total_articles,
            'recent_articles': recent_articles,
            'source_stats': source_stats,
            'recent_tasks': recent_tasks
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {}


@shared_task(name='app.tasks.data_tasks.update_all_entity_momentum')
def update_all_entity_momentum():
    """
    更新所有实体的动量值（定时任务）
    """
    logger.info("📊 开始更新所有实体动量")
    
    try:
        from app.analytics.momentum import momentum_engine
        from datetime import datetime
        
        # 批量更新动量
        result = momentum_engine.update_all_momentum()
        
        logger.info(f"✅ 动量更新完成: {result.get('updated_count')} 个实体")
        
        # 记录任务执行
        mongodb_conn.get_collection('task_history').insert_one({
            'task': 'update_all_entity_momentum',
            'status': 'completed',
            'updated_count': result.get('updated_count'),
            'completed_at': datetime.now()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 动量更新失败: {e}", exc_info=True)
        raise


@shared_task(name='app.tasks.data_tasks.merge_duplicate_entities')
def merge_duplicate_entities():
    """
    合并重复的实体（手动触发）
    """
    logger.info("🔄 开始合并重复实体")
    
    try:
        from collections import defaultdict
        
        # 获取所有实体
        all_entities = list(mongodb_conn.find_many('canonical_entities', {}))
        
        # 按名称分组
        name_to_entities = defaultdict(list)
        for entity in all_entities:
            names = entity.get('names', [])
            if names:
                primary_name = names[0]
                name_to_entities[primary_name].append(entity)
        
        # 查找重复项
        merged_count = 0
        deleted_count = 0
        
        for name, entities in name_to_entities.items():
            if len(entities) <= 1:
                continue
            
            # 按动量排序，保留动量最高的
            entities.sort(key=lambda e: e.get('current_momentum', 0), reverse=True)
            primary = entities[0]
            duplicates = entities[1:]
            
            logger.info(f"合并重复实体: {name} ({len(entities)} 个)")
            
            # 合并引用计数和其他信息
            total_refs = sum(e.get('reference_count', 0) for e in entities)
            all_names = set()
            for e in entities:
                all_names.update(e.get('names', []))
            
            # 更新主实体
            mongodb_conn.get_collection('canonical_entities').update_one(
                {'_id': primary['_id']},
                {'$set': {
                    'reference_count': total_refs,
                    'names': list(all_names),
                    'merged_from': [e['_id'] for e in duplicates],
                    'merged_at': datetime.now()
                }}
            )
            
            # 更新文档引用
            for dup in duplicates:
                # 将引用从重复实体改为主实体
                mongodb_conn.get_collection('document_instances').update_many(
                    {'entity_references.entity_id': dup['_id']},
                    {'$set': {'entity_references.$.entity_id': primary['_id']}}
                )
                
                # 删除重复实体
                mongodb_conn.get_collection('canonical_entities').delete_one(
                    {'_id': dup['_id']}
                )
                deleted_count += 1
            
            merged_count += 1
        
        logger.info(f"✅ 实体去重完成: 合并了 {merged_count} 组重复实体，删除了 {deleted_count} 个重复项")
        
        # 记录任务执行
        mongodb_conn.get_collection('task_history').insert_one({
            'task': 'merge_duplicate_entities',
            'status': 'completed',
            'merged_count': merged_count,
            'deleted_count': deleted_count,
            'completed_at': datetime.now()
        })
        
        return {
            'merged_count': merged_count,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"❌ 实体去重失败: {e}", exc_info=True)
        raise
