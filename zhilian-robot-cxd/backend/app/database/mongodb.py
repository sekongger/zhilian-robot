"""
数据库连接模块 - MongoDB文档数据库
"""
from pymongo import MongoClient
from config.settings import settings
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """MongoDB数据库连接管理"""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db = None
    
    def connect(self):
        """建立连接"""
        try:
            self._client = MongoClient(settings.MONGODB_URI)
            self._db = self._client[settings.MONGODB_DATABASE]
            # 测试连接
            self._client.server_info()
            logger.info("MongoDB连接成功")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            raise
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            logger.info("MongoDB连接已关闭")
    
    def get_collection(self, collection_name: str):
        """获取集合,如果未连接则自动连接"""
        if self._db is None:
            logger.warning("MongoDB未连接,正在自动连接...")
            self.connect()
        return self._db[collection_name]
    
    def insert_one(self, collection_name: str, document: dict):
        """插入单个文档"""
        collection = self.get_collection(collection_name)
        return collection.insert_one(document)
    
    def insert_many(self, collection_name: str, documents: list):
        """批量插入文档"""
        collection = self.get_collection(collection_name)
        return collection.insert_many(documents)
    
    def find_one(self, collection_name: str, query: dict):
        """查询单个文档"""
        collection = self.get_collection(collection_name)
        return collection.find_one(query)
    
    def find_many(self, collection_name: str, query: dict = None, limit: int = 0, sort: list = None):
        """
        查询多个文档
        
        Args:
            collection_name: 集合名称
            query: 查询条件
            limit: 限制返回数量
            sort: 排序条件，格式为 [('field', 1/-1)]，1为升序，-1为降序
        """
        collection = self.get_collection(collection_name)
        cursor = collection.find(query or {})
        
        if sort:
            cursor = cursor.sort(sort)
        
        if limit > 0:
            cursor = cursor.limit(limit)
            
        return list(cursor)
    
    def update_one(self, collection_name: str, query: dict, update: dict, upsert: bool = False):
        """更新单个文档"""
        collection = self.get_collection(collection_name)
        return collection.update_one(query, update, upsert=upsert)
    
    def delete_one(self, collection_name: str, query: dict):
        """删除单个文档"""
        collection = self.get_collection(collection_name)
        return collection.delete_one(query)
    
    def delete_many(self, collection_name: str, query: dict):
        """删除多个文档"""
        collection = self.get_collection(collection_name)
        return collection.delete_many(query)
    
    def aggregate(self, collection_name: str, pipeline: list):
        """聚合查询"""
        collection = self.get_collection(collection_name)
        return list(collection.aggregate(pipeline))


class SourceManager:
    """数据源管理器"""
    
    def __init__(self, db_conn: MongoDBConnection):
        self.db = db_conn
        self.collection_name = 'sources'
    
    def register_source(self, name: str, domain: str, credibility_scores: dict) -> str:
        """
        注册数据源
        
        Args:
            name: 源名称
            domain: 域名
            credibility_scores: 可信度评分字典 {category: score}
            
        Returns:
            source_id
        """
        source_doc = {
            'name': name,
            'domain': domain,
            'credibility_scores': credibility_scores,
            'created_at': datetime.now()
        }
        result = self.db.insert_one(self.collection_name, source_doc)
        logger.info(f"注册数据源: {name} ({domain})")
        return str(result.inserted_id)
    
    def get_source_by_domain(self, domain: str):
        """根据域名获取数据源"""
        return self.db.find_one(self.collection_name, {'domain': domain})
    
    def get_credibility(self, source_id: str, category: str = 'general') -> float:
        """获取数据源在特定类别的可信度"""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        try:
            source = self.db.find_one(self.collection_name, {'_id': ObjectId(source_id)})
            if source and 'credibility_scores' in source:
                return source['credibility_scores'].get(category, 0.5)
        except (InvalidId, TypeError):
            pass
        
        return 0.8  # 默认较高可信度


class CanonicalEntityManager:
    """规范实体管理器"""
    
    def __init__(self, db_conn: MongoDBConnection):
        self.db = db_conn
        self.collection_name = 'canonical_entities'
    
    def create_or_update_entity(self, entity_id: str, entity_type: str, 
                                 names: list, momentum: float = 0.0, 
                                 ontology: dict = None) -> str:
        """
        创建或更新规范实体
        
        Args:
            entity_id: 实体唯一ID
            entity_type: 实体类型
            names: 同义词列表
            momentum: 当前动量值
            ontology: 本体信息
            
        Returns:
            entity_id
        """
        from datetime import datetime
        
        entity_doc = {
            '_id': entity_id,
            'type': entity_type,
            'names': list(set(names)),  # 去重
            'current_momentum': momentum,
            'momentum_history': [
                {'date': datetime.now(), 'value': momentum}
            ],
            'ontology': ontology or {},
            'first_seen': datetime.now(),
            'last_updated': datetime.now(),
            'reference_count': 0
        }
        
        self.db.update_one(
            self.collection_name,
            {'_id': entity_id},
            {'$setOnInsert': entity_doc},
            upsert=True
        )
        
        return entity_id
    
    def add_synonym(self, entity_id: str, synonym: str):
        """添加同义词"""
        self.db.update_one(
            self.collection_name,
            {'_id': entity_id},
            {'$addToSet': {'names': synonym}}
        )
    
    def update_momentum(self, entity_id: str, momentum_value: float):
        """更新动量值"""
        from datetime import datetime
        self.db.update_one(
            self.collection_name,
            {'_id': entity_id},
            {
                '$set': {
                    'current_momentum': momentum_value,
                    'last_updated': datetime.now()
                },
                '$push': {
                    'momentum_history': {
                        'date': datetime.now(),
                        'value': momentum_value
                    }
                }
            }
        )
    
    def find_by_name(self, name: str):
        """通过名称查找规范实体（支持同义词）"""
        return self.db.find_one(self.collection_name, {'names': name})
    
    def increment_reference_count(self, entity_id: str):
        """增加引用计数"""
        self.db.update_one(
            self.collection_name,
            {'_id': entity_id},
            {'$inc': {'reference_count': 1}}
        )


class DocumentInstanceManager:
    """文档实例管理器"""
    
    def __init__(self, db_conn: MongoDBConnection):
        self.db = db_conn
        self.collection_name = 'document_instances'
    
    def save_document_instance(self, source_id: str, title: str, content: str,
                              extracted_time: datetime = None,
                              sentiment: dict = None,
                              entity_references: list = None) -> str:
        """
        保存文档实例
        
        Args:
            source_id: 数据源ID
            title: 标题
            content: 内容
            extracted_time: 提取的时间引用
            sentiment: 情感分析结果
            entity_references: 实体引用列表
            
        Returns:
            document_id
        """
        from datetime import datetime, timedelta
        
        doc = {
            'source_id': source_id,
            'title': title,
            'content': content,
            'extracted_time': extracted_time,
            'sentiment': sentiment or {},
            'entity_references': entity_references or [],
            'created_at': datetime.now(),
            'cached_until': datetime.now() + timedelta(days=30)
        }
        
        result = self.db.insert_one(self.collection_name, doc)
        return str(result.inserted_id)
    
    def get_recent_documents(self, limit: int = 100):
        """获取最近的文档"""
        return self.db.find_many(
            self.collection_name,
            query={},
            limit=limit
        )
    
    def clean_expired_cache(self):
        """清理过期缓存"""
        from datetime import datetime
        result = self.db.delete_many(
            self.collection_name,
            {'cached_until': {'$lt': datetime.now()}}
        )
        logger.info(f"清理过期文档缓存: {result.deleted_count}条")
        return result.deleted_count


# 全局连接实例
mongodb_conn = MongoDBConnection()

# 全局管理器实例
source_manager = SourceManager(mongodb_conn)
canonical_entity_manager = CanonicalEntityManager(mongodb_conn)
document_instance_manager = DocumentInstanceManager(mongodb_conn)
