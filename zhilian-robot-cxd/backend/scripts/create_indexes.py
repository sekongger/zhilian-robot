"""
数据库索引优化脚本
为MongoDB集合添加索引以提升查询性能
"""
from app.database.mongodb import mongodb_conn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_indexes():
    """创建所有必要的索引"""
    
    mongodb_conn.connect()
    db = mongodb_conn._db  # 使用_db私有属性
    
    logger.info("开始创建MongoDB索引...")
    
    # 1. crawled_articles集合索引
    articles_collection = db['crawled_articles']
    
    # 索引：按爬取时间排序（降序）
    articles_collection.create_index([('crawled_at', -1)], name='idx_crawled_at_desc')
    logger.info("✅ 创建索引: crawled_articles.crawled_at")
    
    # 索引：按处理状态查询
    articles_collection.create_index([('processed', 1)], name='idx_processed')
    logger.info("✅ 创建索引: crawled_articles.processed")
    
    # 复合索引：按处理状态和爬取时间
    articles_collection.create_index(
        [('processed', 1), ('crawled_at', -1)], 
        name='idx_processed_crawled_at'
    )
    logger.info("✅ 创建复合索引: crawled_articles.processed + crawled_at")
    
    # 索引：URL（改为非唯一索引，因为已存在重复数据）
    articles_collection.create_index([('url', 1)], name='idx_url')
    logger.info("✅ 创建索引: crawled_articles.url")
    
    
    # 2. canonical_entities集合索引
    entities_collection = db['canonical_entities']
    
    # 索引：按动量值排序（降序）
    entities_collection.create_index(
        [('current_momentum', -1)], 
        name='idx_current_momentum_desc'
    )
    logger.info("✅ 创建索引: canonical_entities.current_momentum")
    
    # 复合索引：按类型和动量排序
    entities_collection.create_index(
        [('type', 1), ('current_momentum', -1)], 
        name='idx_type_momentum'
    )
    logger.info("✅ 创建复合索引: canonical_entities.type + current_momentum")
    
    # 索引：按更新时间
    entities_collection.create_index(
        [('last_updated', -1)], 
        name='idx_last_updated_desc'
    )
    logger.info("✅ 创建索引: canonical_entities.last_updated")
    
    # 索引：按实体名称（用于搜索）
    entities_collection.create_index(
        [('names', 1)], 
        name='idx_names'
    )
    logger.info("✅ 创建索引: canonical_entities.names")
    
    
    # 3. document_instances集合索引
    documents_collection = db['document_instances']
    
    # 索引：按创建时间排序（降序）
    documents_collection.create_index(
        [('created_at', -1)], 
        name='idx_created_at_desc'
    )
    logger.info("✅ 创建索引: document_instances.created_at")
    
    # 索引：按实体ID查询
    documents_collection.create_index(
        [('entity_references.entity_id', 1)], 
        name='idx_entity_references'
    )
    logger.info("✅ 创建索引: document_instances.entity_references.entity_id")
    
    # 复合索引：实体ID + 创建时间（用于时间轴查询）
    documents_collection.create_index(
        [('entity_references.entity_id', 1), ('created_at', -1)], 
        name='idx_entity_created_at'
    )
    logger.info("✅ 创建复合索引: document_instances.entity_references.entity_id + created_at")
    
    
    # 4. task_history集合索引
    task_collection = db['task_history']
    
    # 索引：按开始时间排序（降序）
    task_collection.create_index(
        [('started_at', -1)], 
        name='idx_started_at_desc'
    )
    logger.info("✅ 创建索引: task_history.started_at")
    
    # 索引：按任务名称
    task_collection.create_index(
        [('task_name', 1)], 
        name='idx_task_name'
    )
    logger.info("✅ 创建索引: task_history.task_name")
    
    
    logger.info("=" * 60)
    logger.info("✅ 所有索引创建完成！")
    logger.info("=" * 60)
    
    # 显示所有索引
    logger.info("\n当前索引列表:")
    logger.info("\n[crawled_articles]")
    for idx in articles_collection.list_indexes():
        logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
    
    logger.info("\n[canonical_entities]")
    for idx in entities_collection.list_indexes():
        logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
    
    logger.info("\n[document_instances]")
    for idx in documents_collection.list_indexes():
        logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
    
    logger.info("\n[task_history]")
    for idx in task_collection.list_indexes():
        logger.info(f"  - {idx['name']}: {idx.get('key', {})}")


if __name__ == '__main__':
    try:
        create_indexes()
    except Exception as e:
        logger.error(f"创建索引失败: {e}", exc_info=True)
        raise
