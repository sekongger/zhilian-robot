"""
本体标注服务
用于将NLP提取的实体注册到本体实例表
"""
import logging
from typing import Dict, List, Optional
from app.database.mysql_ontology_db import ontology_db

logger = logging.getLogger(__name__)

# 实体类型到本体类的映射
ENTITY_TYPE_TO_CLASS = {
    "COMPANY": "CLS_ENTERPRISE",
    "companies": "CLS_ENTERPRISE",
    "PERSON": "CLS_PERSON",
    "persons": "CLS_PERSON",
    "PRODUCT": "CLS_PRODUCT",
    "products": "CLS_PRODUCT",
    "TECHNOLOGY": "CLS_TECHNOLOGY",
    "technologies": "CLS_TECHNOLOGY",
    "LOCATION": "CLS_SPACE",
    "locations": "CLS_SPACE",
    "TIME": "CLS_TIME",
    "ORGANIZATION": "CLS_ACTOR",
    "GOVERNMENT": "CLS_GOVERNMENT",
    "RESEARCH_INST": "CLS_RESEARCH_INST",
    "FINANCIAL_INST": "CLS_FINANCIAL_INST",
}

# 文档类型到本体类的映射
DOCUMENT_TYPE_TO_CLASS = {
    "news": "CLS_NEWS_DOC",
    "policy": "CLS_POLICY_DOC",
    "research": "CLS_RESEARCH_DOC",
    "patent": "CLS_PATENT_DOC",
    "standard": "CLS_DOCUMENT",
    "credential": "CLS_DOCUMENT",
}


class OntologyAnnotator:
    """本体标注器"""
    
    def __init__(self):
        self._initialized = False
    
    def _ensure_connected(self):
        """确保数据库连接"""
        if not self._initialized:
            try:
                ontology_db.connect()
                self._initialized = True
            except Exception as e:
                logger.warning(f"本体数据库连接失败: {e}")
                return False
        return ontology_db.is_connected()
    
    def annotate_entities(self, entities: Dict, document_type: str = "news") -> List[Dict]:
        """
        对NLP抽取结果进行本体标注
        
        Args:
            entities: NLP提取的实体字典，格式如 {"companies": ["华为", "小米"], "products": [...]}
            document_type: 文档类型
            
        Returns:
            标注后的实体列表
        """
        if not self._ensure_connected():
            logger.warning("本体数据库未连接，跳过本体标注")
            return []
        
        annotated = []
        
        for entity_type, entity_list in entities.items():
            if not isinstance(entity_list, list):
                continue
                
            class_id = ENTITY_TYPE_TO_CLASS.get(entity_type, "CLS_OBJECT")
            
            for entity_name in entity_list:
                if not entity_name or not isinstance(entity_name, str):
                    continue
                    
                try:
                    instance_id = ontology_db.register_instance(
                        class_id=class_id,
                        canonical_name=entity_name.strip()
                    )
                    annotated.append({
                        "instance_id": instance_id,
                        "class_id": class_id,
                        "name": entity_name.strip(),
                        "entity_type": entity_type
                    })
                    logger.debug(f"实体标注成功: {entity_name} -> {class_id}")
                except Exception as e:
                    logger.error(f"实体标注失败 {entity_name}: {e}")
        
        logger.info(f"本体标注完成，共标注 {len(annotated)} 个实体")
        return annotated
    
    def annotate_document(self, title: str, document_type: str = "news", 
                         mongodb_doc_id: Optional[str] = None) -> Optional[str]:
        """
        对文档进行本体标注
        
        Args:
            title: 文档标题
            document_type: 文档类型
            mongodb_doc_id: MongoDB文档ID
            
        Returns:
            实例ID
        """
        if not self._ensure_connected():
            logger.warning("本体数据库未连接，跳过文档标注")
            return None
        
        class_id = DOCUMENT_TYPE_TO_CLASS.get(document_type, "CLS_DOCUMENT")
        
        try:
            instance_id = ontology_db.register_instance(
                class_id=class_id,
                canonical_name=title.strip(),
                mongodb_doc_id=mongodb_doc_id
            )
            logger.info(f"文档标注成功: {title[:50]}... -> {class_id}")
            return instance_id
        except Exception as e:
            logger.error(f"文档标注失败 {title[:50]}...: {e}")
            return None
    
    def update_neo4j_mapping(self, instance_id: str, neo4j_node_id: int) -> bool:
        """
        更新实例的Neo4j节点ID映射
        
        Args:
            instance_id: 本体实例ID
            neo4j_node_id: Neo4j节点ID
            
        Returns:
            是否更新成功
        """
        if not self._ensure_connected():
            return False
        
        try:
            return ontology_db.update_instance_neo4j_id(instance_id, neo4j_node_id)
        except Exception as e:
            logger.error(f"更新Neo4j映射失败: {e}")
            return False
    
    def get_class_for_entity_type(self, entity_type: str) -> str:
        """
        获取实体类型对应的本体类ID
        
        Args:
            entity_type: 实体类型
            
        Returns:
            本体类ID
        """
        return ENTITY_TYPE_TO_CLASS.get(entity_type, "CLS_OBJECT")
    
    def get_class_for_document_type(self, document_type: str) -> str:
        """
        获取文档类型对应的本体类ID
        
        Args:
            document_type: 文档类型
            
        Returns:
            本体类ID
        """
        return DOCUMENT_TYPE_TO_CLASS.get(document_type, "CLS_DOCUMENT")
    
    def get_instance_by_name(self, name: str, class_id: Optional[str] = None) -> Optional[Dict]:
        """
        根据名称查找实例
        
        Args:
            name: 实体名称
            class_id: 可选的类ID过滤
            
        Returns:
            实例信息
        """
        if not self._ensure_connected():
            return None
        
        try:
            return ontology_db.get_instance_by_name(name, class_id)
        except Exception as e:
            logger.error(f"查找实例失败: {e}")
            return None


# 全局本体标注器实例
ontology_annotator = OntologyAnnotator()
