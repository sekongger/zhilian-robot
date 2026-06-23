"""
智链机器人 - 配置管理模块
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )
    
    # 应用基础配置
    APP_NAME: str = "智链机器人"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENV: str = "development"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Neo4j配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # MongoDB配置
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "zhilian_robot"
    # ODS MongoDB（研报来源）
    ODS_MONGODB_URI: str = ""
    ODS_MONGODB_DATABASE: str = ""
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # MySQL配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "zhilian_robot"
    MYSQL_ONTOLOGY_SCHEMA_DATABASE: str = "ontology_schema_registry"

    # Milvus配置
    MILVUS_HOST: str = ""
    MILVUS_PORT: int = 19530
    
    # AI模型配置
    #     # 智谱 AI API (兼容 OpenAI 接口)
    # OPENAI_API_KEY: str = ""  # 使用智谱 AI API Key
    # OPENAI_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4/"  # 智谱 AI API Base URL
    # OPENAI_MODEL: str = "glm-4"  # 智谱模型名称 (可选: glm-4, glm-4-flash, glm-3-turbo)
    # DeepSeek API (兼容 OpenAI 接口)
    OPENAI_API_KEY: str = "sk-REDACTED"  # 使用 DeepSeek API Key
    OPENAI_API_BASE: str = "https://api.deepseek.com"  # DeepSeek API Base URL
    OPENAI_MODEL: str = "deepseek-chat"  # DeepSeek 模型名称
    HF_TOKEN: str = ""
    HF_MODEL: str = "bert-base-chinese"

    # Graphiti 配置
    GRAPHITI_ENABLED: bool = True
    GRAPHITI_BASE_URL: str = "http://graphiti:8000"
    GRAPHITI_TIMEOUT_SECONDS: float = 30.0
    GRAPHITI_GROUP_PREFIX: str = "openks"
    
    # NLP模型配置
    NER_MODEL: str = "ckiplab/bert-base-chinese-ner"
    RE_MODEL: str = "hfl/chinese-roberta-wwm-ext"
    
    # 爬虫配置
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    CRAWLER_DELAY: int = 2
    CRAWLER_CONCURRENT: int = 5
    
    # 安全配置
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:8100",
        "http://localhost:13000",
        "http://localhost:8000",
        "http://localhost:18000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8100",
        "http://127.0.0.1:13000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:18000",
    ]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # MinIO对象存储配置
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_RAW: str = "raw-data"
    MINIO_BUCKET_PROCESSED: str = "processed-data"

    def model_post_init(self, __context) -> None:
        # 本地容器使用 mysql:3306，远程 IP 默认走 3307（可通过 MYSQL_PORT 显式覆盖）
        if not os.getenv("MYSQL_PORT"):
            if self.MYSQL_HOST not in ("mysql", "localhost", "127.0.0.1") and self.MYSQL_PORT == 3306:
                self.MYSQL_PORT = 3307
    

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 配置实例
settings = get_settings()
