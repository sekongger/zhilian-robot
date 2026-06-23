"""
数据库模块初始化
"""
try:
    from .neo4j_db import neo4j_conn
    NEO4J_AVAILABLE = True
except ImportError:
    neo4j_conn = None
    NEO4J_AVAILABLE = False
from .mongodb import mongodb_conn
from .redis_db import redis_conn

# MinIO连接 - 可选导入，避免模块不存在时报错
try:
    from .minio_db import minio_conn
    MINIO_AVAILABLE = True
except ImportError:
    minio_conn = None
    MINIO_AVAILABLE = False

# MySQL本体库连接 - 可选导入
try:
    from .mysql_ontology_db import ontology_db
    ONTOLOGY_DB_AVAILABLE = True
except ImportError:
    ontology_db = None
    ONTOLOGY_DB_AVAILABLE = False

__all__ = ['neo4j_conn', 'mongodb_conn', 'redis_conn', 'minio_conn', 'ontology_db', 'NEO4J_AVAILABLE']


def init_databases():
    """初始化所有数据库连接"""
    if NEO4J_AVAILABLE and neo4j_conn:
        neo4j_conn.connect()
    mongodb_conn.connect()
    redis_conn.connect()
    if MINIO_AVAILABLE and minio_conn:
        minio_conn.connect()
    if ONTOLOGY_DB_AVAILABLE and ontology_db:
        try:
            ontology_db.connect()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"MySQL本体库连接失败（可选）: {str(e)}")


def close_databases():
    """关闭所有数据库连接"""
    if NEO4J_AVAILABLE and neo4j_conn:
        neo4j_conn.close()
    mongodb_conn.close()
    redis_conn.close()
    if MINIO_AVAILABLE and minio_conn:
        minio_conn.close()
    if ONTOLOGY_DB_AVAILABLE and ontology_db:
        ontology_db.close()
