"""
智链机器人 - 配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
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
    
    # AI模型配置
    # DeepSeek API (兼容 OpenAI 接口)
    OPENAI_API_KEY: str = ""  # 使用 DeepSeek API Key
    OPENAI_API_BASE: str = "https://api.deepseek.com"  # DeepSeek API Base URL
    OPENAI_MODEL: str = "deepseek-chat"  # DeepSeek 模型名称
    HF_TOKEN: str = ""
    HF_MODEL: str = "bert-base-chinese"
    
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
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 配置实例
settings = get_settings()
