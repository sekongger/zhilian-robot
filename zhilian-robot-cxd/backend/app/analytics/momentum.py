"""
动量计算引擎 - 基于Recorded Future的Momentum算法
"""
from app.database.mongodb import canonical_entity_manager, document_instance_manager, source_manager
from app.database.neo4j_db import neo4j_conn
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)


class MomentumEngine:
    """动量计算引擎"""
    
    # 媒体源黑名单 - 这些实体不应出现在动量排行榜中
    MEDIA_SOURCE_BLACKLIST = {
        '爱范儿', 'ifanr', 'iFanr',
        '新浪', '新浪财经', '新浪科技', 'sina',
        '36氪', '36kr',
        'IT之家', 'ithome',
    }
    
    def __init__(self):
        self.entity_mgr = canonical_entity_manager
        self.doc_mgr = document_instance_manager
        self.source_mgr = source_manager
        self.neo4j = neo4j_conn
        
        # 动量计算参数
        self.time_decay_days = 30  # 时间衰减周期（天）
        self.recency_weight = 0.5   # 时间权重
        self.credibility_weight = 0.3  # 可信度权重
        self.reference_weight = 0.2    # 引用权重
    
    def calculate_momentum(self, entity_id: str, time_point: datetime = None) -> float:
        """
        计算实体在指定时间点的动量
        
        Momentum(Entity, Time) = 
            Σ (Reference_Count × Source_Credibility × Recency_Weight × Co-occurrence_Boost)
        
        Args:
            entity_id: 规范实体ID
            time_point: 计算时间点，默认为当前时间
            
        Returns:
            动量值（0-1之间）
        """
        if time_point is None:
            time_point = datetime.now()
        
        try:
            # 1. 获取实体信息
            from app.database.mongodb import mongodb_conn
            entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
            
            if not entity:
                logger.warning(f"实体不存在: {entity_id}")
                return 0.0
            
            # 2. 获取时间窗口内的文档引用
            time_window_start = time_point - timedelta(days=self.time_decay_days)
            
            documents = mongodb_conn.find_many(
                'document_instances',
                {
                    'entity_references.entity_id': entity_id,
                    'created_at': {'$gte': time_window_start, '$lte': time_point}
                }
            )
            
            if not documents:
                logger.debug(f"实体 {entity_id} 在时间窗口内无引用")
                return 0.0
            
            # 3. 计算加权动量
            total_momentum = 0.0
            
            for doc in documents:
                # 获取数据源可信度
                source_id = doc.get('source_id', 'unknown')
                try:
                    credibility = self.source_mgr.get_credibility(source_id) if source_id else 0.8
                except:
                    # 如果source_id不是ObjectId格式，使用默认可信度
                    credibility = 0.8
                
                # 计算时间衰减因子（越新权重越高）
                doc_time = doc.get('created_at', time_point)
                days_ago = (time_point - doc_time).days
                recency_factor = self._calculate_recency_weight(days_ago)
                
                # 计算共现加成（与其他热门实体一起出现）
                co_occurrence_boost = self._calculate_co_occurrence_boost(doc, entity_id)
                
                # 加权求和
                doc_momentum = credibility * recency_factor * (1 + co_occurrence_boost)
                total_momentum += doc_momentum
            
            # 4. 归一化到[0, 1]
            # 使用对数函数防止极端值
            normalized_momentum = self._normalize_momentum(total_momentum)
            
            logger.info(f"实体 {entity_id} 动量计算完成: {normalized_momentum:.4f}")
            return normalized_momentum
            
        except Exception as e:
            logger.error(f"动量计算失败: {e}", exc_info=True)
            return 0.0
    
    def _calculate_recency_weight(self, days_ago: int) -> float:
        """
        计算时间衰减权重
        
        使用指数衰减：weight = e^(-days/decay_period)
        """
        if days_ago < 0:
            days_ago = 0
        
        decay_rate = days_ago / self.time_decay_days
        weight = math.exp(-decay_rate)
        return weight
    
    def _calculate_co_occurrence_boost(self, document: dict, entity_id: str) -> float:
        """
        计算共现加成
        
        如果文档中同时提到多个高动量实体，增加权重
        """
        entity_refs = document.get('entity_references', [])
        
        if len(entity_refs) <= 1:
            return 0.0
        
        # 获取其他实体的动量值
        other_entities = [ref['entity_id'] for ref in entity_refs if ref['entity_id'] != entity_id]
        
        if not other_entities:
            return 0.0
        
        # 查询其他实体的动量
        from app.database.mongodb import mongodb_conn
        other_momentum_sum = 0.0
        for other_id in other_entities[:5]:  # 最多考虑5个共现实体
            other_entity = mongodb_conn.find_one('canonical_entities', {'_id': other_id})
            if other_entity:
                other_momentum_sum += other_entity.get('current_momentum', 0.0)
        
        # 共现加成：其他实体平均动量的50%
        avg_momentum = other_momentum_sum / len(other_entities) if other_entities else 0.0
        boost = avg_momentum * 0.5
        
        return min(boost, 0.5)  # 最大加成50%
    
    def _normalize_momentum(self, raw_momentum: float) -> float:
        """
        归一化动量值到[0, 1]
        
        使用对数压缩：normalized = log(1 + raw) / log(1 + max_expected)
        优化：提高max_expected避免动量值过快达到饱和
        """
        max_expected = 500.0  # 调整预期最大值（从100提高到500），降低归一化速度
        
        if raw_momentum <= 0:
            return 0.0
        
        normalized = math.log(1 + raw_momentum) / math.log(1 + max_expected)
        return min(normalized, 1.0)
    
    def get_momentum_trend(self, entity_id: str, start: datetime, end: datetime, 
                          interval_days: int = 1) -> List[Dict]:
        """
        获取实体的动量趋势
        
        Args:
            entity_id: 实体ID
            start: 开始时间
            end: 结束时间
            interval_days: 采样间隔（天）
            
        Returns:
            [{date: "2024-12-01", value: 0.85}, ...]
        """
        from app.database.mongodb import mongodb_conn
        
        # 首先检查该时间段内是否有该实体的文档引用
        documents_in_range = list(mongodb_conn.find_many(
            'document_instances',
            {
                'entity_references.entity_id': entity_id,
                'created_at': {'$gte': start, '$lte': end}
            }
        ))
        
        # 如果时间范围内没有任何引用，返回全零数据点
        if not documents_in_range:
            logger.info(f"实体 {entity_id} 在时间范围 {start} 到 {end} 内无引用，返回零值趋势")
            trends = []
            current = start
            while current <= end:
                trends.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'value': 0.0
                })
                current += timedelta(days=interval_days)
            return trends
        
        # 有数据时，计算每个时间点基于累积数据的动量
        trends = []
        current = start
        current_time = datetime.now()  # 获取当前时间，避免计算未来动量
        
        try:
            while current <= end:
                # 如果时间点是未来（比当前日期晚），返回0（不预测未来）
                # 注意：使用日期比较，避免时分秒影响
                if current.date() > current_time.date():
                    trends.append({
                        'date': current.strftime('%Y-%m-%d'),
                        'value': 0.0
                    })
                    current += timedelta(days=interval_days)
                    continue
                
                # 计算从start到current当天结束时的累积动量（包含current这一整天）
                current_end_of_day = current.replace(hour=23, minute=59, second=59)
                cumulative_docs = [
                    doc for doc in documents_in_range 
                    if doc.get('created_at', start) <= current_end_of_day
                ]
                
                if cumulative_docs:
                    # 基于累积文档计算动量
                    momentum = self._calculate_momentum_from_docs(
                        entity_id, cumulative_docs, current
                    )
                else:
                    momentum = 0.0
                
                trends.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'value': round(momentum, 4)
                })
                current += timedelta(days=interval_days)
            
            logger.debug(f"实体 {entity_id} 趋势数据生成: {len(trends)} 个数据点")
            return trends
        except Exception as e:
            logger.error(f"获取动量趋势失败: {e}", exc_info=True)
            # 返回空列表而不是抛出异常
            return []
    
    def _calculate_momentum_from_docs(self, entity_id: str, documents: List[Dict], 
                                     current_time: datetime) -> float:
        """
        基于给定的文档列表计算动量
        
        Args:
            entity_id: 实体ID
            documents: 文档列表
            current_time: 当前时间点
            
        Returns:
            动量值
        """
        if not documents:
            return 0.0
        
        total_momentum = 0.0
        
        for doc in documents:
            # 获取数据源可信度
            source_id = doc.get('source_id', 'unknown')
            try:
                credibility = self.source_mgr.get_credibility(source_id) if source_id else 0.8
            except:
                credibility = 0.8
            
            # 计算时间衰减因子（越新权重越高）
            doc_time = doc.get('created_at', current_time)
            days_ago = (current_time - doc_time).days
            recency_factor = self._calculate_recency_weight(days_ago)
            
            # 计算共现加成
            co_occurrence_boost = self._calculate_co_occurrence_boost(doc, entity_id)
            
            # 加权求和
            doc_momentum = credibility * recency_factor * (1 + co_occurrence_boost)
            total_momentum += doc_momentum
        
        # 归一化到[0, 1]
        normalized_momentum = self._normalize_momentum(total_momentum)
        return normalized_momentum
    
    def update_all_momentum(self, entity_type: str = None) -> Dict:
        """
        更新所有实体的动量值
        
        Args:
            entity_type: 只更新特定类型的实体，None表示全部
            
        Returns:
            更新统计
        """
        from app.database.mongodb import mongodb_conn
        
        # 查询实体
        query = {'type': entity_type} if entity_type else {}
        entities = mongodb_conn.find_many('canonical_entities', query)
        
        updated_count = 0
        current_time = datetime.now()
        
        for entity in entities:
            entity_id = entity['_id']
            
            # 计算新动量
            new_momentum = self.calculate_momentum(entity_id, current_time)
            
            # 更新MongoDB
            self.entity_mgr.update_momentum(entity_id, new_momentum)
            
            # 更新Neo4j
            self.neo4j.update_entity_momentum(entity_id, new_momentum)
            
            updated_count += 1
        
        logger.info(f"批量更新动量完成: {updated_count} 个实体")
        
        return {
            'success': True,
            'updated_count': updated_count,
            'entity_type': entity_type or 'ALL'
        }
    
    def get_top_momentum_entities(self, limit: int = 10, entity_type: str = None,
                                  start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """
        获取动量最高的实体
        
        Args:
            limit: 返回数量
            entity_type: 实体类型过滤
            start_date: 开始日期，计算该时间段内的动量
            end_date: 结束日期，计算该时间段内的动量
            
        Returns:
            实体列表（按动量排序）
        """
        from app.database.mongodb import mongodb_conn
        
        # 如果指定了时间范围，需要重新计算该时间段的动量
        if start_date or end_date:
            # 构建文档查询条件
            doc_query = {}
            if start_date or end_date:
                doc_query['created_at'] = {}
                if start_date:
                    doc_query['created_at']['$gte'] = start_date
                if end_date:
                    doc_query['created_at']['$lte'] = end_date
            
            # 获取时间范围内的文档引用的实体ID
            documents = list(mongodb_conn.find_many('document_instances', doc_query))
            logger.info(f"查询文档条件: {doc_query}, 找到文档数: {len(documents)}")
            
            entity_ids_in_range = set()
            for doc in documents:
                for ref in doc.get('entity_references', []):
                    entity_id = ref.get('entity_id')
                    if entity_id:
                        entity_ids_in_range.add(entity_id)
            
            logger.info(f"时间范围内的实体ID数量: {len(entity_ids_in_range)}")
            
            # 如果该时间段没有任何文档，直接返回空结果
            if not entity_ids_in_range:
                logger.info(f"时间范围 {start_date} 到 {end_date} 内没有文档引用")
                return []
            
            # 构建查询，只包含时间范围内被引用的实体，且未被屏蔽
            query = {
                '_id': {'$in': list(entity_ids_in_range)},
                '$or': [
                    {'hidden': {'$exists': False}},
                    {'hidden': False}
                ]
            }
            if entity_type:
                query['type'] = entity_type
            
            # 获取这些实体
            collection = mongodb_conn.get_collection('canonical_entities')
            all_entities = list(collection.find(query))
            
            # 过滤掉媒体源实体
            all_entities = [e for e in all_entities if not self._is_media_source(e)]
            logger.info(f"过滤媒体源后剩余实体数: {len(all_entities)}")
            
            # 使用时间段的最后一天作为计算时间点，但不能超过今天（避免计算未来动量）
            current_time = datetime.now()
            if end_date:
                # 如果结束日期是未来，使用今天；否则使用结束日期
                calc_time = min(end_date, current_time)
            else:
                calc_time = current_time
            
            logger.info(f"计算动量的时间点: {calc_time} (end_date={end_date}, 当前时间={current_time})")
            
            # 为每个实体计算指定时间段的动量
            entity_momentums = []
            for entity in all_entities:
                entity_id = entity['_id']
                # 计算该时间点的动量（会自动只考虑时间窗口内的文档）
                momentum = self.calculate_momentum(entity_id, calc_time)
                
                if momentum > 0:  # 只保留有动量的实体
                    # 将计算出的动量值更新到实体对象中，确保返回的是正确的动量值
                    entity['current_momentum'] = momentum
                    entity_momentums.append({
                        'entity': entity,
                        'momentum': momentum
                    })
            
            # 按动量排序
            entity_momentums.sort(key=lambda x: x['momentum'], reverse=True)
            
            # 取前limit个
            results = [item['entity'] for item in entity_momentums[:limit]]
        else:
            # 没有时间范围限制，直接使用current_momentum排序，且过滤已屏蔽的实体
            query = {
                '$or': [
                    {'hidden': {'$exists': False}},
                    {'hidden': False}
                ]
            }
            if entity_type:
                query['type'] = entity_type
            
            collection = mongodb_conn.get_collection('canonical_entities')
            # 获取更多结果用于过滤，因为会移除媒体源
            all_results = list(collection.find(query).sort('current_momentum', -1).limit(limit * 3))
            # 过滤掉媒体源
            filtered_results = [e for e in all_results if not self._is_media_source(e)]
            logger.info(f"过滤前: {len(all_results)} 个实体, 过滤后: {len(filtered_results)} 个实体")
            # 取前limit个
            results = filtered_results[:limit]
        
        # 转换结果格式
        formatted_results = []
        for entity in results:
            formatted_results.append({
                'id': entity.get('_id'),
                'names': entity.get('names', []),
                'type': entity.get('type'),
                'current_momentum': entity.get('current_momentum', 0),
                'reference_count': entity.get('reference_count', 0),
                'momentum_history': entity.get('momentum_history', []),
                'last_updated': entity.get('last_updated')
            })
        
        return formatted_results
    
    def _is_media_source(self, entity: dict) -> bool:
        """
        判断实体是否为媒体源
        
        Args:
            entity: 实体文档
            
        Returns:
            是否为媒体源
        """
        # 检查所有名称变体
        entity_names = entity.get('names', [])
        for name in entity_names:
            if name in self.MEDIA_SOURCE_BLACKLIST:
                logger.debug(f"过滤媒体源实体: {name}")
                return True
        return False
    
    def detect_momentum_spike(self, entity_id: str, threshold: float = 0.3) -> bool:
        """
        检测动量异常飙升
        
        Args:
            entity_id: 实体ID
            threshold: 飙升阈值（如0.3表示30%的增长）
            
        Returns:
            是否发生飙升
        """
        from app.database.mongodb import mongodb_conn
        
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        
        if not entity:
            return False
        
        history = entity.get('momentum_history', [])
        
        if len(history) < 2:
            return False
        
        # 比较最新值和前一个值
        current = history[-1]['value']
        previous = history[-2]['value']
        
        if previous == 0:
            return current > threshold
        
        change_rate = (current - previous) / previous
        
        if change_rate >= threshold:
            logger.warning(f"检测到动量飙升: {entity_id}, 增长 {change_rate*100:.1f}%")
            return True
        
        return False


    def get_momentum_trend_aggregate(self, start: datetime, end: datetime, 
                                     interval_days: int = 1, entity_type: str = None) -> List[Dict]:
        """
        获取聚合的动量趋势（所有实体的平均动量）
        基于指定时间范围内的文档重新计算
        
        Args:
            start: 开始时间
            end: 结束时间
            interval_days: 采样间隔（天）
            entity_type: 实体类型过滤
            
        Returns:
            [{date: "2024-12-01", avg_momentum: 0.45}, ...]
        """
        from app.database.mongodb import mongodb_conn
        
        # 首先获取时间范围内的所有文档
        documents_in_range = list(mongodb_conn.find_many(
            'document_instances',
            {'created_at': {'$gte': start, '$lte': end}}
        ))
        
        logger.info(f"聚合趋势查询: {start} 到 {end}, 找到文档数: {len(documents_in_range)}")
        
        # 提取被引用的实体ID
        entity_ids_in_range = set()
        for doc in documents_in_range:
            for ref in doc.get('entity_references', []):
                entity_id = ref.get('entity_id')
                if entity_id:
                    entity_ids_in_range.add(entity_id)
        
        logger.info(f"聚合趋势: 提取到 {len(entity_ids_in_range)} 个实体ID")
        
        # 如果时间范围内没有任何文档，返回全零趋势
        if not entity_ids_in_range:
            logger.info(f"时间范围 {start} 到 {end} 内没有文档引用，返回零值趋势")
            trends = []
            current = start
            while current <= end:
                trends.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'avg_momentum': 0.0,
                    'count': 0
                })
                current += timedelta(days=interval_days)
            return trends
        
        # 获取这些实体的信息
        query = {'_id': {'$in': list(entity_ids_in_range)}}
        if entity_type:
            query['type'] = entity_type
        
        entities_in_range = list(mongodb_conn.find_many('canonical_entities', query))
        
        if not entities_in_range:
            logger.info(f"时间范围内没有符合类型 {entity_type} 的实体")
            trends = []
            current = start
            while current <= end:
                trends.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'avg_momentum': 0.0,
                    'count': 0
                })
                current += timedelta(days=interval_days)
            return trends
        
        # 为每个时间点计算平均动量
        trends = []
        current = start
        current_time = datetime.now()  # 获取当前时间，避免计算未来动量
        
        logger.info(f"当前时间: {current_time}, 将计算从 {start} 到 {end} 的趋势")
        
        while current <= end:
            # 如果时间点是未来（比当前日期晚），返回0（不预测未来）
            # 注意：使用日期比较，避免时分秒影响
            if current.date() > current_time.date():
                trends.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'avg_momentum': 0.0,
                    'count': 0
                })
                current += timedelta(days=interval_days)
                continue
            
            # 获取截止到current当天结束时的累积文档（包含current这一整天）
            current_end_of_day = current.replace(hour=23, minute=59, second=59)
            cumulative_docs = [
                doc for doc in documents_in_range 
                if doc.get('created_at', start) <= current_end_of_day
            ]
            
            if cumulative_docs:
                # 为每个实体计算基于累积文档的动量
                momentum_values = []
                for entity in entities_in_range:
                    entity_id = entity['_id']
                    # 过滤该实体相关的文档
                    entity_docs = [
                        doc for doc in cumulative_docs
                        if any(ref.get('entity_id') == entity_id 
                               for ref in doc.get('entity_references', []))
                    ]
                    
                    if entity_docs:
                        momentum = self._calculate_momentum_from_docs(
                            entity_id, entity_docs, current
                        )
                        momentum_values.append(momentum)
                
                avg_momentum = sum(momentum_values) / len(momentum_values) if momentum_values else 0.0
                count = len(momentum_values)
            else:
                avg_momentum = 0.0
                count = 0
            
            trends.append({
                'date': current.strftime('%Y-%m-%d'),
                'avg_momentum': round(avg_momentum, 4),
                'count': count
            })
            
            current += timedelta(days=interval_days)
        
        logger.info(f"生成聚合动量趋势数据: {len(trends)} 个数据点")
        return trends


    def get_momentum_statistics(self, entity_type: str = None, 
                                start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        获取动量统计信息
        
        Args:
            entity_type: 实体类型过滤
            start_date: 开始日期，统计该时间段内有引用的实体
            end_date: 结束日期
            
        Returns:
            统计信息字典
        """
        from app.database.mongodb import mongodb_conn
        
        try:
            # 如果有时间范围，需要统计该时间段内有文档引用的实体
            if start_date or end_date:
                # 构建文档查询条件
                doc_query = {}
                if start_date or end_date:
                    doc_query['created_at'] = {}
                    if start_date:
                        doc_query['created_at']['$gte'] = start_date
                    if end_date:
                        doc_query['created_at']['$lte'] = end_date
                
                # 获取时间范围内的文档引用的实体ID
                documents = mongodb_conn.find_many('document_instances', doc_query)
                entity_ids_in_range = set()
                for doc in documents:
                    for ref in doc.get('entity_references', []):
                        entity_id = ref.get('entity_id')
                        if entity_id:
                            entity_ids_in_range.add(entity_id)
                
                # 构建实体查询
                match_stage = {'_id': {'$in': list(entity_ids_in_range)}}
                if entity_type:
                    match_stage['type'] = entity_type
            else:
                # 没有时间范围，统计所有实体
                match_stage = {}
                if entity_type:
                    match_stage['type'] = entity_type
            
            # 聚合统计
            pipeline = [
                {'$match': match_stage},
                {'$group': {
                    '_id': None,
                    'total_entities': {'$sum': 1},
                    'avg_momentum': {'$avg': '$current_momentum'},
                    'total_references': {'$sum': '$reference_count'},
                    'high_momentum_count': {
                        '$sum': {'$cond': [{'$gte': ['$current_momentum', 0.7]}, 1, 0]}
                    }
                }}
            ]
            
            result = list(mongodb_conn.aggregate('canonical_entities', pipeline))
            stats = result[0] if result else {}
            
            # 类型分布
            type_pipeline = [
                {'$match': match_stage},
                {'$group': {
                    '_id': '$type',
                    'count': {'$sum': 1}
                }}
            ]
            type_results = list(mongodb_conn.aggregate('canonical_entities', type_pipeline))
            type_distribution = {item['_id']: item['count'] for item in type_results if item.get('_id')}
            
            # 动量等级分布 - 使用更安全的手动计数方式
            momentum_levels = {
                'low': 0,
                'medium': 0,
                'high': 0,
                'very_high': 0
            }
            
            # 获取所有实体的动量值
            entities = list(mongodb_conn.find_many('canonical_entities', match_stage))
            for entity in entities:
                momentum = entity.get('current_momentum', 0)
                if momentum < 0.3:
                    momentum_levels['low'] += 1
                elif momentum < 0.5:
                    momentum_levels['medium'] += 1
                elif momentum < 0.7:
                    momentum_levels['high'] += 1
                else:
                    momentum_levels['very_high'] += 1
            
            logger.info(f"动量统计完成: {stats.get('total_entities', 0)} 个实体, "
                       f"类型分布: {len(type_distribution)}, "
                       f"等级分布: {momentum_levels}")
            
            return {
                'total_entities': stats.get('total_entities', 0),
                'average_momentum': round(stats.get('avg_momentum', 0), 4),
                'total_references': stats.get('total_references', 0),
                'high_momentum_count': stats.get('high_momentum_count', 0),
                'type_distribution': type_distribution if type_distribution else {},
                'momentum_levels': momentum_levels
            }
        except Exception as e:
            logger.error(f"获取动量统计失败: {e}", exc_info=True)
            # 返回默认值，避免前端报错
            return {
                'total_entities': 0,
                'average_momentum': 0.0,
                'total_references': 0,
                'high_momentum_count': 0,
                'type_distribution': {},
                'momentum_levels': {
                    'low': 0,
                    'medium': 0,
                    'high': 0,
                    'very_high': 0
                }
            }


# 全局动量引擎实例
momentum_engine = MomentumEngine()
