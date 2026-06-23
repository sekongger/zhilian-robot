"""
数据模型定义
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class DocumentType(str, Enum):
    """文档类型（V2本体：产业文档类子类）"""
    NEWS = "news"           # 资讯文档
    POLICY = "policy"       # 政策文档
    RESEARCH = "research"   # 研报文档
    PATENT = "patent"       # 专利文档
    STANDARD = "standard"   # 标准文档
    CREDENTIAL = "credential"  # 凭证文档


class EntityModel(BaseModel):
    """实体模型"""
    text: str = Field(..., description="实体文本")
    label: str = Field(..., description="实体类型")
    score: float = Field(default=0.0, description="置信度")


class RelationModel(BaseModel):
    """关系模型"""
    subject: str = Field(..., description="主体实体")
    relation: str = Field(..., description="关系类型")
    object: str = Field(..., description="客体实体")
    confidence: float = Field(default=0.0, description="置信度")


class TextAnalysisRequest(BaseModel):
    """文本分析请求"""
    text: str = Field(..., description="待分析文本")
    extract_entities: bool = Field(default=True, description="是否提取实体")
    extract_relations: bool = Field(default=True, description="是否提取关系")


class TextAnalysisResponse(BaseModel):
    """文本分析响应"""
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    relations: List[RelationModel] = Field(default_factory=list)
    summary: str = Field(default="", description="分析摘要")


class GraphNode(BaseModel):
    """图谱节点"""
    id: str
    name: str
    type: str
    properties: Dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """图谱边"""
    source: str
    target: str
    relation: str
    properties: Dict = Field(default_factory=dict)


class GraphData(BaseModel):
    """图谱数据"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class CompanyInfo(BaseModel):
    """企业信息"""
    name: str
    industry: Optional[str] = None
    products: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class IndustryChainQuery(BaseModel):
    """产业链查询请求"""
    company_name: str = Field(..., description="企业名称")
    depth: int = Field(default=2, description="查询深度")
    relation_types: Optional[List[str]] = Field(default=None, description="关系类型过滤")


# ==================== 新增：基于Recorded Future理念的模型 ====================

class SourceCredibilityScore(BaseModel):
    """数据源可信度评分"""
    politics: float = Field(default=0.5, ge=0.0, le=1.0)
    finance: float = Field(default=0.5, ge=0.0, le=1.0)
    technology: float = Field(default=0.5, ge=0.0, le=1.0)
    general: float = Field(default=0.5, ge=0.0, le=1.0)


class DataSource(BaseModel):
    """数据源模型"""
    name: str = Field(..., description="数据源名称")
    domain: str = Field(..., description="域名")
    credibility_scores: Dict[str, float] = Field(..., description="可信度评分")
    created_at: datetime = Field(default_factory=datetime.now)


class SentimentAnalysis(BaseModel):
    """情感分析结果"""
    polarity: float = Field(default=0.0, ge=-1.0, le=1.0, description="情感极性（-1负面到1正面）")
    intensity: float = Field(default=0.0, ge=0.0, le=1.0, description="情感强度")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")


class EntityReference(BaseModel):
    """实体引用"""
    entity_id: str = Field(..., description="规范实体ID")
    mention: str = Field(..., description="原文提及文本")
    context: str = Field(default="", description="上下文片段")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class TemporalInfo(BaseModel):
    """时间信息"""
    absolute_time: Optional[datetime] = Field(None, description="绝对时间")
    relative_time: Optional[str] = Field(None, description="相对时间表达")
    event_type: str = Field(default="PRESENT", description="PAST/PRESENT/FUTURE")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DocumentInstance(BaseModel):
    """文档实例模型"""
    source_id: str = Field(..., description="数据源ID")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    extracted_time: Optional[datetime] = Field(None, description="提取的时间引用")
    sentiment: Optional[SentimentAnalysis] = Field(None, description="情感分析")
    entity_references: List[EntityReference] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    cached_until: datetime = Field(default_factory=lambda: datetime.now())


class MomentumHistoryPoint(BaseModel):
    """动量历史点"""
    date: datetime
    value: float = Field(ge=0.0, le=1.0)


class OntologyInfo(BaseModel):
    """本体信息"""
    parent: Optional[str] = Field(None, description="父类别")
    industry: Optional[str] = Field(None, description="所属行业")
    sub_categories: List[str] = Field(default_factory=list, description="子类别")


class CanonicalEntity(BaseModel):
    """规范实体模型"""
    id: str = Field(..., description="唯一标识符，如CANONICAL_华为")
    type: str = Field(..., description="实体类型：COMPANY/PRODUCT/TECHNOLOGY/PERSON/LOCATION")
    names: List[str] = Field(..., description="同义词列表")
    current_momentum: float = Field(default=0.0, ge=0.0, le=1.0, description="当前动量值")
    momentum_history: List[MomentumHistoryPoint] = Field(default_factory=list)
    ontology: Optional[OntologyInfo] = Field(None, description="本体关系")
    first_seen: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    reference_count: int = Field(default=0, description="被引用次数")
    avg_credibility: float = Field(default=0.5, ge=0.0, le=1.0, description="平均来源可信度")


class TimelineEvent(BaseModel):
    """时间轴事件"""
    event_id: str
    event_type: str = Field(..., description="事件类型：并购、合作、产品发布等")
    entity_ids: List[str] = Field(..., description="涉及的实体ID列表")
    description: str
    timestamp: datetime
    is_future: bool = Field(default=False, description="是否为未来预测事件")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_count: int = Field(default=1, description="来源数量")


class MomentumTrend(BaseModel):
    """动量趋势"""
    entity_id: str
    entity_name: str
    data_points: List[MomentumHistoryPoint]
    trend_direction: str = Field(default="stable", description="上升/下降/稳定")
    change_rate: float = Field(default=0.0, description="变化率")


class EntityTimelineResponse(BaseModel):
    """实体时间轴响应"""
    entity: CanonicalEntity
    events: List[TimelineEvent]
    momentum_trend: MomentumTrend
