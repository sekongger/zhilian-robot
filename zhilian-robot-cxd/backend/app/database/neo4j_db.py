"""
数据库连接模块 - Neo4j图数据库
"""
from neo4j import GraphDatabase
from config.settings import settings
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Neo4j数据库连接管理"""
    
    def __init__(self):
        self._driver: Optional[GraphDatabase.driver] = None
    
    def connect(self):
        """建立连接"""
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info("Neo4j连接成功")
        except Exception as e:
            logger.error(f"Neo4j连接失败: {str(e)}")
            raise
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j连接已关闭")
    
    def execute_query(self, query: str, parameters: dict = None):
        """执行Cypher查询"""
        if not self._driver:
            logger.error("Neo4j driver 未初始化")
            return []
        
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                # 完整读取所有记录
                records = []
                for record in result:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # 处理 Neo4j 节点对象
                        if hasattr(value, '_properties'):
                            record_dict[key] = dict(value._properties)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                return records
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            return []
    
    def execute_write(self, query: str, parameters: dict = None):
        """执行写入操作"""
        with self._driver.session() as session:
            result = session.write_transaction(
                lambda tx: tx.run(query, parameters or {})
            )
            return result
    
    # ==================== 新增：规范实体相关方法 ====================
    
    def create_canonical_entity(self, entity_id: str, name: str, entity_type: str,
                               momentum: float = 0.0, properties: dict = None):
        """
        创建规范实体节点
        
        Args:
            entity_id: 实体唯一ID
            name: 实体名称
            entity_type: 实体类型
            momentum: 动量值
            properties: 其他属性
        """
        props = properties or {}
        query = """
        MERGE (e:CanonicalEntity {id: $entity_id})
        ON CREATE SET 
            e.name = $name,
            e.type = $entity_type,
            e.current_momentum = $momentum,
            e.first_seen = datetime(),
            e.last_updated = datetime(),
            e.reference_count = 0,
            e.avg_credibility = 0.5
        ON MATCH SET
            e.name = $name,
            e.last_updated = datetime()
        SET e += $properties
        RETURN e
        """
        params = {
            'entity_id': entity_id,
            'name': name,
            'entity_type': entity_type,
            'momentum': momentum,
            'properties': props
        }
        return self.execute_write(query, params)
    
    def update_entity_momentum(self, entity_id: str, momentum: float):
        """更新实体动量"""
        query = """
        MATCH (e:CanonicalEntity {id: $entity_id})
        SET e.current_momentum = $momentum,
            e.last_updated = datetime()
        RETURN e
        """
        return self.execute_write(query, {'entity_id': entity_id, 'momentum': momentum})
    
    def create_temporal_relation(self, source_id: str, target_id: str, 
                                relation_type: str, confidence: float = 0.9,
                                established_date: datetime = None):
        """
        创建时间化关系
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            confidence: 置信度
            established_date: 建立时间
        """
        est_date = established_date or datetime.now()
        query = f"""
        MATCH (s:CanonicalEntity {{id: $source_id}})
        MATCH (t:CanonicalEntity {{id: $target_id}})
        MERGE (s)-[r:{relation_type}]->(t)
        ON CREATE SET
            r.confidence = $confidence,
            r.established_date = datetime($est_date),
            r.last_confirmed = datetime(),
            r.source_count = 1
        ON MATCH SET
            r.confidence = ($confidence + r.confidence) / 2,
            r.last_confirmed = datetime(),
            r.source_count = r.source_count + 1
        RETURN r
        """
        params = {
            'source_id': source_id,
            'target_id': target_id,
            'confidence': confidence,
            'est_date': est_date.isoformat()
        }
        return self.execute_write(query, params)
    
    def get_entity_with_momentum(self, entity_id: str):
        """获取实体及其动量信息"""
        query = """
        MATCH (e:CanonicalEntity {id: $entity_id})
        RETURN e
        """
        return self.execute_query(query, {'entity_id': entity_id})
    
    def get_top_momentum_entities(self, limit: int = 10, entity_type: str = None):
        """获取动量最高的实体"""
        type_filter = f"WHERE e.type = '{entity_type}'" if entity_type else ""
        query = f"""
        MATCH (e:CanonicalEntity)
        {type_filter}
        RETURN e
        ORDER BY e.current_momentum DESC
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_entity_relations_with_time(self, entity_id: str, depth: int = 2):
        """
        获取实体的时间化关系网络
        
        Args:
            entity_id: 实体ID
            depth: 查询深度
            
        Returns:
            节点和关系列表
        """
        query = f"""
        MATCH path = (start:CanonicalEntity {{id: $entity_id}})-[r*1..{depth}]-(connected)
        WITH start, connected, relationships(path) as rels
        RETURN 
            collect(DISTINCT start) + collect(DISTINCT connected) as nodes,
            [rel IN rels | {{
                source: startNode(rel).id,
                target: endNode(rel).id,
                type: type(rel),
                confidence: rel.confidence,
                established_date: rel.established_date,
                last_confirmed: rel.last_confirmed
            }}] as relationships
        """
        return self.execute_query(query, {'entity_id': entity_id})
    
    def increment_reference_count(self, entity_id: str):
        """增加实体引用计数"""
        query = """
        MATCH (e:CanonicalEntity {id: $entity_id})
        SET e.reference_count = e.reference_count + 1
        RETURN e.reference_count as count
        """
        return self.execute_write(query, {'entity_id': entity_id})


# 全局连接实例
neo4j_conn = Neo4jConnection()
