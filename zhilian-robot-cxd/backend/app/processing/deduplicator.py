"""
数据去重器 - 基于内容指纹的去重
"""
import re
import logging
import hashlib
from typing import List, Set, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    数据去重器
    
    使用SimHash和精确哈希结合的方式进行去重
    """
    
    def __init__(self, hash_bits: int = 64, threshold: float = 0.9):
        """
        初始化去重器
        
        Args:
            hash_bits: SimHash的位数
            threshold: 相似度阈值(0-1)，超过此值认为是重复
        """
        self.hash_bits = hash_bits
        self.threshold = threshold
        
        # 缓存已见过的指纹 (用于快速查找)
        self._exact_hashes: Set[str] = set()
        self._simhashes: List[Tuple[int, str, datetime]] = []  # (simhash, record_id, timestamp)
    
    def compute_fingerprint(self, content: str) -> str:
        """
        计算内容的精确指纹(MD5)
        
        Args:
            content: 文本内容
            
        Returns:
            MD5指纹
        """
        if not content:
            return ""
        
        # 预处理: 移除空白和标点，转小写
        normalized = self._normalize_for_hash(content)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def compute_simhash(self, content: str) -> int:
        """
        计算内容的SimHash
        
        SimHash用于检测近似重复
        
        Args:
            content: 文本内容
            
        Returns:
            SimHash值
        """
        if not content:
            return 0
        
        try:
            from simhash import Simhash
            return Simhash(self._get_features(content)).value
        except ImportError:
            # 如果simhash库未安装，使用简化实现
            return self._simple_simhash(content)
    
    def _simple_simhash(self, content: str) -> int:
        """简化的SimHash实现"""
        features = self._get_features(content)
        
        v = [0] * self.hash_bits
        for feature in features:
            h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            for i in range(self.hash_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] >= 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    def _get_features(self, content: str) -> List[str]:
        """
        提取文本特征(用于SimHash)
        
        使用n-gram作为特征
        """
        # 预处理
        content = self._normalize_for_hash(content)
        
        # 分词 (简单按字符分割，也可以使用jieba)
        tokens = list(content)
        
        # 生成n-gram (使用bigram和trigram)
        features = []
        for n in [2, 3]:
            for i in range(len(tokens) - n + 1):
                features.append(''.join(tokens[i:i+n]))
        
        return features
    
    def _normalize_for_hash(self, content: str) -> str:
        """规范化内容用于哈希计算"""
        # 移除空白
        content = re.sub(r'\s+', '', content)
        # 转小写
        content = content.lower()
        # 移除标点
        content = re.sub(r'[^\w\u4e00-\u9fff]', '', content)
        return content
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        计算两个SimHash的汉明距离
        
        Args:
            hash1: 第一个SimHash
            hash2: 第二个SimHash
            
        Returns:
            汉明距离
        """
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance
    
    def similarity(self, hash1: int, hash2: int) -> float:
        """
        计算两个SimHash的相似度
        
        Args:
            hash1: 第一个SimHash
            hash2: 第二个SimHash
            
        Returns:
            相似度(0-1)
        """
        distance = self.hamming_distance(hash1, hash2)
        return 1 - (distance / self.hash_bits)
    
    def is_duplicate(self, content: str, record_id: str = None) -> bool:
        """
        检查内容是否重复
        
        先检查精确匹配，再检查近似匹配
        
        Args:
            content: 文本内容
            record_id: 记录ID (用于排除自身)
            
        Returns:
            是否重复
        """
        if not content:
            return False
        
        # 1. 精确匹配检查
        exact_hash = self.compute_fingerprint(content)
        if exact_hash in self._exact_hashes:
            return True
        
        # 2. 近似匹配检查
        simhash = self.compute_simhash(content)
        
        for stored_hash, stored_id, _ in self._simhashes:
            if record_id and stored_id == record_id:
                continue
            
            sim = self.similarity(simhash, stored_hash)
            if sim >= self.threshold:
                logger.debug(f"发现近似重复: similarity={sim:.2f}")
                return True
        
        return False
    
    def add_fingerprint(self, content: str, record_id: str):
        """
        添加内容指纹到缓存
        
        Args:
            content: 文本内容
            record_id: 记录ID
        """
        if not content:
            return
        
        # 添加精确哈希
        exact_hash = self.compute_fingerprint(content)
        self._exact_hashes.add(exact_hash)
        
        # 添加SimHash
        simhash = self.compute_simhash(content)
        self._simhashes.append((simhash, record_id, datetime.now()))
    
    def find_near_duplicates(self, content: str, 
                            top_k: int = 5) -> List[Tuple[str, float]]:
        """
        查找近似重复的记录
        
        Args:
            content: 文本内容
            top_k: 返回最相似的K个
            
        Returns:
            [(record_id, similarity), ...]
        """
        if not content:
            return []
        
        simhash = self.compute_simhash(content)
        
        # 计算与所有已存储哈希的相似度
        similarities = []
        for stored_hash, record_id, _ in self._simhashes:
            sim = self.similarity(simhash, stored_hash)
            if sim >= 0.5:  # 至少50%相似才考虑
                similarities.append((record_id, sim))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def clean_old_fingerprints(self, max_age_days: int = 30):
        """
        清理过期的指纹
        
        Args:
            max_age_days: 保留的最大天数
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        original_count = len(self._simhashes)
        self._simhashes = [
            (h, rid, ts) for h, rid, ts in self._simhashes 
            if ts >= cutoff
        ]
        
        removed_count = original_count - len(self._simhashes)
        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个过期指纹")
    
    def load_from_mongodb(self, collection_name: str = "fingerprints"):
        """
        从MongoDB加载历史指纹
        
        Args:
            collection_name: 集合名称
        """
        try:
            from app.database.mongodb import mongodb_conn
            
            docs = mongodb_conn.find_many(
                collection_name,
                query={},
                limit=100000  # 限制加载数量
            )
            
            for doc in docs:
                if doc.get('exact_hash'):
                    self._exact_hashes.add(doc['exact_hash'])
                if doc.get('simhash'):
                    self._simhashes.append((
                        doc['simhash'],
                        doc.get('record_id', ''),
                        doc.get('created_at', datetime.now())
                    ))
            
            logger.info(f"从MongoDB加载了 {len(self._exact_hashes)} 个精确哈希, "
                       f"{len(self._simhashes)} 个SimHash")
                       
        except Exception as e:
            logger.error(f"加载指纹失败: {e}")
    
    def save_to_mongodb(self, content: str, record_id: str, 
                       collection_name: str = "fingerprints"):
        """
        保存指纹到MongoDB
        
        Args:
            content: 文本内容
            record_id: 记录ID
            collection_name: 集合名称
        """
        try:
            from app.database.mongodb import mongodb_conn
            
            doc = {
                'record_id': record_id,
                'exact_hash': self.compute_fingerprint(content),
                'simhash': self.compute_simhash(content),
                'created_at': datetime.now()
            }
            
            mongodb_conn.insert_one(collection_name, doc)
            
        except Exception as e:
            logger.error(f"保存指纹失败: {e}")
    
    def clear_cache(self):
        """清空内存缓存"""
        self._exact_hashes.clear()
        self._simhashes.clear()
        logger.info("指纹缓存已清空")


# 全局去重器实例
deduplicator = Deduplicator()
