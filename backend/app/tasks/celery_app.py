"""
Celery应用配置
"""
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_shutdown
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# 创建Celery应用
celery_app = Celery(
    'zhilian_tasks',
    broker=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
    backend=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
    include=[
        'app.tasks.crawl_tasks',
        'app.tasks.data_tasks',
        'app.tasks.kg_tasks',
    ]
)


# Celery Worker 子进程启动时初始化数据库连接
# 注意: 使用 worker_process_init 而不是 worker_init,确保每个 Worker 进程都初始化连接
@worker_process_init.connect
def init_worker_process(**kwargs):
    """Worker子进程启动时初始化数据库连接"""
    logger.info("🚀 Celery Worker 进程启动,正在初始化数据库连接...")
    try:
        from app.database import init_databases
        init_databases()
        logger.info("✅ 数据库连接初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库连接初始化失败: {str(e)}", exc_info=True)


# Celery Worker 关闭时清理资源
@worker_shutdown.connect
def shutdown_worker(**kwargs):
    """Worker关闭时清理数据库连接"""
    logger.info("🛑 Celery Worker 关闭,正在清理资源...")
    try:
        from app.database import close_databases
        close_databases()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 数据库连接关闭失败: {str(e)}", exc_info=True)

# 基本配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# 定时任务配置
celery_app.conf.beat_schedule = {
    # 每天凌晨2点爬取新闻
    'crawl-industry-news-daily': {
        'task': 'app.tasks.crawl_tasks.crawl_all_news',
        'schedule': crontab(hour=2, minute=0),
        'args': (),
    },
    # 每6小时检查RSS更新
    'check-rss-feeds': {
        'task': 'app.tasks.crawl_tasks.fetch_rss_updates',
        'schedule': crontab(minute=0, hour='*/6'),
        'args': (),
    },
    # 每天凌晨4点更新所有实体动量
    'update-entity-momentum-daily': {
        'task': 'app.tasks.data_tasks.update_all_entity_momentum',
        'schedule': crontab(hour=4, minute=0),
        'args': (),
    },
    # 每周一凌晨3点清理旧数据
    'cleanup-old-data': {
        'task': 'app.tasks.data_tasks.cleanup_old_crawl_data',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),
        'args': (30,),  # 清理30天前的数据
    },
    # 每30分钟消费一次 news_kg 队列
    'build-news-kg-queue': {
        'task': 'app.tasks.kg_tasks.build_news_kg_queue',
        'schedule': crontab(minute='*/30'),
        'args': (20,),
    },
}

logger.info("Celery应用已配置完成")
