"""
预测模型模块
基于Recorded Future理念，使用时间序列分析预测实体动量趋势
支持ARIMA、指数平滑等方法
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
import asyncio

# 注意：生产环境需要安装 statsmodels
# pip install statsmodels
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("警告: statsmodels未安装，预测功能将使用简化算法")


class MomentumPredictor:
    """
    动量预测器
    预测实体在未来时间段的动量值
    """
    
    def __init__(self, prediction_horizon_days: int = 7):
        """
        初始化预测器
        
        Args:
            prediction_horizon_days: 预测时间跨度（天）
        """
        self.prediction_horizon_days = prediction_horizon_days
        # 使用全局的 canonical_entity_manager 实例
        from app.database.mongodb import canonical_entity_manager
        self.entity_mgr = canonical_entity_manager
    
    async def predict_momentum(
        self,
        entity_id: str,
        method: str = "auto"
    ) -> Optional[Dict]:
        """
        预测单个实体的动量趋势
        
        Args:
            entity_id: 实体ID
            method: 预测方法 ("arima", "exponential", "linear", "auto")
            
        Returns:
            预测结果，包含未来动量值和置信区间
        """
        # 获取历史数据
        historical_data = await self._get_historical_momentum_data(entity_id)
        
        if not historical_data or len(historical_data) < 7:
            return {
                "entity_id": entity_id,
                "error": "数据不足，无法进行可靠预测",
                "min_required_points": 7,
                "available_points": len(historical_data) if historical_data else 0
            }
        
        # 自动选择最佳方法
        if method == "auto":
            method = self._select_best_method(historical_data)
        
        # 执行预测
        if method == "arima" and STATSMODELS_AVAILABLE:
            predictions = self._arima_forecast(historical_data)
        elif method == "exponential" and STATSMODELS_AVAILABLE:
            predictions = self._exponential_smoothing_forecast(historical_data)
        else:
            predictions = self._linear_forecast(historical_data)
        
        # 获取实体信息
        entity = self.entity_mgr.db.find_one(
            self.entity_mgr.collection_name,
            {"_id": entity_id}
        )
        
        return {
            "entity_id": entity_id,
            "entity_name": entity.get("name") if entity else "未知",
            "entity_type": entity.get("type") if entity else "未知",
            "current_momentum": historical_data[-1]["momentum"],
            "prediction_method": method,
            "prediction_horizon_days": self.prediction_horizon_days,
            "predictions": predictions,
            "generated_at": datetime.now()
        }
    
    async def predict_top_rising_entities(
        self,
        limit: int = 20,
        entity_type: Optional[str] = None,
        min_current_momentum: float = 0.3
    ) -> List[Dict]:
        """
        预测未来上升最快的实体
        
        Args:
            limit: 返回数量限制
            entity_type: 实体类型过滤
            min_current_momentum: 最低当前动量阈值
            
        Returns:
            预测上升实体列表
        """
        # 查询候选实体
        query = {"current_momentum": {"$gte": min_current_momentum}}
        if entity_type:
            query["type"] = entity_type
        
        entities = self.entity_mgr.db.find_many(
            self.entity_mgr.collection_name,
            query=query,
            limit=500
        )
        
        predictions = []
        
        for entity in entities:
            try:
                # 预测每个实体
                prediction = await self.predict_momentum(entity["entity_id"], method="linear")
                
                if prediction and "predictions" in prediction:
                    # 计算预测增长率
                    current = prediction["current_momentum"]
                    future = prediction["predictions"][-1]["predicted_momentum"]
                    growth_rate = (future - current) / current if current > 0 else 0
                    
                    if growth_rate > 0.1:  # 只保留增长超过10%的
                        predictions.append({
                            **prediction,
                            "growth_rate": growth_rate,
                            "predicted_momentum_change": future - current
                        })
                        
            except Exception as e:
                continue
        
        # 按增长率排序
        predictions.sort(key=lambda x: x["growth_rate"], reverse=True)
        
        return predictions[:limit]
    
    async def predict_event_impact(
        self,
        event_name: str,
        related_entities: List[str],
        baseline_momentum: float = 0.5
    ) -> Dict:
        """
        预测事件对相关实体的影响
        
        Args:
            event_name: 事件名称
            related_entities: 相关实体ID列表
            baseline_momentum: 基准动量值
            
        Returns:
            事件影响预测
        """
        impact_predictions = []
        
        for entity_id in related_entities:
            prediction = await self.predict_momentum(entity_id)
            
            if prediction and "predictions" in prediction:
                # 计算事件影响系数
                avg_predicted = np.mean([p["predicted_momentum"] for p in prediction["predictions"]])
                impact_coefficient = avg_predicted / baseline_momentum if baseline_momentum > 0 else 1.0
                
                impact_predictions.append({
                    "entity_id": entity_id,
                    "entity_name": prediction.get("entity_name"),
                    "impact_coefficient": impact_coefficient,
                    "impact_level": self._classify_impact(impact_coefficient),
                    "predicted_avg_momentum": avg_predicted
                })
        
        # 排序
        impact_predictions.sort(key=lambda x: x["impact_coefficient"], reverse=True)
        
        return {
            "event_name": event_name,
            "analyzed_entities_count": len(impact_predictions),
            "high_impact_entities": [p for p in impact_predictions if p["impact_level"] == "high"],
            "medium_impact_entities": [p for p in impact_predictions if p["impact_level"] == "medium"],
            "low_impact_entities": [p for p in impact_predictions if p["impact_level"] == "low"],
            "overall_impact_score": np.mean([p["impact_coefficient"] for p in impact_predictions]) if impact_predictions else 0,
            "generated_at": datetime.now()
        }
    
    async def _get_historical_momentum_data(
        self,
        entity_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        获取历史动量数据
        
        注意：这是简化实现，生产环境应从时间序列数据库查询
        """
        # TODO: 实现真正的时间序列存储
        # 现在返回模拟数据
        entity = self.entity_mgr.db.find_one(
            self.entity_mgr.collection_name,
            {"_id": entity_id}
        )
        
        if not entity:
            return []
        
        current_momentum = entity.get("current_momentum", 0)
        
        # 生成模拟历史数据（生产环境应从数据库读取）
        historical_data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i)
            # 添加随机波动模拟真实数据
            noise = np.random.normal(0, 0.05)
            momentum = max(0, min(1, current_momentum + noise - (days - i) * 0.01))
            
            historical_data.append({
                "date": date,
                "momentum": momentum
            })
        
        return historical_data
    
    def _select_best_method(self, data: List[Dict]) -> str:
        """
        根据数据特征自动选择最佳预测方法
        """
        if len(data) >= 30 and STATSMODELS_AVAILABLE:
            # 数据充足且有库支持，使用ARIMA
            return "arima"
        elif len(data) >= 14 and STATSMODELS_AVAILABLE:
            # 中等数据量，使用指数平滑
            return "exponential"
        else:
            # 数据较少或无库支持，使用线性回归
            return "linear"
    
    def _arima_forecast(self, data: List[Dict]) -> List[Dict]:
        """
        ARIMA模型预测
        """
        try:
            values = [d["momentum"] for d in data]
            
            # 拟合ARIMA模型 (p=2, d=1, q=2)
            model = ARIMA(values, order=(2, 1, 2))
            fitted_model = model.fit()
            
            # 预测未来值
            forecast = fitted_model.forecast(steps=self.prediction_horizon_days)
            conf_int = fitted_model.get_forecast(steps=self.prediction_horizon_days).conf_int()
            
            predictions = []
            for i in range(self.prediction_horizon_days):
                future_date = datetime.now() + timedelta(days=i + 1)
                predictions.append({
                    "date": future_date,
                    "predicted_momentum": max(0, min(1, float(forecast[i]))),
                    "confidence_lower": max(0, min(1, float(conf_int[i, 0]))),
                    "confidence_upper": max(0, min(1, float(conf_int[i, 1])))
                })
            
            return predictions
            
        except Exception as e:
            print(f"ARIMA预测失败: {str(e)}, 降级使用线性预测")
            return self._linear_forecast(data)
    
    def _exponential_smoothing_forecast(self, data: List[Dict]) -> List[Dict]:
        """
        指数平滑预测
        """
        try:
            values = [d["momentum"] for d in data]
            
            # 拟合指数平滑模型
            model = ExponentialSmoothing(values, trend="add", seasonal=None)
            fitted_model = model.fit()
            
            # 预测
            forecast = fitted_model.forecast(steps=self.prediction_horizon_days)
            
            predictions = []
            for i in range(self.prediction_horizon_days):
                future_date = datetime.now() + timedelta(days=i + 1)
                predictions.append({
                    "date": future_date,
                    "predicted_momentum": max(0, min(1, float(forecast[i]))),
                    "confidence_lower": max(0, min(1, float(forecast[i]) - 0.1)),
                    "confidence_upper": max(0, min(1, float(forecast[i]) + 0.1))
                })
            
            return predictions
            
        except Exception as e:
            print(f"指数平滑预测失败: {str(e)}, 降级使用线性预测")
            return self._linear_forecast(data)
    
    def _linear_forecast(self, data: List[Dict]) -> List[Dict]:
        """
        线性回归预测（简单但鲁棒）
        """
        values = [d["momentum"] for d in data]
        x = np.arange(len(values))
        
        # 线性拟合
        slope, intercept, r_value, _, std_err = stats.linregress(x, values)
        
        predictions = []
        for i in range(self.prediction_horizon_days):
            future_x = len(values) + i
            future_date = datetime.now() + timedelta(days=i + 1)
            
            predicted_value = slope * future_x + intercept
            # 计算标准误差作为置信区间
            margin = 1.96 * std_err  # 95%置信区间
            
            predictions.append({
                "date": future_date,
                "predicted_momentum": max(0, min(1, predicted_value)),
                "confidence_lower": max(0, min(1, predicted_value - margin)),
                "confidence_upper": max(0, min(1, predicted_value + margin)),
                "trend": "上升" if slope > 0.01 else ("下降" if slope < -0.01 else "平稳"),
                "r_squared": r_value ** 2
            })
        
        return predictions
    
    def _classify_impact(self, impact_coefficient: float) -> str:
        """
        分类影响级别
        """
        if impact_coefficient >= 1.5:
            return "high"
        elif impact_coefficient >= 1.2:
            return "medium"
        else:
            return "low"


# 使用示例
async def example_usage():
    """使用示例"""
    predictor = MomentumPredictor(prediction_horizon_days=7)
    
    # 预测单个实体
    entity_id = "example_entity_123"
    prediction = await predictor.predict_momentum(entity_id)
    print(f"预测方法: {prediction.get('prediction_method')}")
    print(f"未来7天预测: {len(prediction.get('predictions', []))} 个数据点")
    
    # 预测上升实体
    rising_entities = await predictor.predict_top_rising_entities(limit=10)
    print(f"发现 {len(rising_entities)} 个潜力上升实体")
    
    # 预测事件影响
    impact = await predictor.predict_event_impact(
        event_name="某科技公司IPO",
        related_entities=["entity1", "entity2", "entity3"]
    )
    print(f"事件整体影响分数: {impact['overall_impact_score']:.2f}")


if __name__ == "__main__":
    asyncio.run(example_usage())
