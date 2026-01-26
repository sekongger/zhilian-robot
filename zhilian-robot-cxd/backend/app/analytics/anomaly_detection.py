"""
异常检测模块
基于Recorded Future理念，检测实体动量的异常波动
识别突发事件、虚假信息传播等异常模式
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from app.database.mongodb import canonical_entity_manager
from app.analytics.momentum import MomentumEngine
import asyncio

class AnomalyDetector:
    """
    异常检测器
    使用统计方法和时间序列分析检测动量异常
    """
    
    def __init__(
        self,
        z_score_threshold: float = 3.0,
        momentum_spike_threshold: float = 0.5,
        reference_window_days: int = 30
    ):
        """
        初始化异常检测器
        
        Args:
            z_score_threshold: Z分数阈值（默认3.0，即99.7%置信区间）
            momentum_spike_threshold: 动量激增阈值（相对变化）
            reference_window_days: 参考时间窗口（天）
        """
        self.z_score_threshold = z_score_threshold
        self.momentum_spike_threshold = momentum_spike_threshold
        self.reference_window_days = reference_window_days
        self.entity_mgr = canonical_entity_manager
        self.momentum_engine = MomentumEngine()
    
    async def detect_momentum_spikes(
        self,
        entity_type: Optional[str] = None,
        lookback_hours: int = 24
    ) -> List[Dict]:
        """
        检测动量激增（Momentum Spike）
        
        算法：
        1. 获取最近时间窗口内的实体
        2. 计算当前动量与历史平均动量的差异
        3. 标记超过阈值的异常实体
        
        Args:
            entity_type: 实体类型过滤
            lookback_hours: 回溯时间（小时）
            
        Returns:
            异常实体列表，包含异常详情
        """
        anomalies = []
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        # 查询条件
        query = {"last_updated": {"$gte": cutoff_time}}
        if entity_type:
            query["type"] = entity_type
        
        # 获取候选实体
        entities = self.entity_mgr.db.find_many(self.entity_mgr.collection_name, query=query, limit=1000)
        
        for entity in entities:
            try:
                # 计算历史动量统计
                historical_stats = await self._get_historical_momentum_stats(
                    entity["entity_id"],
                    days=self.reference_window_days
                )
                
                current_momentum = entity.get("current_momentum", 0)
                
                if not historical_stats:
                    continue
                
                mean_momentum = historical_stats["mean"]
                std_momentum = historical_stats["std"]
                
                # 计算Z分数
                if std_momentum > 0:
                    z_score = (current_momentum - mean_momentum) / std_momentum
                else:
                    z_score = 0
                
                # 计算相对变化率
                if mean_momentum > 0:
                    relative_change = (current_momentum - mean_momentum) / mean_momentum
                else:
                    relative_change = 0
                
                # 判断是否为异常
                is_spike = (
                    abs(z_score) > self.z_score_threshold or
                    relative_change > self.momentum_spike_threshold
                )
                
                if is_spike:
                    anomalies.append({
                        "entity_id": entity["entity_id"],
                        "entity_name": entity["name"],
                        "entity_type": entity.get("type"),
                        "current_momentum": current_momentum,
                        "historical_mean": mean_momentum,
                        "historical_std": std_momentum,
                        "z_score": z_score,
                        "relative_change": relative_change,
                        "severity": self._calculate_severity(z_score, relative_change),
                        "anomaly_type": "momentum_spike" if relative_change > 0 else "momentum_drop",
                        "detected_at": datetime.now(),
                        "reference_count": entity.get("reference_count", 0),
                        "last_updated": entity.get("last_updated")
                    })
                    
            except Exception as e:
                print(f"检测实体 {entity.get('name')} 异常失败: {str(e)}")
                continue
        
        # 按严重程度排序
        anomalies.sort(key=lambda x: x["severity"], reverse=True)
        
        return anomalies
    
    async def detect_coordinated_activity(
        self,
        min_entities: int = 5,
        time_window_hours: int = 6
    ) -> List[Dict]:
        """
        检测协同活动（Coordinated Activity）
        识别多个实体在短时间内同时获得高动量的模式
        这可能表明虚假信息传播或协同炒作
        
        Args:
            min_entities: 最小实体数量
            time_window_hours: 时间窗口（小时）
            
        Returns:
            可疑协同活动列表
        """
        coordinated_groups = []
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        # 查询最近高动量实体
        high_momentum_entities = self.entity_mgr.db.find_many(
            self.entity_mgr.collection_name,
            query={"current_momentum": {"$gte": 0.7}, "last_updated": {"$gte": cutoff_time}},
            limit=1000
        )
        
        if len(high_momentum_entities) < min_entities:
            return coordinated_groups
        
        # 按类型分组
        type_groups = {}
        for entity in high_momentum_entities:
            entity_type = entity.get("type", "unknown")
            if entity_type not in type_groups:
                type_groups[entity_type] = []
            type_groups[entity_type].append(entity)
        
        # 检测每个类型组的协同性
        for entity_type, entities in type_groups.items():
            if len(entities) >= min_entities:
                # 计算动量分布的一致性
                momentums = [e.get("current_momentum", 0) for e in entities]
                mean_momentum = np.mean(momentums)
                std_momentum = np.std(momentums)
                coefficient_of_variation = std_momentum / mean_momentum if mean_momentum > 0 else 0
                
                # 低变异系数表示高度一致，可能是协同活动
                if coefficient_of_variation < 0.2:  # 变异系数小于20%
                    coordinated_groups.append({
                        "entity_type": entity_type,
                        "entity_count": len(entities),
                        "entity_names": [e["name"] for e in entities[:10]],  # 显示前10个
                        "mean_momentum": mean_momentum,
                        "std_momentum": std_momentum,
                        "coefficient_of_variation": coefficient_of_variation,
                        "time_window_hours": time_window_hours,
                        "detected_at": datetime.now(),
                        "risk_level": "high" if coefficient_of_variation < 0.1 else "medium"
                    })
        
        return coordinated_groups
    
    async def detect_sudden_silence(
        self,
        momentum_drop_threshold: float = 0.7,
        lookback_hours: int = 48
    ) -> List[Dict]:
        """
        检测突然沉默（Sudden Silence）
        识别曾经高动量但突然降至极低的实体
        可能表明事件冷却或信息压制
        
        Args:
            momentum_drop_threshold: 动量下降阈值
            lookback_hours: 回溯时间
            
        Returns:
            沉默实体列表
        """
        silent_entities = []
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        # 查询最近更新的实体
        entities = self.entity_mgr.db.find_many(
            self.entity_mgr.collection_name,
            query={"last_updated": {"$gte": cutoff_time}},
            limit=1000
        )
        
        for entity in entities:
            try:
                historical_stats = await self._get_historical_momentum_stats(
                    entity["entity_id"],
                    days=2  # 只看最近2天
                )
                
                if not historical_stats or historical_stats["max"] < 0.5:
                    continue  # 历史动量不高，不算沉默
                
                current_momentum = entity.get("current_momentum", 0)
                momentum_drop = historical_stats["max"] - current_momentum
                
                if momentum_drop >= momentum_drop_threshold:
                    silent_entities.append({
                        "entity_id": entity["entity_id"],
                        "entity_name": entity["name"],
                        "entity_type": entity.get("type"),
                        "current_momentum": current_momentum,
                        "peak_momentum": historical_stats["max"],
                        "momentum_drop": momentum_drop,
                        "drop_percentage": (momentum_drop / historical_stats["max"] * 100) if historical_stats["max"] > 0 else 0,
                        "detected_at": datetime.now(),
                        "last_updated": entity.get("last_updated")
                    })
                    
            except Exception as e:
                continue
        
        # 按下降幅度排序
        silent_entities.sort(key=lambda x: x["momentum_drop"], reverse=True)
        
        return silent_entities
    
    async def _get_historical_momentum_stats(
        self,
        entity_id: str,
        days: int = 30
    ) -> Optional[Dict]:
        """
        获取实体历史动量统计
        
        Args:
            entity_id: 实体ID
            days: 统计天数
            
        Returns:
            统计数据（mean, std, min, max）
        """
        try:
            # 从时间线数据计算（这需要先存储时间线数据）
            # 简化实现：使用当前动量作为历史参考
            entity = self.entity_mgr.db.find_one(
                self.entity_mgr.collection_name,
                {"_id": entity_id}
            )
            
            if not entity:
                return None
            
            # TODO: 实现真正的时间序列数据存储和查询
            # 这里使用简化方法
            current_momentum = entity.get("current_momentum", 0)
            
            # 模拟历史统计（生产环境应从时间序列数据库查询）
            return {
                "mean": current_momentum * 0.7,  # 假设历史平均为当前的70%
                "std": current_momentum * 0.2,   # 假设标准差为当前的20%
                "min": max(0, current_momentum - 0.3),
                "max": min(1, current_momentum + 0.2)
            }
            
        except Exception as e:
            print(f"获取历史统计失败: {str(e)}")
            return None
    
    def _calculate_severity(self, z_score: float, relative_change: float) -> float:
        """
        计算异常严重程度（0-1）
        
        Args:
            z_score: Z分数
            relative_change: 相对变化率
            
        Returns:
            严重程度分数
        """
        # 综合Z分数和相对变化计算严重程度
        z_component = min(abs(z_score) / 10, 1.0)  # 归一化到0-1
        change_component = min(abs(relative_change), 1.0)
        
        # 加权平均
        severity = (z_component * 0.6 + change_component * 0.4)
        
        return round(severity, 3)
    
    async def generate_anomaly_report(
        self,
        entity_type: Optional[str] = None
    ) -> Dict:
        """
        生成综合异常报告
        
        Args:
            entity_type: 实体类型过滤
            
        Returns:
            完整异常报告
        """
        print("正在生成异常检测报告...")
        
        # 并行执行多种检测
        spikes, coordinated, silences = await asyncio.gather(
            self.detect_momentum_spikes(entity_type=entity_type),
            self.detect_coordinated_activity(),
            self.detect_sudden_silence()
        )
        
        report = {
            "generated_at": datetime.now(),
            "entity_type_filter": entity_type,
            "summary": {
                "momentum_spikes_count": len(spikes),
                "coordinated_activities_count": len(coordinated),
                "sudden_silences_count": len(silences),
                "total_anomalies": len(spikes) + len(coordinated) + len(silences)
            },
            "momentum_spikes": spikes[:20],  # 只返回Top 20
            "coordinated_activities": coordinated,
            "sudden_silences": silences[:20],
            "risk_assessment": self._assess_overall_risk(spikes, coordinated, silences)
        }
        
        return report
    
    def _assess_overall_risk(
        self,
        spikes: List[Dict],
        coordinated: List[Dict],
        silences: List[Dict]
    ) -> Dict:
        """
        评估整体风险水平
        
        Returns:
            风险评估结果
        """
        # 计算高严重度异常数量
        high_severity_spikes = sum(1 for s in spikes if s["severity"] > 0.7)
        high_risk_coordinated = sum(1 for c in coordinated if c.get("risk_level") == "high")
        
        total_high_risk = high_severity_spikes + high_risk_coordinated
        
        # 确定风险等级
        if total_high_risk >= 10:
            risk_level = "critical"
        elif total_high_risk >= 5:
            risk_level = "high"
        elif total_high_risk >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "high_severity_anomalies": total_high_risk,
            "recommendations": self._get_recommendations(risk_level)
        }
    
    def _get_recommendations(self, risk_level: str) -> List[str]:
        """获取风险建议"""
        recommendations = {
            "critical": [
                "立即启动人工审核流程",
                "通知安全团队和管理层",
                "考虑暂停相关实体的自动传播",
                "交叉验证高风险信息源"
            ],
            "high": [
                "增加对异常实体的监控频率",
                "人工审核Top 10高风险实体",
                "检查信息源可信度评分"
            ],
            "medium": [
                "定期审查异常实体",
                "保持正常监控频率"
            ],
            "low": [
                "继续正常监控",
                "无需特殊操作"
            ]
        }
        return recommendations.get(risk_level, [])


# 使用示例
async def example_usage():
    """使用示例"""
    detector = AnomalyDetector(
        z_score_threshold=3.0,
        momentum_spike_threshold=0.5
    )
    
    # 检测动量激增
    spikes = await detector.detect_momentum_spikes(lookback_hours=24)
    print(f"发现 {len(spikes)} 个动量异常")
    
    # 检测协同活动
    coordinated = await detector.detect_coordinated_activity()
    print(f"发现 {len(coordinated)} 个可疑协同活动")
    
    # 生成完整报告
    report = await detector.generate_anomaly_report()
    print(f"总风险等级: {report['risk_assessment']['risk_level']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
