"""
MySQL 本体模型库访问层
"""
import logging
import hashlib
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config.settings import settings

logger = logging.getLogger(__name__)


class OntologyDB:
    """本体模型库管理"""
    
    def __init__(self):
        self.engine = None
        self.Session = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        if self._connected:
            return
        
        try:
            url = (
                f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
                f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_ONTOLOGY_SCHEMA_DATABASE}"
                f"?charset=utf8mb4"
            )
            self.engine = create_engine(
                url, 
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600
            )
            self.Session = sessionmaker(bind=self.engine)
            self._connected = True
            logger.info("MySQL本体模型库连接成功")
        except Exception as e:
            logger.error(f"MySQL本体模型库连接失败: {str(e)}")
            raise
    
    def close(self):
        """关闭连接"""
        if self.engine:
            self.engine.dispose()
            self._connected = False
            logger.info("MySQL本体模型库连接已关闭")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def get_ontology_meta(self) -> Optional[Dict]:
        """获取本体模型信息"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            result = session.execute(text("SELECT * FROM inc_ontology_meta LIMIT 1"))
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    
    def get_classes(self, category: Optional[str] = None, level: Optional[str] = None) -> List[Dict]:
        """获取类定义列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_class WHERE 1=1"
            params = {}
            if category:
                sql += " AND category = :category"
                params["category"] = category
            if level:
                sql += " AND class_level = :level"
                params["level"] = level
            sql += " ORDER BY category, class_level, class_id"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def get_class_by_id(self, class_id: str) -> Optional[Dict]:
        """根据ID获取类定义"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            result = session.execute(
                text("SELECT * FROM inc_class WHERE class_id = :class_id"),
                {"class_id": class_id}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    
    def get_class_tree(self) -> List[Dict]:
        """获取类层级树"""
        classes = self.get_classes()
        tree = []
        class_map = {c["class_id"]: c for c in classes}
        
        for c in classes:
            if not c.get("parent_class_id"):
                tree.append(self._build_subtree(c, class_map))
        return tree
    
    def _build_subtree(self, node: Dict, class_map: Dict) -> Dict:
        """递归构建子树"""
        children = [
            self._build_subtree(c, class_map)
            for c in class_map.values()
            if c.get("parent_class_id") == node["class_id"]
        ]
        return {**node, "children": children}
    
    def get_properties(self, class_id: Optional[str] = None) -> List[Dict]:
        """获取属性定义列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_property WHERE 1=1"
            params = {}
            if class_id:
                sql += " AND class_id = :class_id"
                params["class_id"] = class_id
            sql += " ORDER BY class_id, property_group, property_id"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def get_relations(self, group: Optional[str] = None) -> List[Dict]:
        """获取关系定义列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_relation WHERE 1=1"
            params = {}
            if group:
                sql += " AND relation_group = :group"
                params["group"] = group
            sql += " ORDER BY relation_group, relation_id"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def get_axioms(self, axiom_type: Optional[str] = None, enabled_only: bool = True) -> List[Dict]:
        """获取公理列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_axiom WHERE 1=1"
            params = {}
            if enabled_only:
                sql += " AND is_enabled = 1"
            if axiom_type:
                sql += " AND axiom_type = :type"
                params["type"] = axiom_type
            sql += " ORDER BY axiom_type, priority, axiom_code"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def get_concepts(self, concept_type: Optional[str] = None) -> List[Dict]:
        """获取产业概念列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_concept WHERE 1=1"
            params = {}
            if concept_type:
                sql += " AND concept_type = :concept_type"
                params["concept_type"] = concept_type
            sql += " ORDER BY concept_type, position, concept_id"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def register_instance(self, class_id: str, canonical_name: str, 
                         neo4j_node_id: Optional[int] = None, 
                         mongodb_doc_id: Optional[str] = None) -> str:
        """注册实例"""
        if not self._connected:
            self.connect()
        
        name_hash = hashlib.md5(canonical_name.encode()).hexdigest()[:12]
        instance_id = f"INST_{class_id}_{name_hash}"
        
        with self.Session() as session:
            sql = """
                INSERT INTO inc_instance (instance_id, class_id, canonical_name, neo4j_node_id, mongodb_doc_id)
                VALUES (:instance_id, :class_id, :canonical_name, :neo4j_node_id, :mongodb_doc_id)
                ON DUPLICATE KEY UPDATE 
                    neo4j_node_id = COALESCE(VALUES(neo4j_node_id), neo4j_node_id),
                    mongodb_doc_id = COALESCE(VALUES(mongodb_doc_id), mongodb_doc_id),
                    updated_at = NOW()
            """
            session.execute(text(sql), {
                "instance_id": instance_id,
                "class_id": class_id,
                "canonical_name": canonical_name,
                "neo4j_node_id": neo4j_node_id,
                "mongodb_doc_id": mongodb_doc_id
            })
            session.commit()
        return instance_id
    
    def update_instance_neo4j_id(self, instance_id: str, neo4j_node_id: int) -> bool:
        """更新实例的Neo4j节点ID"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            result = session.execute(
                text("UPDATE inc_instance SET neo4j_node_id = :neo4j_node_id, updated_at = NOW() WHERE instance_id = :instance_id"),
                {"instance_id": instance_id, "neo4j_node_id": neo4j_node_id}
            )
            session.commit()
            return result.rowcount > 0
    
    def get_instances(self, class_id: Optional[str] = None, 
                     status: str = "active", 
                     limit: int = 100, 
                     offset: int = 0) -> List[Dict]:
        """获取实例列表"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_instance WHERE status = :status"
            params = {"status": status, "limit": limit, "offset": offset}
            if class_id:
                sql += " AND class_id = :class_id"
                params["class_id"] = class_id
            sql += " ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def get_instance_by_id(self, instance_id: str) -> Optional[Dict]:
        """根据ID获取实例"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            result = session.execute(
                text("SELECT * FROM inc_instance WHERE instance_id = :instance_id"),
                {"instance_id": instance_id}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    
    def get_instance_by_name(self, canonical_name: str, class_id: Optional[str] = None) -> Optional[Dict]:
        """根据规范名称获取实例"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT * FROM inc_instance WHERE canonical_name = :canonical_name AND status = 'active'"
            params = {"canonical_name": canonical_name}
            if class_id:
                sql += " AND class_id = :class_id"
                params["class_id"] = class_id
            result = session.execute(text(sql), params)
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    
    def count_instances(self, class_id: Optional[str] = None, status: str = "active") -> int:
        """统计实例数量"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            sql = "SELECT COUNT(*) as count FROM inc_instance WHERE status = :status"
            params = {"status": status}
            if class_id:
                sql += " AND class_id = :class_id"
                params["class_id"] = class_id
            result = session.execute(text(sql), params)
            row = result.fetchone()
            return row.count if row else 0
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self._connected:
            self.connect()
        
        with self.Session() as session:
            stats = {}
            
            result = session.execute(text(
                "SELECT category, COUNT(*) as count FROM inc_class GROUP BY category"
            ))
            stats["classes_by_category"] = {row.category: row.count for row in result}
            
            result = session.execute(text(
                "SELECT class_level, COUNT(*) as count FROM inc_class GROUP BY class_level"
            ))
            stats["classes_by_level"] = {row.class_level: row.count for row in result}
            
            result = session.execute(text(
                "SELECT c.category, COUNT(i.instance_id) as count "
                "FROM inc_class c LEFT JOIN inc_instance i ON c.class_id = i.class_id AND i.status = 'active' "
                "GROUP BY c.category"
            ))
            stats["instances_by_category"] = {row.category: row.count for row in result}
            
            result = session.execute(text(
                "SELECT relation_group, COUNT(*) as count FROM inc_relation GROUP BY relation_group"
            ))
            stats["relations_by_group"] = {row.relation_group: row.count for row in result}
            
            result = session.execute(text(
                "SELECT axiom_type, COUNT(*) as count FROM inc_axiom WHERE is_enabled=1 GROUP BY axiom_type"
            ))
            stats["axioms_by_type"] = {row.axiom_type: row.count for row in result}
            
            result = session.execute(text(
                "SELECT concept_type, COUNT(*) as count FROM inc_concept GROUP BY concept_type"
            ))
            stats["concepts_by_type"] = {row.concept_type: row.count for row in result}
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_class"))
            stats["total_classes"] = result.fetchone().count
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_relation"))
            stats["total_relations"] = result.fetchone().count
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_axiom WHERE is_enabled=1"))
            stats["total_axioms"] = result.fetchone().count
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_instance WHERE status='active'"))
            stats["total_instances"] = result.fetchone().count
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_property"))
            stats["total_properties"] = result.fetchone().count
            
            result = session.execute(text("SELECT COUNT(*) as count FROM inc_concept"))
            stats["total_concepts"] = result.fetchone().count
            
            return stats


ontology_db = OntologyDB()
