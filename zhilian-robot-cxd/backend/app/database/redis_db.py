"""
数据库连接模块 - Redis缓存
"""
import redis
from config.settings import settings
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)


class RedisConnection:
    """Redis缓存连接管理"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    def connect(self):
        """建立连接"""
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # 测试连接
            self._client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            raise
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            logger.info("Redis连接已关闭")
    
    def set(self, key: str, value: any, expire: int = None):
        """设置键值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        self._client.set(key, value, ex=expire)
    
    def get(self, key: str):
        """获取值"""
        value = self._client.get(key)
        if value:
            try:
                return json.loads(value)
            except:
                return value
        return None
    
    def delete(self, key: str):
        """删除键"""
        return self._client.delete(key)
    
    def exists(self, key: str):
        """检查键是否存在"""
        return self._client.exists(key)


# 全局连接实例
redis_conn = RedisConnection()
