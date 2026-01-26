"""
爬虫定时任务
"""
from celery import shared_task
from app.crawler.news_crawler import news_crawler
from app.crawler.rss_parser import rss_parser
from app.nlp.llm import llm_processor
from app.services.graph_service import graph_service
from app.database.mongodb import mongodb_conn
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(name='app.tasks.crawl_tasks.crawl_all_news', bind=True)
def crawl_all_news(self):
    """
    爬取所有关键词的新闻并构建图谱
    """
    logger.info("⏰ 定时任务启动: 爬取行业新闻")
    
    # 预定义关键词
    keywords = [
        # === 核心零部件 (上游) ===
        "精密减速器", "RV减速器", "谐波减速器",
        "伺服电机", "伺服驱动器", "运动控制器",
        "机器视觉传感器", "激光雷达 LiDAR", "六维力传感器",
        
        # === 本体制造 (中游) ===
        "工业机器人", "协作机器人", "SCARA机器人", "Delta机器人",
        "人形机器人", "具身智能", "AGV", "AMR",
        "发那科", "ABB", "安川电机", "库卡", "埃斯顿", "汇川技术", # 龙头企业
        
        # === 系统集成与应用 (下游) ===
        "焊接机器人", "码垛机器人", "喷涂机器人",
        "黑灯工厂", "智能产线", "柔性制造"
    ]
    
    total_processed = 0
    total_entities = 0
    total_relations = 0
    
    try:
        for keyword in keywords:
            logger.info(f"📰 正在处理关键词: {keyword}")
            
            # 1. 爬取新闻
            articles = news_crawler.crawl_all_sources(keyword)
            
            for article in articles:
                try:
                    # 2. 使用DeepSeek提取实体和关系
                    result = llm_processor.analyze_industry_chain(article['content'])
                    entities = result.get('entities', {})
                    relations = result.get('relations', [])
                    
                    # 3. 保存到Neo4j图数据库
                    save_result = graph_service.save_analyzed_data(entities, relations)
                    
                    if save_result.get('success'):
                        total_entities += save_result.get('entities_count', 0)
                        total_relations += save_result.get('relations_count', 0)
                    
                    # 4. 保存原始数据到MongoDB
                    article_doc = {
                        'title': article['title'],
                        'content': article['content'],
                        'source': article['source'],
                        'keyword': article.get('keyword', keyword),
                        'url': article.get('url', ''),
                        'entities': entities,
                        'relations': relations,
                        'crawled_at': article.get('crawled_at', datetime.now()),
                        'processed_at': datetime.now(),
                        'processed': True
                    }
                    
                    result = mongodb_conn.get_collection('crawled_articles').insert_one(article_doc)
                    article_id = str(result.inserted_id)
                    
                    # 创建文档实例
                    from app.database.mongodb import document_instance_manager
                    entity_references = []
                    for category, items in entities.items():
                        # Use lowercase category to match MongoDB entity IDs
                        for item_name in items:
                            entity_id = f"CANONICAL_{category}_{item_name}"
                            entity_references.append({
                                'entity_id': entity_id,
                                'entity_name': item_name,
                                'entity_type': category
                            })
                    
                    if entity_references:
                        document_instance_manager.save_document_instance(
                            source_id=article['source'],
                            title=article['title'],
                            content=article.get('content', ''),
                            extracted_time=article.get('crawled_at', datetime.now()),
                            entity_references=entity_references
                        )
                    
                    total_processed += 1
                    
                    logger.info(f"✅ 处理成功: {article['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"❌ 处理文章失败: {e}")
                    continue
        
        summary = {
            'task': 'crawl_all_news',
            'status': 'completed',
            'keywords_count': len(keywords),
            'articles_processed': total_processed,
            'entities_extracted': total_entities,
            'relations_extracted': total_relations,
            'completed_at': datetime.now().isoformat()
        }
        
        # 保存任务执行记录（保存到MongoDB时使用datetime对象）
        mongodb_summary = summary.copy()
        mongodb_summary['completed_at'] = datetime.now()
        mongodb_summary['keywords'] = keywords
        mongodb_conn.get_collection('task_history').insert_one(mongodb_summary)
        
        logger.info(f"🎉 任务完成! 处理 {total_processed} 篇文章, "
                   f"提取 {total_entities} 个实体, {total_relations} 个关系")
        
        return summary
        
    except Exception as e:
        logger.error(f"💥 任务执行失败: {e}", exc_info=True)
        raise


@shared_task(name='app.tasks.crawl_tasks.fetch_rss_updates', bind=True)
def fetch_rss_updates(self):
    """
    获取RSS订阅更新
    """
    logger.info("⏰ 定时任务启动: 检查RSS更新")
    
    total_processed = 0
    total_entities = 0
    total_relations = 0
    
    try:
        # 1. 解析所有RSS源
        articles = rss_parser.parse_all_feeds()
        
        if not articles:
            logger.info("📭 没有获取到新文章")
            return {
                'task': 'fetch_rss_updates',
                'status': 'completed',
                'articles_processed': 0,
                'entities_extracted': 0,
                'relations_extracted': 0
            }
        
        # 2. 批量检查已存在的URL（优化：一次查询代替N次）
        article_urls = [article['url'] for article in articles if article.get('url')]
        existing_urls = set()
        if article_urls:
            existing_docs = mongodb_conn.get_collection('crawled_articles').find(
                {'url': {'$in': article_urls}},
                {'url': 1}
            )
            existing_urls = {doc['url'] for doc in existing_docs}
        
        # 3. 过滤出新文章
        new_articles = [article for article in articles if article.get('url') not in existing_urls]
        
        skipped_count = len(articles) - len(new_articles)
        if skipped_count > 0:
            logger.info(f"⏭️ 跳过 {skipped_count} 篇已处理文章")
        
        if not new_articles:
            logger.info("✅ 所有文章均已处理，无需更新")
            return {
                'task': 'fetch_rss_updates',
                'status': 'completed',
                'articles_processed': 0,
                'entities_extracted': 0,
                'relations_extracted': 0
            }
        
        logger.info(f"📝 发现 {len(new_articles)} 篇新文章，开始处理...")
        
        # 4. 处理新文章
        for article in new_articles:
            try:
                # 2. 提取实体和关系
                result = llm_processor.analyze_industry_chain(article['content'])
                entities = result.get('entities', {})
                relations = result.get('relations', [])
                
                # 3. 保存到图谱
                save_result = graph_service.save_analyzed_data(entities, relations)
                
                if save_result.get('success'):
                    total_entities += save_result.get('entities_count', 0)
                    total_relations += save_result.get('relations_count', 0)
                
                # 4. 保存到MongoDB
                article_doc = {
                    'title': article['title'],
                    'content': article['content'],
                    'source': article['source'],
                    'url': article.get('url', ''),
                    'entities': entities,
                    'relations': relations,
                    'published_at': article.get('published_at'),
                    'crawled_at': article.get('crawled_at', datetime.now()),
                    'processed_at': datetime.now(),
                    'processed': True
                }
                
                result = mongodb_conn.get_collection('crawled_articles').insert_one(article_doc)
                article_id = str(result.inserted_id)
                
                # 5. 创建文档实例（用于动量计算）
                from app.database.mongodb import document_instance_manager
                
                # 构建实体引用列表
                entity_references = []
                for category, items in entities.items():
                    # Use lowercase category to match MongoDB entity IDs
                    for item_name in items:
                        entity_id = f"CANONICAL_{category}_{item_name}"
                        entity_references.append({
                            'entity_id': entity_id,
                            'entity_name': item_name,
                            'entity_type': category
                        })
                
                if entity_references:
                    document_instance_manager.save_document_instance(
                        source_id=article['source'],
                        title=article['title'],
                        content=article.get('content', ''),
                        extracted_time=article.get('published_at', datetime.now()),
                        entity_references=entity_references
                    )
                
                total_processed += 1
                
                logger.info(f"✅ RSS文章处理成功: {article['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"❌ 处理RSS文章失败: {e}")
                continue
        
        summary = {
            'task': 'fetch_rss_updates',
            'status': 'completed',
            'articles_processed': total_processed,
            'entities_extracted': total_entities,
            'relations_extracted': total_relations,
            'completed_at': datetime.now()
        }
        
        mongodb_conn.get_collection('task_history').insert_one(summary)
        
        logger.info(f"🎉 RSS更新完成! 处理 {total_processed} 篇新文章")
        
        # 返回不包含ObjectId的结果(避免JSON序列化错误)
        return {
            'task': 'fetch_rss_updates',
            'status': 'completed',
            'articles_processed': total_processed,
            'entities_extracted': total_entities,
            'relations_extracted': total_relations
        }
        
    except Exception as e:
        logger.error(f"💥 RSS更新失败: {e}", exc_info=True)
        raise


@shared_task(name='app.tasks.crawl_tasks.crawl_single_keyword')
def crawl_single_keyword(keyword: str):
    """
    爬取单个关键词的新闻(手动触发) - 修复版：增加历史记录
    """
    logger.info(f"🔍 手动爬取: {keyword}")
    
    # 初始化统计变量
    processed_count = 0
    total_entities = 0
    total_relations = 0
    
    try:
        articles = news_crawler.crawl_all_sources(keyword)
        
        for article in articles:
            try:
                result = llm_processor.analyze_industry_chain(article['content'])
                entities = result.get('entities', {})
                relations = result.get('relations', [])
                
                # 保存图谱并获取统计数据
                save_result = graph_service.save_analyzed_data(entities, relations)
                if save_result.get('success'):
                    total_entities += save_result.get('entities_count', 0)
                    total_relations += save_result.get('relations_count', 0)
                
                article_doc = {
                    'title': article['title'],
                    'content': article['content'],
                    'source': article['source'],
                    'keyword': keyword,
                    'url': article.get('url', ''),
                    'entities': entities,
                    'relations': relations,
                    'crawled_at': article.get('crawled_at', datetime.now()),
                    'processed_at': datetime.now(),
                    'processed': True  # 确保状态为已处理
                }
                
                result = mongodb_conn.get_collection('crawled_articles').insert_one(article_doc)
                article_id = str(result.inserted_id)
                
                # 创建文档实例
                from app.database.mongodb import document_instance_manager
                entity_references = []
                for category, items in entities.items():
                    # Use lowercase category to match MongoDB entity IDs
                    for item_name in items:
                        entity_id = f"CANONICAL_{category}_{item_name}"
                        entity_references.append({
                            'entity_id': entity_id,
                            'entity_name': item_name,
                            'entity_type': category
                        })
                
                if entity_references:
                    document_instance_manager.save_document_instance(
                        source_id=article['source'],
                        title=article['title'],
                        content=article.get('content', ''),
                        extracted_time=article.get('crawled_at', datetime.now()),
                        entity_references=entity_references
                    )
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"处理文章失败: {e}")
                continue
        
        # === 新增：构造任务总结并保存到数据库 ===
        summary = {
            'task': 'crawl_single_keyword',
            'status': 'completed',
            'keyword': keyword,  # 记录具体的关键词
            'articles_processed': processed_count,
            'entities_extracted': total_entities,
            'relations_extracted': total_relations,
            'completed_at': datetime.now()
        }
        mongodb_conn.get_collection('task_history').insert_one(summary)
        # ======================================

        logger.info(f"✅ 关键词 '{keyword}' 处理完成: {processed_count} 篇文章")
        
        # 返回结果 (JSON可序列化版本)
        return {
            'task': 'crawl_single_keyword',
            'status': 'completed',
            'keyword': keyword,
            'articles_processed': processed_count,
            'entities_extracted': total_entities,
            'relations_extracted': total_relations,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"爬取失败: {e}", exc_info=True)
        # 记录失败的任务历史
        mongodb_conn.get_collection('task_history').insert_one({
            'task': 'crawl_single_keyword',
            'status': 'failed',
            'keyword': keyword,
            'error': str(e),
            'completed_at': datetime.now()
        })
        # 返回JSON可序列化的错误信息
        return {
            'task': 'crawl_single_keyword',
            'status': 'failed',
            'keyword': keyword,
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }
