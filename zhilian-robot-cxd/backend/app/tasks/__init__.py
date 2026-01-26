"""
Celery任务调度
"""
from .celery_app import celery_app
from .crawl_tasks import *
from .data_tasks import *

__all__ = ['celery_app']
