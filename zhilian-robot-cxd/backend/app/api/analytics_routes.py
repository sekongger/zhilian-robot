"""
高级分析API路由
提供异常检测、预测分析、本体管理等高级功能
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from app.analytics.anomaly_detection import AnomalyDetector
from app.analytics.prediction import MomentumPredictor
from app.analytics.ontology import OntologyManager

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics"])

# 初始化分析器
anomaly_detector = AnomalyDetector()
momentum_predictor = MomentumPredictor()
ontology_manager = OntologyManager()


@router.get("/anomalies/spikes")
async def detect_momentum_spikes(
    entity_type: Optional[str] = None,
    lookback_hours: int = Query(24, ge=1, le=168, description="回溯时间（小时）")
):
    """
    检测动量激增异常
    
    参数:
    - entity_type: 实体类型过滤（可选）
    - lookback_hours: 回溯时间窗口（1-168小时）
    
    返回:
    - 异常实体列表，包含严重程度和统计信息
    """
    try:
        anomalies = await anomaly_detector.detect_momentum_spikes(
            entity_type=entity_type,
            lookback_hours=lookback_hours
        )
        
        return {
            "success": True,
            "count": len(anomalies),
            "lookback_hours": lookback_hours,
            "anomalies": anomalies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/anomalies/coordinated")
async def detect_coordinated_activity(
    min_entities: int = Query(5, ge=2, description="最小实体数量"),
    time_window_hours: int = Query(6, ge=1, le=48, description="时间窗口（小时）")
):
    """
    检测协同活动（可能的虚假信息传播）
    
    参数:
    - min_entities: 触发检测的最小实体数量
    - time_window_hours: 时间窗口
    
    返回:
    - 可疑协同活动组列表
    """
    try:
        coordinated_groups = await anomaly_detector.detect_coordinated_activity(
            min_entities=min_entities,
            time_window_hours=time_window_hours
        )
        
        return {
            "success": True,
            "count": len(coordinated_groups),
            "coordinated_groups": coordinated_groups
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/anomalies/silence")
async def detect_sudden_silence(
    momentum_drop_threshold: float = Query(0.7, ge=0, le=1, description="动量下降阈值"),
    lookback_hours: int = Query(48, ge=1, le=168, description="回溯时间（小时）")
):
    """
    检测突然沉默（高动量实体突然冷却）
    
    参数:
    - momentum_drop_threshold: 动量下降阈值
    - lookback_hours: 回溯时间
    
    返回:
    - 沉默实体列表
    """
    try:
        silent_entities = await anomaly_detector.detect_sudden_silence(
            momentum_drop_threshold=momentum_drop_threshold,
            lookback_hours=lookback_hours
        )
        
        return {
            "success": True,
            "count": len(silent_entities),
            "silent_entities": silent_entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/anomalies/report")
async def generate_anomaly_report(
    entity_type: Optional[str] = None
):
    """
    生成综合异常检测报告
    
    参数:
    - entity_type: 实体类型过滤（可选）
    
    返回:
    - 完整异常报告，包含多种异常类型和风险评估
    """
    try:
        report = await anomaly_detector.generate_anomaly_report(
            entity_type=entity_type
        )
        
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")


@router.get("/predict/entity/{entity_id}")
async def predict_entity_momentum(
    entity_id: str,
    method: str = Query("auto", regex="^(auto|arima|exponential|linear)$", description="预测方法")
):
    """
    预测单个实体的未来动量
    
    参数:
    - entity_id: 实体ID
    - method: 预测方法（auto/arima/exponential/linear）
    
    返回:
    - 未来7天的动量预测和置信区间
    """
    try:
        prediction = await momentum_predictor.predict_momentum(
            entity_id=entity_id,
            method=method
        )
        
        return {
            "success": True,
            "prediction": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.get("/predict/rising")
async def predict_rising_entities(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    entity_type: Optional[str] = None,
    min_current_momentum: float = Query(0.3, ge=0, le=1, description="最低当前动量")
):
    """
    预测未来上升最快的实体
    
    参数:
    - limit: 返回数量限制
    - entity_type: 实体类型过滤
    - min_current_momentum: 最低当前动量阈值
    
    返回:
    - 预测上升实体列表，按增长率排序
    """
    try:
        rising_entities = await momentum_predictor.predict_top_rising_entities(
            limit=limit,
            entity_type=entity_type,
            min_current_momentum=min_current_momentum
        )
        
        return {
            "success": True,
            "count": len(rising_entities),
            "rising_entities": rising_entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/predict/event-impact")
async def predict_event_impact(
    event_name: str = Query(..., description="事件名称"),
    related_entities: List[str] = Query(..., description="相关实体ID列表")
):
    """
    预测事件对相关实体的影响
    
    参数:
    - event_name: 事件名称
    - related_entities: 相关实体ID列表
    
    返回:
    - 事件影响预测，包含各实体受影响程度
    """
    try:
        impact_prediction = await momentum_predictor.predict_event_impact(
            event_name=event_name,
            related_entities=related_entities
        )
        
        return {
            "success": True,
            "impact_prediction": impact_prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/ontology/synonym")
async def register_synonym(
    canonical_name: str = Query(..., description="标准名称"),
    synonym: str = Query(..., description="同义词"),
    entity_type: str = Query(..., description="实体类型"),
    confidence: float = Query(1.0, ge=0, le=1, description="置信度")
):
    """
    注册实体同义词
    
    参数:
    - canonical_name: 标准名称
    - synonym: 同义词/别名
    - entity_type: 实体类型
    - confidence: 置信度（0-1）
    
    返回:
    - 注册结果
    """
    try:
        success = await ontology_manager.register_synonym(
            canonical_name=canonical_name,
            synonym=synonym,
            entity_type=entity_type,
            confidence=confidence,
            source="api"
        )
        
        return {
            "success": success,
            "message": "同义词注册成功" if success else "同义词已存在"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.get("/ontology/canonical/{name}")
async def get_canonical_name(
    name: str,
    entity_type: Optional[str] = None,
    fuzzy_threshold: float = Query(0.85, ge=0, le=1, description="模糊匹配阈值")
):
    """
    获取实体的标准名称
    
    参数:
    - name: 实体名称
    - entity_type: 实体类型（可选）
    - fuzzy_threshold: 模糊匹配阈值
    
    返回:
    - 标准名称（如果找到）
    """
    try:
        canonical = await ontology_manager.get_canonical_name(
            name=name,
            entity_type=entity_type,
            fuzzy_threshold=fuzzy_threshold
        )
        
        return {
            "success": True,
            "input_name": name,
            "canonical_name": canonical,
            "is_found": canonical is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/ontology/synonyms/{canonical_name}")
async def get_all_synonyms(canonical_name: str):
    """
    获取实体的所有同义词
    
    参数:
    - canonical_name: 标准名称
    
    返回:
    - 同义词列表（包含标准名称）
    """
    try:
        synonyms = await ontology_manager.get_all_synonyms(canonical_name)
        
        return {
            "success": True,
            "canonical_name": canonical_name,
            "synonyms": synonyms,
            "count": len(synonyms)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/ontology/stats")
async def get_ontology_statistics():
    """
    获取本体管理统计信息
    
    返回:
    - 本体数据统计
    """
    try:
        stats = await ontology_manager.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")
