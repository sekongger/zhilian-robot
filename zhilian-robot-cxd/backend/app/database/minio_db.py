"""
MinIO对象存储连接模块 - 用于原始数据和文件存储
"""
from minio import Minio
from minio.error import S3Error
from config.settings import settings
from typing import Optional, BinaryIO, List, Dict
from datetime import timedelta
import logging
import io
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class MinIOConnection:
    """MinIO对象存储连接管理"""
    
    def __init__(self):
        self._client: Optional[Minio] = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        try:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            # 测试连接
            self._client.list_buckets()
            self._connected = True
            logger.info("MinIO连接成功")
            
            # 初始化默认Bucket
            self._init_buckets()
            
        except Exception as e:
            logger.error(f"MinIO连接失败: {str(e)}")
            raise
    
    def _init_buckets(self):
        """初始化所需的Bucket"""
        buckets = [
            settings.MINIO_BUCKET_RAW,       # 原始数据
            settings.MINIO_BUCKET_PROCESSED  # 处理后数据
        ]
        
        for bucket_name in buckets:
            try:
                if not self._client.bucket_exists(bucket_name):
                    self._client.make_bucket(bucket_name)
                    logger.info(f"创建Bucket: {bucket_name}")
                else:
                    logger.debug(f"Bucket已存在: {bucket_name}")
            except S3Error as e:
                logger.error(f"创建Bucket失败 {bucket_name}: {e}")
    
    def close(self):
        """关闭连接"""
        self._client = None
        self._connected = False
        logger.info("MinIO连接已关闭")
    
    @property
    def client(self) -> Minio:
        """获取MinIO客户端,如果未连接则自动连接"""
        if not self._connected or self._client is None:
            logger.warning("MinIO未连接,正在自动连接...")
            self.connect()
        return self._client
    
    def upload_file(self, bucket_name: str, object_name: str, 
                   file_data: BinaryIO, content_type: str = "application/octet-stream",
                   metadata: Dict = None) -> str:
        """
        上传文件到MinIO
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称/路径
            file_data: 文件数据(二进制流)
            content_type: MIME类型
            metadata: 自定义元数据
            
        Returns:
            对象的完整路径
        """
        try:
            # 获取文件大小
            file_data.seek(0, 2)  # 移动到文件末尾
            file_size = file_data.tell()
            file_data.seek(0)  # 回到文件开头
            
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata
            )
            
            full_path = f"{bucket_name}/{object_name}"
            logger.info(f"文件上传成功: {full_path}")
            return full_path
            
        except S3Error as e:
            logger.error(f"文件上传失败: {e}")
            raise
    
    def upload_bytes(self, bucket_name: str, object_name: str,
                    data: bytes, content_type: str = "application/octet-stream",
                    metadata: Dict = None) -> str:
        """
        上传字节数据到MinIO
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称/路径
            data: 字节数据
            content_type: MIME类型
            metadata: 自定义元数据
            
        Returns:
            对象的完整路径
        """
        file_data = io.BytesIO(data)
        return self.upload_file(bucket_name, object_name, file_data, content_type, metadata)
    
    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        """
        从MinIO下载文件
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称
            
        Returns:
            文件字节数据
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"文件下载成功: {bucket_name}/{object_name}")
            return data
        except S3Error as e:
            logger.error(f"文件下载失败: {e}")
            raise
    
    def get_presigned_url(self, bucket_name: str, object_name: str, 
                         expires: timedelta = timedelta(hours=1)) -> str:
        """
        生成临时访问URL
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称
            expires: 过期时间(默认1小时)
            
        Returns:
            临时访问URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name, object_name, expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"生成预签名URL失败: {e}")
            raise
    
    def list_objects(self, bucket_name: str, prefix: str = "", 
                    recursive: bool = True) -> List[Dict]:
        """
        列出Bucket中的对象
        
        Args:
            bucket_name: Bucket名称
            prefix: 前缀过滤
            recursive: 是否递归列出
            
        Returns:
            对象列表
        """
        try:
            objects = self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
            result = []
            for obj in objects:
                result.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })
            return result
        except S3Error as e:
            logger.error(f"列出对象失败: {e}")
            raise
    
    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """
        删除对象
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称
            
        Returns:
            是否删除成功
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"对象删除成功: {bucket_name}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"对象删除失败: {e}")
            return False
    
    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        检查对象是否存在
        
        Args:
            bucket_name: Bucket名称
            object_name: 对象名称
            
        Returns:
            是否存在
        """
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False
    
    def generate_object_name(self, source_type: str, original_filename: str = None,
                            content: bytes = None) -> str:
        """
        生成标准化的对象名称
        
        格式: {source_type}/{YYYY}/{MM}/{DD}/{hash}_{filename}
        
        Args:
            source_type: 数据源类型 (rss/crawler/file/api)
            original_filename: 原始文件名
            content: 文件内容(用于生成hash)
            
        Returns:
            标准化的对象名称
        """
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        
        # 生成内容hash
        if content:
            content_hash = hashlib.md5(content).hexdigest()[:8]
        else:
            content_hash = hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:8]
        
        # 生成文件名
        if original_filename:
            filename = f"{content_hash}_{original_filename}"
        else:
            filename = f"{content_hash}.bin"
        
        return f"{source_type}/{date_path}/{filename}"


# 全局连接实例
minio_conn = MinIOConnection()
