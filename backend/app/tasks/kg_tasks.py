"""
知识图谱构建任务
"""
from celery import shared_task
import logging
from pathlib import Path
import sys

_SOURCE_PROJECT_ROOT = Path(__file__).resolve().parents[3] / "supxmind" / "supxmind-openks"
if _SOURCE_PROJECT_ROOT.exists() and str(_SOURCE_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_PROJECT_ROOT))

from openks.entry.api.service import build_news_kg

logger = logging.getLogger(__name__)


@shared_task(name='app.tasks.kg_tasks.build_news_kg_queue', bind=True)
def build_news_kg_queue(self, limit: int = 20):
    logger.info("⏰ 启动 news_kg 队列构建任务, limit=%s", limit)
    result = build_news_kg(limit=limit)
    logger.info(
        "✅ news_kg 构建任务完成: processed=%s statements=%s",
        result.get("processed"),
        result.get("statements_written"),
    )
    return result
