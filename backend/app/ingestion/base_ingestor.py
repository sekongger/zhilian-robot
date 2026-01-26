"""
数据接入器基类 - 定义统一的数据接入接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """数据源类型"""
    RSS = "rss"
    CRAWLER = "crawler"
    FILE = "file"
    API = "api"
    STREAM = "stream"


class ContentType(Enum):
    """内容类型"""
    TEXT = "text/plain"
    HTML = "text/html"
    PDF = "application/pdf"
    EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV = "text/csv"
    JSON = "application/json"
    XML = "application/xml"
    IMAGE = "image/*"
    BINARY = "application/octet-stream"


@dataclass
class RawDataRecord:
    """
    原始数据记录
    
    存储从各种数据源接入的原始未处理数据
    """
    # 基础标识
    record_id: str = ""                    # 唯一记录ID (自动生成)
    
    # 来源信息
    source_type: str = ""                  # 来源类型: rss/crawler/file/api
    source_name: str = ""                  # 来源名称 (如: 36kr, baidu_news)
    source_url: str = ""                   # 原始URL (如适用)
    
    # 内容数据
    raw_content: bytes = b""               # 原始内容 (二进制)
    content_type: str = "application/octet-stream"  # MIME类型
    content_encoding: str = "utf-8"        # 内容编码
    content_hash: str = ""                 # 内容哈希 (用于去重)
    
    # 提取的文本 (如果可以提取)
    extracted_text: str = ""               # 提取的纯文本
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 自定义元数据
    
    # 时间信息
    original_timestamp: Optional[datetime] = None  # 原始内容的时间
    ingested_at: datetime = field(default_factory=datetime.now)  # 接入时间
    
    # 存储路径
    minio_path: str = ""                   # MinIO存储路径
    
    # 处理状态
    is_processed: bool = False             # 是否已处理
    processing_error: str = ""             # 处理错误信息
    
    def __post_init__(self):
        """初始化后处理"""
        # 生成记录ID (如果未提供)
        if not self.record_id:
            self.record_id = self._generate_id()
        
        # 生成内容哈希 (如果未提供)
        if not self.content_hash and self.raw_content:
            self.content_hash = self._compute_hash()
    
    def _generate_id(self) -> str:
        """生成唯一记录ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        source_hash = hashlib.md5(
            f"{self.source_type}:{self.source_name}:{timestamp}".encode()
        ).hexdigest()[:8]
        return f"RAW_{self.source_type.upper()}_{source_hash}"
    
    def _compute_hash(self) -> str:
        """计算内容哈希"""
        return hashlib.sha256(self.raw_content).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (用于MongoDB存储)"""
        return {
            "record_id": self.record_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "content_type": self.content_type,
            "content_encoding": self.content_encoding,
            "content_hash": self.content_hash,
            "extracted_text": self.extracted_text[:5000] if self.extracted_text else "",  # 限制长度
            "metadata": self.metadata,
            "original_timestamp": self.original_timestamp,
            "ingested_at": self.ingested_at,
            "minio_path": self.minio_path,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
            "raw_content_size": len(self.raw_content)  # 不存储原始内容,只存储大小
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], raw_content: bytes = b"") -> "RawDataRecord":
        """从字典创建实例"""
        return cls(
            record_id=data.get("record_id", ""),
            source_type=data.get("source_type", ""),
            source_name=data.get("source_name", ""),
            source_url=data.get("source_url", ""),
            raw_content=raw_content,
            content_type=data.get("content_type", "application/octet-stream"),
            content_encoding=data.get("content_encoding", "utf-8"),
            content_hash=data.get("content_hash", ""),
            extracted_text=data.get("extracted_text", ""),
            metadata=data.get("metadata", {}),
            original_timestamp=data.get("original_timestamp"),
            ingested_at=data.get("ingested_at", datetime.now()),
            minio_path=data.get("minio_path", ""),
            is_processed=data.get("is_processed", False),
            processing_error=data.get("processing_error", "")
        )


class BaseIngestor(ABC):
    """
    数据接入器基类
    
    所有数据接入器都应继承此类并实现抽象方法
    """
    
    def __init__(self, source_type: str, source_name: str):
        """
        初始化接入器
        
        Args:
            source_type: 数据源类型 (rss/crawler/file/api)
            source_name: 数据源名称
        """
        self.source_type = source_type
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def ingest(self, source: Any, **kwargs) -> List[RawDataRecord]:
        """
        接入数据
        
        Args:
            source: 数据源 (可以是URL、文件路径、API配置等)
            **kwargs: 其他参数
            
        Returns:
            原始数据记录列表
        """
        pass
    
    @abstractmethod
    def validate(self, record: RawDataRecord) -> bool:
        """
        验证数据记录
        
        Args:
            record: 原始数据记录
            
        Returns:
            是否有效
        """
        pass
    
    def extract_text(self, record: RawDataRecord) -> str:
        """
        从原始数据中提取文本 (子类可重写)
        
        Args:
            record: 原始数据记录
            
        Returns:
            提取的文本
        """
        # 默认实现: 尝试解码为文本
        try:
            return record.raw_content.decode(record.content_encoding)
        except Exception:
            return ""
    
    def compute_fingerprint(self, content: str) -> str:
        """
        计算内容指纹 (用于去重)
        
        Args:
            content: 文本内容
            
        Returns:
            内容指纹
        """
        # 简单实现: 使用MD5
        return hashlib.md5(content.encode()).hexdigest()
    
    def save_to_storage(self, record: RawDataRecord) -> str:
        """
        保存原始数据到存储
        
        Args:
            record: 原始数据记录
            
        Returns:
            存储路径
        """
        from app.database.minio_db import minio_conn
        from config.settings import settings
        
        try:
            # 生成对象名称
            object_name = minio_conn.generate_object_name(
                source_type=record.source_type,
                content=record.raw_content
            )
            
            # 上传到MinIO
            minio_path = minio_conn.upload_bytes(
                bucket_name=settings.MINIO_BUCKET_RAW,
                object_name=object_name,
                data=record.raw_content,
                content_type=record.content_type,
                metadata={
                    "source_name": record.source_name,
                    "record_id": record.record_id,
                    "content_hash": record.content_hash
                }
            )
            
            record.minio_path = minio_path
            self.logger.info(f"原始数据已保存到MinIO: {minio_path}")
            return minio_path
            
        except Exception as e:
            self.logger.error(f"保存到MinIO失败: {e}")
            raise
    
    def save_metadata(self, record: RawDataRecord) -> str:
        """
        保存元数据到MongoDB
        
        Args:
            record: 原始数据记录
            
        Returns:
            MongoDB记录ID
        """
        from app.database.mongodb import mongodb_conn
        
        try:
            result = mongodb_conn.insert_one("raw_data", record.to_dict())
            self.logger.info(f"元数据已保存到MongoDB: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            self.logger.error(f"保存到MongoDB失败: {e}")
            raise
    
    def ingest_and_store(self, source: Any, **kwargs) -> List[RawDataRecord]:
        """
        接入数据并存储
        
        这是一个便捷方法，组合了接入、验证和存储操作
        
        Args:
            source: 数据源
            **kwargs: 其他参数
            
        Returns:
            处理后的记录列表
        """
        records = self.ingest(source, **kwargs)
        stored_records = []
        
        for record in records:
            try:
                # 验证
                if not self.validate(record):
                    self.logger.warning(f"记录验证失败: {record.record_id}")
                    continue
                
                # 提取文本
                if not record.extracted_text:
                    record.extracted_text = self.extract_text(record)
                
                # 保存到存储
                self.save_to_storage(record)
                self.save_metadata(record)
                
                stored_records.append(record)
                
            except Exception as e:
                record.processing_error = str(e)
                self.logger.error(f"处理记录失败 {record.record_id}: {e}")
        
        self.logger.info(f"成功接入并存储 {len(stored_records)}/{len(records)} 条记录")
        return stored_records
