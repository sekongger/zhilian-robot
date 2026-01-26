"""
规范化服务 - 实现Recorded Future的实体规范化理念
"""
from app.database.mongodb import canonical_entity_manager, document_instance_manager
from app.database.neo4j_db import neo4j_conn
from typing import Dict, List, Optional
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)


class CanonicalizationService:
    """实体规范化服务"""
    
    def __init__(self):
        self.mongo_entity_mgr = canonical_entity_manager
        self.neo4j = neo4j_conn
        
        # 同义词映射缓存
        self.synonym_cache = {}
    
    def canonicalize_entity(self, entity_name: str, entity_type: str) -> str:
        """
        将实体名称规范化为唯一的规范ID
        
        Args:
            entity_name: 原始实体名称
            entity_type: 实体类型
            
        Returns:
            canonical_id: 规范实体ID (如 "CANONICAL_华为")
        """
        # 1. 清理实体名称
        cleaned_name = self._clean_entity_name(entity_name)
        
        # 2. 检查是否已存在同义词映射
        canonical_entity = self.mongo_entity_mgr.find_by_name(cleaned_name)
        
        if canonical_entity:
            # 已存在，返回现有ID
            canonical_id = canonical_entity['_id']
            logger.debug(f"找到已存在实体: {cleaned_name} -> {canonical_id}")
            return canonical_id
        
        # 3. 尝试通过相似度匹配查找同义词
        similar_entity_id = self._find_similar_entity(cleaned_name, entity_type)
        
        if similar_entity_id:
            # 找到相似实体，添加为同义词
            self.mongo_entity_mgr.add_synonym(similar_entity_id, cleaned_name)
            logger.info(f"将 {cleaned_name} 添加为 {similar_entity_id} 的同义词")
            return similar_entity_id
        
        # 4. 创建新的规范实体
        canonical_id = self._generate_canonical_id(cleaned_name, entity_type)
        self.mongo_entity_mgr.create_or_update_entity(
            entity_id=canonical_id,
            entity_type=entity_type,
            names=[cleaned_name]
        )
        
        logger.info(f"创建新规范实体: {canonical_id} ({cleaned_name})")
        return canonical_id
    
    def _clean_entity_name(self, name: str) -> str:
        """清理实体名称（去除空格、标点等）"""
        cleaned = name.strip()
        # 移除常见后缀
        suffixes = ['公司', '有限公司', '股份有限公司', 'Ltd', 'Inc', 'Corporation', 'Corp']
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        return cleaned
    
    def _find_similar_entity(self, name: str, entity_type: str) -> Optional[str]:
        """
        通过相似度查找已存在的同义实体
        
        优先查找完全相同的名称（忽略类型差异），避免重复实体
        然后在同类型中查找相似实体
        """
        from app.database.mongodb import mongodb_conn
        
        # 1. 首先查找名称完全匹配的实体（不限类型，避免重复）
        exact_match = mongodb_conn.find_one(
            'canonical_entities',
            {'names': name}
        )
        
        if exact_match:
            logger.info(f"找到名称完全匹配的实体: {name} -> {exact_match['_id']} (类型: {exact_match.get('type')})")
            # 如果类型不同，保留已有类型，避免重复
            if exact_match.get('type') != entity_type:
                logger.warning(f"实体 {name} 存在类型冲突: 已有{exact_match.get('type')}，新请求{entity_type}，保留已有类型")
            return exact_match['_id']
        
        # 2. 然后查找相似实体（限定同类型）
        entities = mongodb_conn.find_many(
            'canonical_entities',
            {'type': entity_type}
        )
        
        for entity in entities:
            # 检查是否有任何同义词与当前名称相似
            for synonym in entity.get('names', []):
                if self._is_similar(name, synonym):
                    return entity['_id']
        
        return None
    
    def _is_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """
        判断两个名称是否相似
        
        简单实现：检查是否互相包含
        高级实现可使用：Levenshtein距离、Jaro-Winkler距离或BERT语义相似度
        """
        # 互相包含判断
        if name1 in name2 or name2 in name1:
            return True
        
        # 字符重叠率判断
        set1 = set(name1)
        set2 = set(name2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return False
        
        similarity = intersection / union
        return similarity >= threshold
    
    def _generate_canonical_id(self, name: str, entity_type: str) -> str:
        """生成规范实体ID"""
        # 使用类型前缀 + 名称
        return f"CANONICAL_{entity_type}_{name}"
    
    def save_canonical_graph(self, entities: Dict[str, List[str]], 
                            relations: List[Dict],
                            source_id: str,
                            source_credibility: float = 0.5) -> Dict:
        """
        保存规范化的图谱数据
        
        Args:
            entities: 实体字典 {"companies": ["华为", "Huawei"], ...}
            relations: 关系列表
            source_id: 数据源ID
            source_credibility: 数据源可信度
            
        Returns:
            保存结果统计
        """
        canonical_entities = {}
        entity_references = []
        
        # 1. 规范化所有实体
        for entity_type, entity_names in entities.items():
            for name in entity_names:
                canonical_id = self.canonicalize_entity(name, entity_type)
                canonical_entities[name] = canonical_id
                
                # 记录实体引用
                entity_references.append({
                    'entity_id': canonical_id,
                    'mention': name,
                    'confidence': 0.9
                })
                
                # 增加引用计数
                self.mongo_entity_mgr.increment_reference_count(canonical_id)
                
                # 在Neo4j中创建或更新节点
                self.neo4j.create_canonical_entity(
                    entity_id=canonical_id,
                    name=name,
                    entity_type=entity_type
                )
        
        # 2. 规范化关系
        canonical_relations = []
        for relation in relations:
            subject = relation.get('subject')
            obj = relation.get('object')
            
            # 获取规范ID
            canonical_subject = canonical_entities.get(subject)
            canonical_object = canonical_entities.get(obj)
            
            if canonical_subject and canonical_object:
                # 创建时间化关系
                self.neo4j.create_temporal_relation(
                    source_id=canonical_subject,
                    target_id=canonical_object,
                    relation_type=relation.get('relation', 'RELATED'),
                    confidence=relation.get('confidence', 0.9)
                )
                
                canonical_relations.append({
                    'subject': canonical_subject,
                    'object': canonical_object,
                    'relation': relation.get('relation'),
                    'confidence': relation.get('confidence', 0.9)
                })
        
        logger.info(f"规范化完成: {len(canonical_entities)} 实体, {len(canonical_relations)} 关系")
        
        return {
            'success': True,
            'canonical_entities_count': len(canonical_entities),
            'canonical_relations_count': len(canonical_relations),
            'entity_references': entity_references
        }
    
    def merge_duplicate_entities(self, entity_id_1: str, entity_id_2: str) -> bool:
        """
        合并重复实体
        
        Args:
            entity_id_1: 保留的实体ID
            entity_id_2: 被合并的实体ID
            
        Returns:
            是否成功
        """
        try:
            # 1. 获取两个实体的信息
            from app.database.mongodb import mongodb_conn
            entity1 = mongodb_conn.find_one('canonical_entities', {'_id': entity_id_1})
            entity2 = mongodb_conn.find_one('canonical_entities', {'_id': entity_id_2})
            
            if not entity1 or not entity2:
                logger.error("实体不存在")
                return False
            
            # 2. 合并同义词
            merged_names = list(set(entity1.get('names', []) + entity2.get('names', [])))
            
            # 3. 合并引用计数
            merged_count = entity1.get('reference_count', 0) + entity2.get('reference_count', 0)
            
            # 4. 更新entity1
            mongodb_conn.update_one(
                'canonical_entities',
                {'_id': entity_id_1},
                {
                    '$set': {
                        'names': merged_names,
                        'reference_count': merged_count,
                        'last_updated': datetime.now()
                    }
                }
            )
            
            # 5. 在Neo4j中重定向所有entity2的关系到entity1
            redirect_query = f"""
            // 重定向出边
            MATCH (old:CanonicalEntity {{id: $old_id}})-[r]->(target)
            MATCH (new:CanonicalEntity {{id: $new_id}})
            CREATE (new)-[r2:{{type: type(r)}}]->(target)
            SET r2 = properties(r)
            DELETE r
            
            // 重定向入边
            WITH old, new
            MATCH (source)-[r]->(old)
            CREATE (source)-[r2:{{type: type(r)}}]->(new)
            SET r2 = properties(r)
            DELETE r
            
            // 删除旧节点
            DELETE old
            """
            
            self.neo4j.execute_write(redirect_query, {
                'old_id': entity_id_2,
                'new_id': entity_id_1
            })
            
            # 6. 删除entity2
            mongodb_conn.delete_many('canonical_entities', {'_id': entity_id_2})
            
            logger.info(f"成功合并实体: {entity_id_2} -> {entity_id_1}")
            return True
            
        except Exception as e:
            logger.error(f"合并实体失败: {e}", exc_info=True)
            return False


# 全局服务实例
canonicalization_service = CanonicalizationService()
