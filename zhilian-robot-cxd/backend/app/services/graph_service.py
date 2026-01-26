"""
业务服务 - 图谱构建服务
"""
from app.database.neo4j_db import neo4j_conn
from app.nlp import llm_processor
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class GraphService:
    """图谱构建服务"""
    
    def __init__(self):
        self.neo4j = neo4j_conn
    
    def save_analyzed_data(self, entities: Dict, relations: List[Dict]) -> Dict:
        """
        直接保存已分析的实体和关系到图谱
        
        Args:
            entities: 实体字典 {"companies": [...], "products": [...], ...}
            relations: 关系列表 [{"subject": "", "relation": "", "object": "", "confidence": 0.9}, ...]
            
        Returns:
            保存结果
        """
        try:
            logger.info(f"开始保存数据到图谱: {sum(len(v) for v in entities.values())} 个实体, {len(relations)} 个关系")
            
            # 1. 保存到 Neo4j
            self._save_to_graph(entities, relations)
            
            # 2. 保存到 MongoDB canonical_entities (用于动量计算)
            self._save_to_mongodb(entities)
            
            return {
                "success": True,
                "entities_count": sum(len(v) for v in entities.values()),
                "relations_count": len(relations)
            }
        except Exception as e:
            logger.error(f"保存到图谱失败: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def build_graph_from_text(self, text: str, use_llm: bool = True) -> Dict:
        """
        从文本构建图谱（使用DeepSeek LLM）
        
        Args:
            text: 输入文本
            use_llm: 保留参数以兼容旧接口（现在始终使用LLM）
            
        Returns:
            构建结果
        """
        try:
            # 使用DeepSeek LLM分析
            result = llm_processor.analyze_industry_chain(text)
            entities = result['entities']
            relations = result['relations']
            
            # 存入图数据库
            self._save_to_graph(entities, relations)
            
            return {
                "success": True,
                "entities_count": sum(len(v) for v in entities.values()),
                "relations_count": len(relations)
            }
        except Exception as e:
            logger.error(f"图谱构建失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _save_to_graph(self, entities: Dict, relations: List[Dict]):
        """保存实体和关系到Neo4j(智能合并,避免重复)"""
        # 创建实体节点 - 使用MERGE避免重复
        for category, items in entities.items():
            for item in items:
                self._merge_entity(item, category)
        
        # 创建关系 - 智能合并
        for relation in relations:
            self._merge_relation(relation)
    
    def _merge_entity(self, name: str, entity_type: str, confidence: float = 0.9):
        """
        智能合并实体节点
        - 如果不存在则创建
        - 如果已存在则更新置信度和时间戳
        """
        query = """
        MERGE (e:Entity {name: $name})
        ON CREATE SET
            e.type = $type,
            e.confidence = $confidence,
            e.created_at = datetime(),
            e.updated_at = datetime(),
            e.occurrence_count = 1
        ON MATCH SET
            e.updated_at = datetime(),
            e.occurrence_count = e.occurrence_count + 1,
            e.confidence = CASE
                WHEN $confidence > e.confidence THEN $confidence
                ELSE e.confidence
            END
        RETURN e
        """
        self.neo4j.execute_write(query, {
            "name": name,
            "type": entity_type,
            "confidence": confidence
        })
    
    def _save_to_mongodb(self, entities: Dict):
        """
        保存实体到 MongoDB canonical_entities 集合
        用于动量计算和实体管理
        
        注意：每次保存文档引用的实体时，都会增加引用计数
        """
        from app.database.mongodb import canonical_entity_manager
        
        for category, items in entities.items():
            # Use lowercase category to match MongoDB entity IDs
            # This ensures consistency with document_instances
            for item_name in items:
                # 生成实体ID (使用小写category)
                entity_id = f"CANONICAL_{category}_{item_name}"
                
                # 创建或更新实体
                canonical_entity_manager.create_or_update_entity(
                    entity_id=entity_id,
                    entity_type=category,
                    names=[item_name],
                    momentum=0.0  # 初始动量为0，需要后续计算
                )
                
                # 增加引用计数（每次处理文档都计数一次）
                canonical_entity_manager.increment_reference_count(entity_id)
    
    def _merge_relation(self, relation: Dict):
        """
        智能合并关系
        - 如果不存在则创建
        - 如果已存在则更新置信度(取平均值)
        """
        # 将关系类型转换为有效的Neo4j关系类型(移除空格和特殊字符)
        relation_type = relation.get("relation", "RELATION")
        relation_label = relation_type
        relation_type_safe = relation_type.replace(" ", "_").replace("-", "_").upper()
        
        query = f"""
        MATCH (a:Entity {{name: $subject}})
        MATCH (b:Entity {{name: $object}})
        MERGE (a)-[r:{relation_type_safe}]->(b)
        ON CREATE SET
            r.label = $label,
            r.confidence = $confidence,
            r.created_at = datetime(),
            r.updated_at = datetime(),
            r.occurrence_count = 1
        ON MATCH SET
            r.updated_at = datetime(),
            r.occurrence_count = r.occurrence_count + 1,
            r.confidence = (r.confidence + $confidence) / 2
        RETURN r
        """
        
        self.neo4j.execute_write(query, {
            "subject": relation.get("subject"),
            "object": relation.get("object"),
            "label": relation_label,
            "confidence": relation.get("confidence", 0.9)
        })
    
    def query_industry_chain(self, company_name: str, depth: int = 2) -> Dict:
        """
        查询企业的产业链关系
        
        Args:
            company_name: 企业名称(支持模糊匹配)
            depth: 查询深度
            
        Returns:
            图谱数据
        """
        logger.info(f"查询企业: {company_name}, 深度: {depth}")
        
        # 使用模糊匹配查询,支持部分企业名称
        query = f"""
        MATCH path = (n:Entity)-[*1..{depth}]-(m:Entity)
        WHERE n.name CONTAINS $company OR n.name = $company
        RETURN n, m, relationships(path) as rels
        LIMIT 100
        """
        
        try:
            result = self.neo4j.execute_query(query, {"company": company_name})
            logger.info(f"查询返回 {len(result)} 条记录")
            
            # 打印第一条记录用于调试
            if result:
                logger.info(f"第一条记录: {result[0]}")
            else:
                # 如果没有结果,查看所有节点名称
                all_nodes_query = "MATCH (n:Entity) RETURN n.name as name LIMIT 10"
                all_nodes = self.neo4j.execute_query(all_nodes_query)
                logger.info(f"数据库中的节点: {all_nodes}")
            
            return self._format_graph_data(result)
        except Exception as e:
            logger.error(f"查询失败: {str(e)}", exc_info=True)
            return {"nodes": [], "edges": []}
    
    def _format_graph_data(self, raw_data: List) -> Dict:
        """格式化图谱数据（包含动量信息）"""
        from app.database.mongodb import mongodb_conn
        
        nodes = []
        edges = []
        node_set = set()
        
        for record in raw_data:
            # 提取节点 n 和 m
            for key in ['n', 'm']:
                if key in record and record[key]:
                    node_data = record[key]
                    node_id = node_data.get('name')
                    if node_id and node_id not in node_set:
                        node_type = node_data.get('type', 'unknown')
                        
                        # 从MongoDB获取动量信息
                        entity_id = f"CANONICAL_{node_type}_{node_id}"
                        canonical_entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
                        
                        # 调试日志
                        logger.info(f"查询节点: {node_id}, 类型: {node_type}, 实体ID: {entity_id}, 找到: {canonical_entity is not None}")
                        if canonical_entity:
                            logger.info(f"  动量值: {canonical_entity.get('current_momentum')}, 引用: {canonical_entity.get('reference_count')}")
                        
                        # 提取动量值和引用次数
                        current_momentum = 0.0
                        reference_count = 0
                        if canonical_entity:
                            current_momentum = canonical_entity.get('current_momentum', 0.0)
                            reference_count = canonical_entity.get('reference_count', 0)
                        
                        nodes.append({
                            "id": node_id,
                            "name": node_id,
                            "type": node_type,
                            "current_momentum": current_momentum,
                            "reference_count": reference_count
                        })
                        node_set.add(node_id)
            
            # 提取关系
            if 'rels' in record and record['rels']:
                rels = record['rels']
                # rels 可能是列表
                if not isinstance(rels, list):
                    rels = [rels]
                
                for rel in rels:
                    # 处理关系对象
                    if hasattr(rel, 'type') and hasattr(rel, 'start_node') and hasattr(rel, 'end_node'):
                        # 优先使用label属性(原始关系名称),否则使用type
                        rel_dict = dict(rel)
                        relation_label = rel_dict.get('label', rel.type)
                        
                        edges.append({
                            "source": dict(rel.start_node)['name'],
                            "target": dict(rel.end_node)['name'],
                            "relation": relation_label,
                            "confidence": rel_dict.get('confidence', 0.9)
                        })
        
        logger.info(f"格式化结果: {len(nodes)} 个节点, {len(edges)} 条边")
        return {"nodes": nodes, "edges": edges}
    
    def get_entity_neighbors(self, entity_id: str, depth: int = 1) -> List[Dict]:
        """
        获取实体的关联关系
        
        Args:
            entity_id: 实体ID（在Neo4j中对应name属性）
            depth: 关系深度（1表示直接关联，2表示二度关联等）
            
        Returns:
            关联关系列表
        """
        try:
            # 查询指定深度的关联关系
            query = f"""
            MATCH path = (e:Entity {{name: $entity_id}})-[*1..{depth}]-(related:Entity)
            WITH relationships(path) as rels, related
            UNWIND rels as r
            RETURN DISTINCT 
                startNode(r).name as source,
                type(r) as relation,
                endNode(r).name as target,
                r.confidence as confidence,
                r.label as label
            LIMIT 100
            """
            
            results = self.neo4j.execute_query(query, {"entity_id": entity_id})
            
            relations = []
            for record in results:
                relations.append({
                    "source": record.get('source'),
                    "target": record.get('target'),
                    "relation": record.get('label') or record.get('relation'),
                    "confidence": record.get('confidence', 0.9)
                })
            
            logger.info(f"获取实体 {entity_id} 的关联关系: {len(relations)} 条")
            return relations
            
        except Exception as e:
            logger.error(f"获取实体关联关系失败: {e}", exc_info=True)
            return []
    
    def get_graph_statistics(self) -> Dict:
        """获取图谱统计信息"""
        try:
            # 统计节点数
            node_count_query = "MATCH (n:Entity) RETURN count(n) as count"
            node_result = self.neo4j.execute_query(node_count_query)
            node_count = node_result[0]['count'] if node_result else 0
            
            # 统计关系数
            rel_count_query = "MATCH ()-[r]->() RETURN count(r) as count"
            rel_result = self.neo4j.execute_query(rel_count_query)
            rel_count = rel_result[0]['count'] if rel_result else 0
            
            return {
                "node_count": node_count,
                "relation_count": rel_count
            }
        except Exception as e:
            logger.error(f"统计查询失败: {str(e)}")
            return {"node_count": 0, "relation_count": 0}


# 全局服务实例
graph_service = GraphService()
