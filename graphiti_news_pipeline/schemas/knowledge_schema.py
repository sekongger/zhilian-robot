from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum
from datetime import date, datetime

# Concept Categories (as defined in IncCore.schema) - these will be properties of entities
# For simplicity, we define them as simple string Enums or directly as string properties.
# If Graphiti needs specific Pydantic models for these concepts, we would define them.

class IndustrySector(str, Enum):
    # This would typically be populated with actual industry sectors. For now, it's a placeholder.
    # Graphiti might extract these as simple string properties if there's no fixed list.
    # Example values (replace with actual data):
    ENERGY = "能源"
    MANUFACTURING = "制造业"
    TECHNOLOGY = "科技"
    FINANCE = "金融"
    # ... add more as needed

class CompanyCategory(str, Enum):
    # Example values:
    PRIVATE = "民营企业"
    STATE_OWNED = "国有企业"
    FOREIGN_INVESTED = "外资企业"
    # ... add more as needed

class ProductCategory(str, Enum):
    # Example values:
    SOFTWARE = "软件产品"
    HARDWARE = "硬件产品"
    SERVICE = "服务产品"
    # ... add more as needed

class TechnologyCategory(str, Enum):
    # Example values:
    AI = "人工智能"
    BIG_DATA = "大数据"
    BLOCKCHAIN = "区块链"
    # ... add more as needed

class PersonCategory(str, Enum):
    # Example values:
    ENTREPRENEUR = "企业家"
    SCIENTIST = "科学家"
    POLITICIAN = "政治家"
    # ... add more as needed

class OrganizationCategory(str, Enum):
    # Example values:
    GOVERNMENT = "政府机构"
    RESEARCH = "科研机构"
    INVESTMENT = "投资机构"
    # ... add more as needed

class RegionCategory(str, Enum):
    # Example values:
    COUNTRY = "国家"
    PROVINCE = "省份"
    CITY = "城市"
    # ... add more as needed

class TermCategory(str, Enum):
    # Example values:
    TECHNICAL_TERM = "技术术语"
    INDUSTRY_TERM = "行业术语"
    # ... add more as needed

class EventCategory(str, Enum):
    # Example values:
    POLICY = "政策事件"
    COOPERATION = "合作事件"
    FINANCING = "融资事件"
    # ... add more as needed


class EntityType(str, Enum):
    """
    All entity types defined in IncCore.schema, for Graphiti's extraction.
    This enum maps to the labels of nodes that Graphiti will create.
    """
    INDUSTRY_NODE = "IndustryNode"
    REGION = "Region"
    COMPANY = "Company"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    TECHNOLOGY = "Technology"
    PRODUCT_OBJECT = "ProductObject"
    CHUNK = "Chunk" # IncCore's IndexType, treated as an EntityType for Graphiti processing
    DOCUMENT = "Document"
    DATA_SOURCE = "DataSource"
    INDEX = "Index" # IncCore's IndexType, treated as an EntityType for Graphiti processing
    # Base Event type, specific events will inherit from it.
    EVENT = "Event"
    GOVERNMENT_PUBLISH_POLICY_EVENT = "GovernmentPublishPolicyEvent"
    COMPANY_COOPERATION_EVENT = "CompanyCooperationEvent"
    COMPANY_FINANCING_EVENT = "CompanyFinancingEvent"


class BaseEntity(BaseModel):
    """
    所有核心实体的基类。
    Graphiti之后会尝试将抽取的信息填充到这些字段中。
    """
    label: str = Field(..., alias="name", description="实体的名称")
    description: Optional[str] = Field(None, description="关于该实体的详细描述信息")
    alias: Optional[List[str]] = Field(None, description="别名")
    officialName: Optional[str] = Field(None, description="标准名称")
    semanticType: Optional[str] = Field(None, description="语义类型")


class IndustryNode(BaseEntity):
    """
    产业节点
    """
    industryCategory: Optional[IndustrySector] = Field(None, description="产业分类")


class Region(BaseEntity):
    """
    区域实体
    """
    category: Optional[RegionCategory] = Field(None, description="分类")


class IndustryActor(BaseEntity):
    """
    产业主体，作为公司、机构、人物的基类。
    """
    pass


class Person(IndustryActor):
    """
    人物实体
    """
    nameEn: Optional[str] = Field(None, description="英文名称")
    gender: Optional[Literal["男", "女"]] = Field(None, description="性别")
    jobTitle: Optional[str] = Field(None, description="职称")
    eduDgree: Optional[str] = Field(None, description="学历")
    birthYear: Optional[int] = Field(None, description="出生年份")
    nationality: Optional[str] = Field(None, description="国籍")
    honors: Optional[List[str]] = Field(None, description="荣誉")
    category: Optional[List[PersonCategory]] = Field(None, description="分类")
    # Relations - will be handled as nested models for Graphiti extraction
    relatedCompany: Optional[List[str]] = Field(None, description="关联企业")
    relatedOrganization: Optional[List[str]] = Field(None, description="关联机构")


class Organization(IndustryActor):
    """
    机构实体
    """
    category: Optional[List[OrganizationCategory]] = Field(None, description="分类")
    region: Optional[List[str]] = Field(None, description="所属区域")
    website: Optional[str] = Field(None, description="官网")


class Company(IndustryActor):
    """
    公司实体
    """
    nameEn: Optional[str] = Field(None, description="英文名称")
    category: Optional[List[CompanyCategory]] = Field(None, description="分类")
    industry: Optional[List[IndustrySector]] = Field(None, description="所属行业")
    region: Optional[List[str]] = Field(None, description="所属区域")
    code: Optional[str] = Field(None, description="统一社会信用代码")
    legalPerson: Optional[str] = Field(None, description="法人")
    foundedDate: Optional[date] = Field(None, description="成立日期")
    status: Optional[str] = Field(None, description="经营状态")
    website: Optional[str] = Field(None, description="官网")
    businessScope: Optional[str] = Field(None, description="经营范围")
    companyScale: Optional[str] = Field(None, description="企业规模")
    # Relations - will be handled as nested models for Graphiti extraction
    shareholder: Optional[List[str]] = Field(None, description="股东")
    personShareholder: Optional[List[str]] = Field(None, description="个人股东")
    invest: Optional[List[str]] = Field(None, description="对外投资")
    branch: Optional[List[str]] = Field(None, description="分支机构")
    supplier: Optional[List[str]] = Field(None, description="供应商")
    customer: Optional[List[str]] = Field(None, description="客户")


class Technology(BaseEntity):
    """
    技术实体
    """
    category: Optional[List[TechnologyCategory]] = Field(None, description="分类")
    applyScenarios: Optional[List[str]] = Field(None, description="应用场景")


class ProductObject(BaseEntity):
    """
    产品对象实体
    """
    category: Optional[List[ProductCategory]] = Field(None, description="分类")
    industry: Optional[List[IndustrySector]] = Field(None, description="所属行业")
    manufacturer: Optional[str] = Field(None, description="所属企业")
    brand: Optional[str] = Field(None, description="品牌")
    model: Optional[str] = Field(None, description="型号")
    # Relations
    coreTechnology: Optional[List[str]] = Field(None, description="核心技术")


class Document(BaseEntity):
    """
    文档实体
    """
    source: Optional[str] = Field(None, description="来源")


class DataSource(BaseEntity):
    """
    数据来源实体
    """
    confidence: Optional[float] = Field(None, description="置信度")


class Chunk(BaseEntity): # IncCore's IndexType, modeled as EntityType for Graphiti
    """
    文本块实体 (用于索引和检索)
    """
    content: Optional[str] = Field(None, description="内容")
    source: Optional[str] = Field(None, description="来源")


class Index(BaseEntity): # IncCore's IndexType, modeled as EntityType for Graphiti
    """
    产业指标实体
    """
    pass


# --- Event Definitions ---

class Event(BaseModel): # Base EventType from IncCore
    """
    事件实体基类。Graphiti会尝试从文本中抽取符合事件模式的信息。
    """
    subject: Optional[str] = Field(None, description="主体")
    location: Optional[str] = Field(None, description="地点")
    category: Optional[EventCategory] = Field(None, description="事件分类")
    source: Optional[str] = Field(None, description="来源")
    publishTime: Optional[datetime] = Field(None, description="发布时间")


class GovernmentPublishPolicyEvent(Event):
    """
    政府发布政策事件
    """
    subject: Optional[str] = Field(None, description="主体 (通常为政府机构)")
    object: Optional[str] = Field(None, description="客体 (政策影响的对象或内容)") # IncCore has 'object: Text' here
    location: Optional[str] = Field(None, description="区域")
    confidence: Optional[float] = Field(None, description="置信度")


class CompanyCooperationEvent(Event):
    """
    企业合作事件
    """
    subject: Optional[str] = Field(None, description="主体 (发起合作的企业)")
    object: Optional[str] = Field(None, description="客体 (合作对象，可以是任意产业主体)")
    location: Optional[str] = Field(None, description="地点")
    confidence: Optional[float] = Field(None, description="置信度")


class CompanyFinancingEvent(Event):
    """
    企业融资事件
    """
    subject: Optional[str] = Field(None, description="主体 (融资企业)")
    object: Optional[str] = Field(None, description="客体 (投资机构)")
    financingAmount: Optional[float] = Field(None, description="融资金额")
    financingRound: Optional[str] = Field(None, description="融资轮次")
    location: Optional[str] = Field(None, description="地点")
    confidence: Optional[float] = Field(None, description="置信度")

