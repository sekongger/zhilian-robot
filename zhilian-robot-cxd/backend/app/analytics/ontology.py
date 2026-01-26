"""
本体管理器（Ontology Manager）
管理实体同义词、别名、规范化映射
基于Recorded Future的实体标准化理念
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
from app.database.mongodb import mongodb_conn
import asyncio
from difflib import SequenceMatcher


class OntologyManager:
    """
    本体管理器
    负责实体的同义词管理、别名映射、规范化处理
    """
    
    def __init__(self):
        """初始化本体管理器"""
        # 获取数据库实例
        db = mongodb_conn.get_collection("entity_synonyms").database
        # 同义词映射集合
        self.synonyms_collection = db["entity_synonyms"]
        # 实体类型本体集合
        self.type_ontology_collection = db["entity_type_ontology"]
        # 索引将在首次使用时创建
    
    async def _ensure_indexes(self):
        """确保索引存在"""
        await self.synonyms_collection.create_index("canonical_name")
        await self.synonyms_collection.create_index("synonyms")
        await self.type_ontology_collection.create_index("type_name")
    
    async def register_synonym(
        self,
        canonical_name: str,
        synonym: str,
        entity_type: str,
        confidence: float = 1.0,
        source: str = "manual"
    ) -> bool:
        """
        注册实体同义词
        
        Args:
            canonical_name: 标准名称
            synonym: 同义词/别名
            entity_type: 实体类型
            confidence: 置信度（0-1）
            source: 来源（manual, llm, fuzzy_match）
            
        Returns:
            是否成功注册
        """
        # 检查是否已存在
        existing = await self.synonyms_collection.find_one({
            "canonical_name": canonical_name
        })
        
        if existing:
            # 更新现有记录，添加新同义词
            if synonym not in existing.get("synonyms", []):
                await self.synonyms_collection.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$push": {"synonyms": synonym},
                        "$set": {"last_updated": datetime.now()}
                    }
                )
                return True
            return False  # 同义词已存在
        else:
            # 创建新记录
            synonym_doc = {
                "canonical_name": canonical_name,
                "entity_type": entity_type,
                "synonyms": [synonym] if synonym != canonical_name else [],
                "confidence": confidence,
                "source": source,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            await self.synonyms_collection.insert_one(synonym_doc)
            return True
    
    async def get_canonical_name(
        self,
        name: str,
        entity_type: Optional[str] = None,
        fuzzy_threshold: float = 0.85
    ) -> Optional[str]:
        """
        获取实体的标准名称
        支持精确匹配和模糊匹配
        
        Args:
            name: 实体名称
            entity_type: 实体类型（用于过滤）
            fuzzy_threshold: 模糊匹配阈值
            
        Returns:
            标准名称，如果未找到返回None
        """
        # 1. 精确匹配标准名称
        query = {"canonical_name": name}
        if entity_type:
            query["entity_type"] = entity_type
        
        result = await self.synonyms_collection.find_one(query)
        if result:
            return result["canonical_name"]
        
        # 2. 精确匹配同义词
        query = {"synonyms": name}
        if entity_type:
            query["entity_type"] = entity_type
        
        result = await self.synonyms_collection.find_one(query)
        if result:
            return result["canonical_name"]
        
        # 3. 模糊匹配
        candidates = await self.synonyms_collection.find(
            {"entity_type": entity_type} if entity_type else {}
        ).to_list(length=1000)
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # 与标准名称比较
            score = self._similarity(name, candidate["canonical_name"])
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = candidate["canonical_name"]
            
            # 与同义词比较
            for syn in candidate.get("synonyms", []):
                score = self._similarity(name, syn)
                if score > best_score and score >= fuzzy_threshold:
                    best_score = score
                    best_match = candidate["canonical_name"]
        
        return best_match
    
    async def get_all_synonyms(
        self,
        canonical_name: str
    ) -> List[str]:
        """
        获取实体的所有同义词
        
        Args:
            canonical_name: 标准名称
            
        Returns:
            同义词列表（包含标准名称）
        """
        result = await self.synonyms_collection.find_one({
            "canonical_name": canonical_name
        })
        
        if result:
            synonyms = [canonical_name] + result.get("synonyms", [])
            return list(set(synonyms))  # 去重
        
        return [canonical_name]
    
    async def merge_entities(
        self,
        source_name: str,
        target_canonical_name: str,
        entity_type: str
    ) -> bool:
        """
        合并实体（将source_name作为target的同义词）
        
        Args:
            source_name: 源实体名称
            target_canonical_name: 目标标准名称
            entity_type: 实体类型
            
        Returns:
            是否成功合并
        """
        # 检查源实体是否已有同义词映射
        source_doc = await self.synonyms_collection.find_one({
            "$or": [
                {"canonical_name": source_name},
                {"synonyms": source_name}
            ]
        })
        
        if source_doc:
            # 源实体已存在映射，需要合并所有同义词
            all_synonyms = [source_doc["canonical_name"]] + source_doc.get("synonyms", [])
            
            # 将所有同义词添加到目标
            for syn in all_synonyms:
                if syn != target_canonical_name:
                    await self.register_synonym(
                        canonical_name=target_canonical_name,
                        synonym=syn,
                        entity_type=entity_type,
                        source="merge"
                    )
            
            # 删除源文档
            await self.synonyms_collection.delete_one({"_id": source_doc["_id"]})
        else:
            # 源实体无映射，直接添加为同义词
            await self.register_synonym(
                canonical_name=target_canonical_name,
                synonym=source_name,
                entity_type=entity_type,
                source="merge"
            )
        
        return True
    
    async def auto_discover_synonyms(
        self,
        entity_name: str,
        entity_type: str,
        context_text: str
    ) -> List[Dict]:
        """
        使用LLM自动发现实体的同义词
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型
            context_text: 上下文文本
            
        Returns:
            发现的同义词列表
        """
        try:
            # 使用LLM提取潜在同义词
            prompt = f"""
请分析以下文本，找出"{entity_name}"（类型: {entity_type}）的所有可能同义词、别名或指代：

{context_text}

只返回JSON格式的同义词列表：
{{"synonyms": ["同义词1", "同义词2", ...]}}
"""
            
            # 这里需要调用LLM（简化实现）
            # 在生产环境中应调用app.nlp.llm模块
            discovered_synonyms = []
            
            # TODO: 实现LLM调用
            # result = await call_llm(prompt)
            # discovered_synonyms = parse_llm_result(result)
            
            return discovered_synonyms
            
        except Exception as e:
            print(f"自动发现同义词失败: {str(e)}")
            return []
    
    async def register_type_hierarchy(
        self,
        parent_type: str,
        child_types: List[str]
    ):
        """
        注册实体类型层次结构
        
        Args:
            parent_type: 父类型
            child_types: 子类型列表
            
        示例：
            parent_type="organization"
            child_types=["company", "ngo", "government_agency"]
        """
        existing = await self.type_ontology_collection.find_one({
            "type_name": parent_type
        })
        
        if existing:
            await self.type_ontology_collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "child_types": child_types,
                        "last_updated": datetime.now()
                    }
                }
            )
        else:
            type_doc = {
                "type_name": parent_type,
                "child_types": child_types,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            await self.type_ontology_collection.insert_one(type_doc)
    
    async def get_type_hierarchy(self) -> Dict[str, List[str]]:
        """
        获取完整的类型层次结构
        
        Returns:
            类型层次字典
        """
        hierarchy = {}
        docs = await self.type_ontology_collection.find({}).to_list(length=1000)
        
        for doc in docs:
            hierarchy[doc["type_name"]] = doc.get("child_types", [])
        
        return hierarchy
    
    async def normalize_entity_batch(
        self,
        entities: List[Dict]
    ) -> List[Dict]:
        """
        批量规范化实体名称
        
        Args:
            entities: 实体列表，每个包含name和type字段
            
        Returns:
            规范化后的实体列表，添加canonical_name字段
        """
        normalized = []
        
        for entity in entities:
            name = entity.get("name")
            entity_type = entity.get("type")
            
            if not name:
                continue
            
            canonical = await self.get_canonical_name(name, entity_type)
            
            normalized.append({
                **entity,
                "canonical_name": canonical if canonical else name,
                "is_normalized": canonical is not None
            })
        
        return normalized
    
    def _similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度（0-1）
        使用SequenceMatcher算法
        """
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    async def get_statistics(self) -> Dict:
        """
        获取本体管理统计信息
        
        Returns:
            统计数据
        """
        total_mappings = await self.synonyms_collection.count_documents({})
        
        # 统计每种类型的映射数
        type_counts = {}
        docs = await self.synonyms_collection.find({}).to_list(length=10000)
        
        total_synonyms = 0
        for doc in docs:
            entity_type = doc.get("entity_type", "unknown")
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            total_synonyms += len(doc.get("synonyms", []))
        
        return {
            "total_canonical_entities": total_mappings,
            "total_synonyms": total_synonyms,
            "average_synonyms_per_entity": total_synonyms / total_mappings if total_mappings > 0 else 0,
            "entity_types": type_counts,
            "type_hierarchy_count": await self.type_ontology_collection.count_documents({})
        }


# 初始化默认类型层次结构
async def initialize_default_ontology():
    """初始化默认的实体类型本体"""
    ontology_mgr = OntologyManager()
    
    # 定义默认类型层次
    default_hierarchy = {
        "person": ["politician", "entrepreneur", "celebrity", "scientist"],
        "organization": ["company", "ngo", "government_agency", "university"],
        "location": ["country", "city", "landmark", "region"],
        "event": ["political_event", "economic_event", "disaster", "conference"],
        "product": ["software", "hardware", "service", "brand"]
    }
    
    for parent, children in default_hierarchy.items():
        await ontology_mgr.register_type_hierarchy(parent, children)
    
    print("默认实体类型本体已初始化")


# 使用示例
async def example_usage():
    """使用示例"""
    ontology_mgr = OntologyManager()
    
    # 注册同义词
    await ontology_mgr.register_synonym(
        canonical_name="阿里巴巴集团",
        synonym="阿里",
        entity_type="organization",
        confidence=0.95,
        source="manual"
    )
    
    await ontology_mgr.register_synonym(
        canonical_name="阿里巴巴集团",
        synonym="Alibaba",
        entity_type="organization",
        confidence=0.98,
        source="manual"
    )
    
    # 获取标准名称
    canonical = await ontology_mgr.get_canonical_name("阿里", "organization")
    print(f"'阿里' 的标准名称: {canonical}")
    
    # 获取所有同义词
    synonyms = await ontology_mgr.get_all_synonyms("阿里巴巴集团")
    print(f"所有同义词: {synonyms}")
    
    # 统计信息
    stats = await ontology_mgr.get_statistics()
    print(f"本体统计: {stats}")


if __name__ == "__main__":
    # 初始化默认本体
    asyncio.run(initialize_default_ontology())
    
    # 运行示例
    asyncio.run(example_usage())
