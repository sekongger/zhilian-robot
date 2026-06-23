import json
import re
from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class EntityType(str, Enum):
    ECONOMIC_SECTOR = "EconomicSector"
    INDUSTRY_GROUP = "IndustryGroup"
    INDUSTRY = "Industry"
    PRODUCT_TERM = "ProductTerm"
    PRODUCT = "Product"
    PRODUCT_MODEL = "ProductModel"
    ENTERPRISE = "Enterprise"
    TECHNOLOGY = "Technology"
    PATENT = "Patent"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    REGION = "Region"
    POLICY = "Policy"
    INDEX = "Index"
    DATA_SOURCE = "DataSource"
    DOCUMENT = "Document"
    CHUNK = "Chunk"
    ENTERPRISE_EVENT = "EnterpriseEvent"
    ORGANIZATION_EVENT = "OrganizationEvent"


NoneType = type(None)


def _strip_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(args) == 1:
            return args[0]
    return annotation


def _is_list_annotation(annotation: Any) -> bool:
    return get_origin(annotation) in {list, List}


def _stringify_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _coerce_to_string(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "、".join(_stringify_value(item) for item in value if item is not None)
    return _stringify_value(value)


def _coerce_to_string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [_stringify_value(item) for item in value if item is not None]
    return [_stringify_value(value)]


def _coerce_to_temporal(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", raw):
        return raw

    zh_match = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日?", raw)
    if zh_match:
        year, month, day = zh_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    slash_match = re.fullmatch(r"(\d{4})[./](\d{1,2})[./](\d{1,2})", raw)
    if slash_match:
        year, month, day = slash_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    # Vague expressions such as "2026年春夏" are useful text evidence, but not
    # valid temporal values for schema fields. Drop them instead of failing the
    # whole episode ingestion.
    return None


class GraphitiSchemaModel(BaseModel):
    """Tolerate common LLM shape drift without dropping the whole episode."""

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_llm_attribute_shape(cls, value: Any, info: ValidationInfo) -> Any:
        if value is None or info.field_name is None:
            return value

        field = cls.model_fields.get(info.field_name)
        if field is None:
            return value

        annotation = _strip_optional(field.annotation)
        if annotation is str:
            return _coerce_to_string(value)

        if _is_list_annotation(annotation):
            item_annotation = _strip_optional(get_args(annotation)[0]) if get_args(annotation) else Any
            if item_annotation is str:
                return _coerce_to_string_list(value)

        if annotation in {date, datetime}:
            return _coerce_to_temporal(value)

        return value


class BaseEntity(GraphitiSchemaModel):
    """Generic named entity.

    This is a shared base model and should not be used as a concrete type signal.
    Concrete subtype docstrings define extraction boundaries.
    """

    label: str = Field(..., alias="name", description="Entity name")
    officialName: Optional[str] = None
    shortName: Optional[str] = None
    alias: Optional[List[str]] = None
    description: Optional[str] = None


class EconomicSector(BaseEntity):
    """Top-level economic sector taxonomy node.

    Use for macro sector concepts such as automotive, energy, healthcare, IT.
    This is the highest business classification layer above IndustryGroup/Industry.
    Do not use for a specific enterprise, product, technology, person, region,
    or a concrete "industry cluster" phrase.
    """

    classificationCode: Optional[str] = None
    classificationName: Optional[str] = None
    gicsSectorCode: Optional[List[str]] = None
    gicsSectorName: Optional[List[str]] = None
    gicsMappingRelation: Optional[str] = None


class IndustryGroup(BaseEntity):
    """Mid-level industry cluster under an economic sector.

    Use for grouped industry categories in classification systems.
    Typical language: "产业群", "产业链集群", "行业群", "赛道群".
    Prefer IndustryGroup when the phrase denotes a cluster of multiple industries.
    Do not use for scenario words, organizations, or products.
    Do not classify such cluster terms as Product.
    """

    classificationCode: Optional[str] = None
    classificationName: Optional[str] = None
    gicsGroupCode: Optional[List[str]] = None
    gicsGroupName: Optional[List[str]] = None
    gicsMappingRelation: Optional[str] = None
    belongsToEconomicSector: Optional[str] = None


class Industry(BaseEntity):
    """Concrete industry category.

    Use for concrete industry labels in taxonomies and analysis contexts.
    Typical language: "...制造业", "...服务业", "...系统业", "...行业".
    Do not use for places or scenarios (e.g., factory, campus, hospital scene),
    and do not use for products or product models.
    """

    classificationCode: Optional[str] = None
    classificationName: Optional[str] = None
    gicsIndustryCode: Optional[List[str]] = None
    gicsIndustryName: Optional[List[str]] = None
    gicsMappingRelation: Optional[str] = None
    belongsToEconomicSector: Optional[str] = None
    belongsToIndustryGroup: Optional[str] = None


class ProductTerm(BaseEntity):
    """Product-related terminology node.

    Use for standard product terms, aliases, and controlled vocabulary entries.
    It is a concept/term layer, not a sellable object.
    Do not use for concrete products or specific sellable product models.
    """

    belongsToEconomicSector: Optional[str] = None
    source: Optional[str] = None


class Product(BaseEntity):
    """Product category or product object.

    Use for a product entity/object that can carry classification and composition info.
    Product is object-level (platform/system/solution/device family), not model-level.
    Prefer Product when names look like platform/system/solution families, such as
    terms ending with "平台", "系统", "解决方案", "套件", "装置".
    If text contains a concrete version/model code (e.g., Pro/Lite, SKU, 型号编号),
    prefer ProductModel instead of Product.
    Do not use for company names, industry clusters, technology-only terms, or people.
    """

    classificationCode: Optional[str] = None
    classificationName: Optional[str] = None
    classificationLevel: Optional[int] = None
    isLeaf: Optional[int] = None
    extensionBasis: Optional[List[str]] = None

    belongsToEconomicSector: Optional[str] = None
    belongsToIndustryGroup: Optional[str] = None
    belongsToIndustry: Optional[str] = None
    subclassOf: Optional[str] = None

    rawMaterial: Optional[List[str]] = None
    component: Optional[List[str]] = None
    equipment: Optional[List[str]] = None
    auxiliaryMaterial: Optional[List[str]] = None
    applicationTerminal: Optional[List[str]] = None

    hasTerm: Optional[List[str]] = None
    coreTechnology: Optional[List[str]] = None


class ProductModel(BaseEntity):
    """Specific product model/SKU/version.

    Use when a concrete model is present (brand/series/model/spec/version/SKU).
    Typical signals: model code, year/version suffix, trim names such as Pro/Lite/Max.
    ProductModel is instance-level under Product.
    Do not classify generic platform/system/solution names as ProductModel unless
    a concrete model identifier is explicitly present in the same name span.
    Do not use for generic product category names or platform-level product objects.
    """

    brand: Optional[str] = None
    series: Optional[str] = None
    model: Optional[str] = None
    specification: Optional[List[str]] = None
    technicalParameter: Optional[List[str]] = None
    publishDate: Optional[date] = None
    productLifecycleStatus: Optional[str] = None

    belongsToProduct: Optional[str] = None
    manufacturer: Optional[str] = None
    coreTechnology: Optional[List[str]] = None


class Enterprise(BaseEntity):
    """Commercial legal entity (company).

    Use for corporations and business entities, often with company suffixes
    such as Ltd, Inc, Corp, Group, Holdings, Co.
    Do not use for natural persons, government agencies, associations, or
    generic technology/product terms.
    """

    unifiedSocialCreditCode: Optional[str] = None
    nameEn: Optional[List[str]] = None
    officialWebsite: Optional[List[str]] = None
    status: Optional[str] = None
    inception: Optional[date] = None
    companyScale: Optional[str] = None
    mainBusiness: Optional[str] = None
    businessScope: Optional[str] = None

    region: Optional[str] = None
    belongsToEconomicSector: Optional[str] = None
    belongsToIndustryGroup: Optional[str] = None
    belongsToIndustry: Optional[str] = None

    legalPerson: Optional[str] = None
    personShareholder: Optional[List[str]] = None
    keyPerson: Optional[List[str]] = None

    shareholder: Optional[List[str]] = None
    invest: Optional[List[str]] = None
    belongsToGroup: Optional[str] = None
    childOrganization: Optional[List[str]] = None

    supplier: Optional[List[str]] = None
    customer: Optional[List[str]] = None
    coreTechnology: Optional[List[str]] = None
    corePatent: Optional[List[str]] = None


class Technology(BaseEntity):
    """Technology, method, protocol, or technical capability.

    Use for technical systems, algorithms, standards, and engineering methods.
    Do not use for data source platforms, organizations, or products unless
    the text explicitly describes a technology artifact.
    """

    nameEn: Optional[str] = None
    maturityLevel: Optional[str] = None
    applicationScenario: Optional[List[str]] = None
    belongsToIndustry: Optional[str] = None
    belongsToProduct: Optional[str] = None


class Patent(BaseEntity):
    """Patent right or patent document entity.

    Use only when patent evidence exists, such as patent number, patent type,
    application/publication/grant status or date.
    Do not use for generic IP concepts like 'intellectual property' without
    concrete patent evidence.
    """

    patentNo: Optional[str] = None
    patentType: Optional[str] = None
    status: Optional[str] = None
    applicationDate: Optional[date] = None
    publicationDate: Optional[date] = None
    grantDate: Optional[date] = None

    belongsToTechnology: Optional[List[str]] = None
    belongsToProduct: Optional[List[str]] = None
    belongsToEnterprise: Optional[List[str]] = None
    belongsToOrganization: Optional[List[str]] = None


class Organization(BaseEntity):
    """Non-enterprise organization.

    Use for institutions such as government bodies, universities, research
    institutes, associations, standards bodies, and NGOs.
    Do not use for commercial companies (Enterprise) or natural persons.
    """

    nameEn: Optional[str] = None
    officialWebsite: Optional[List[str]] = None
    category: Optional[List[str]] = None
    locatedIn: Optional[List[str]] = None


class Person(BaseEntity):
    """Natural person.

    Use only for individual human names (founder, CEO, scientist, etc.).
    Do not use for enterprises, institutions, product names, or policy titles.
    A role title alone without a person name should not be classified as Person.
    """

    nameEn: Optional[str] = None
    gender: Optional[str] = None
    jobTitle: Optional[str] = None
    eduDegree: Optional[str] = None
    birthYear: Optional[int] = None
    honors: Optional[List[str]] = None
    category: Optional[List[str]] = None

    nationality: Optional[str] = None
    worksForEnterprise: Optional[List[str]] = None
    worksForOrganization: Optional[List[str]] = None


class Region(BaseEntity):
    """Geographic region or administrative area.

    Use for countries, provinces, cities, districts, parks, and named locations.
    Do not use for organizations, policies, or industries.
    """

    regionCode: Optional[str] = None
    category: Optional[str] = None
    belongToRegion: Optional[str] = None


class Policy(BaseEntity):
    """Policy, regulation, guideline, or program document.

    Use for named policy artifacts with issuing/effective context.
    Do not use for events, organizations, or generic strategic slogans.
    """

    policyNo: Optional[str] = None
    policyLevel: Optional[str] = None
    category: Optional[List[str]] = None
    publishTime: Optional[datetime] = None
    effectiveTime: Optional[datetime] = None
    expiryTime: Optional[datetime] = None

    issuedBy: Optional[List[str]] = None
    appliesToRegion: Optional[List[str]] = None
    appliesToIndustry: Optional[List[str]] = None


class Index(BaseEntity):
    """Indicator, metric, index, or benchmark item.

    Use for measurable indicators (e.g., standards/ratings/indices/benchmarks).
    Do not use for products, technologies, or data sources.
    """

    category: Optional[List[str]] = None


class DataSource(BaseEntity):
    """Data source/provider/channel.

    Use for explicit information sources such as databases, platforms,
    websites, APIs, reports, and statistical bureaus.
    Do not use for technical features/protocols (e.g., OTA) unless the text
    explicitly identifies them as a data source.
    """

    confidence: Optional[float] = None


class Document(BaseEntity):
    """Document artifact.

    Use for named reports, white papers, standards, filings, manuals, and
    certificates as document objects.
    Do not use for organizations or events.
    """

    category: Optional[List[str]] = None
    publishTime: Optional[datetime] = None
    source: Optional[str] = None


class Chunk(GraphitiSchemaModel):
    """Text chunk node representing a sub-document fragment.

    Use for content slices used in retrieval and grounding.
    Not a business entity type.
    """

    label: Optional[str] = Field(None, alias="name", description="Chunk name")
    description: Optional[str] = None
    content: Optional[str] = None
    sourceDocument: Optional[str] = None


class BaseEvent(GraphitiSchemaModel):
    """Generic event node.

    Use for time-bound happenings with subject/location/source context.
    Not for static entity objects like companies or products.
    """

    label: Optional[str] = Field(None, alias="name", description="Event name")
    description: Optional[str] = None
    category: Optional[str] = None
    publishTime: Optional[datetime] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None


class EnterpriseEvent(BaseEvent):
    """Event centered on an enterprise.

    Typical examples: financing, launch, merger, partnership, production, recall.
    """

    pass


class OrganizationEvent(BaseEvent):
    """Event centered on a non-enterprise organization.

    Typical examples: policy release, standard publication, institution announcement.
    """

    pass
