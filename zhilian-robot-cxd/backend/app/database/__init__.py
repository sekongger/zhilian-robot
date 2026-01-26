"""
数据库模块初始化
"""
from .neo4j_db import neo4j_conn
from .mongodb import mongodb_conn
from .redis_db import redis_conn

# MinIO连接 - 可选导入，避免模块不存在时报错
try:
    from .minio_db import minio_conn
    MINIO_AVAILABLE = True
except ImportError:
    minio_conn = None
    MINIO_AVAILABLE = False

__all__ = ['neo4j_conn', 'mongodb_conn', 'redis_conn', 'minio_conn']


def init_databases():
    """初始化所有数据库连接"""
    neo4j_conn.connect()
    mongodb_conn.connect()
    redis_conn.connect()
    if MINIO_AVAILABLE and minio_conn:
        minio_conn.connect()


def close_databases():
    """关闭所有数据库连接"""
    neo4j_conn.close()
    mongodb_conn.close()
    redis_conn.close()
    if MINIO_AVAILABLE and minio_conn:
        minio_conn.close()
