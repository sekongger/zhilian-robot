# Neo4j v2 数据结构说明

本文只描述 `IncCore_0422_最新.schema` 对应的数据结构，用于和外部 Wikidata 大图做子图融合。

说明：schema 模型里部分字段使用了 Pydantic alias（如 `label` 的 alias 是 `name`），Neo4j 实际落库字段以 `name` 为准。

## 1. 总体分层

- 业务实体层：`Enterprise`、`Product`、`ProductModel`、`Technology`、`Patent`、`Organization`、`Person`、`Region`、`Policy`、`Index`、`DataSource`、`Document`、`Chunk`
- 事件抽取层：`EnterpriseEvent`、`OrganizationEvent`
- 新闻入图层：`Episodic`
- 脉络聚合层：`StoryThread`

## 2. 当前 v2 标签

已出现的 v2 标签：`Enterprise`、`Product`、`Technology`、`Industry`、`Person`、`Organization`、`Region`、`Index`、`Document`、`DataSource`、`Chunk`、`EnterpriseEvent`、`OrganizationEvent`、`Episodic`、`StoryThread`

schema 已定义但当前库可能尚未出现的标签：`EconomicSector`、`IndustryGroup`、`ProductTerm`、`ProductModel`、`Patent`、`Policy`

## 3. 通用节点字段

所有业务实体节点通常带有以下基础字段：

- `uuid`
- `name`
- `summary`
- `labels`
- `created_at`
- `group_id`
- `momentum_score`
- `momentum_updated_at`
- `pageRank`
- `communityId`
- `name_embedding`

其中：

- `uuid` 是图内主键
- `name` 是展示名
- `summary` 是摘要
- `labels` 是实体标签数组
- `momentum_score`、`pageRank`、`communityId` 属于运行时计算字段

## 4. 业务实体结构

### 4.1 EconomicSector

- `classificationCode`
- `classificationName`
- `gicsSectorCode`
- `gicsSectorName`
- `gicsMappingRelation`

### 4.2 IndustryGroup

- `classificationCode`
- `classificationName`
- `gicsGroupCode`
- `gicsGroupName`
- `gicsMappingRelation`
- `belongsToEconomicSector`

### 4.3 Industry

- `classificationCode`
- `classificationName`
- `gicsIndustryCode`
- `gicsIndustryName`
- `gicsMappingRelation`
- `belongsToEconomicSector`
- `belongsToIndustryGroup`

### 4.4 ProductTerm

- `belongsToEconomicSector`
- `source`

### 4.5 Product

- `classificationCode`
- `classificationName`
- `classificationLevel`
- `isLeaf`
- `extensionBasis`
- `belongsToEconomicSector`
- `belongsToIndustryGroup`
- `belongsToIndustry`
- `subclassOf`
- `rawMaterial`
- `component`
- `equipment`
- `auxiliaryMaterial`
- `applicationTerminal`
- `hasTerm`
- `coreTechnology`

### 4.6 ProductModel

- `brand`
- `series`
- `model`
- `specification`
- `technicalParameter`
- `publishDate`
- `productLifecycleStatus`
- `belongsToProduct`
- `manufacturer`
- `coreTechnology`

### 4.7 Enterprise

- `unifiedSocialCreditCode`
- `nameEn`
- `officialWebsite`
- `status`
- `inception`
- `companyScale`
- `mainBusiness`
- `businessScope`
- `region`
- `belongsToEconomicSector`
- `belongsToIndustryGroup`
- `belongsToIndustry`
- `legalPerson`
- `personShareholder`
- `keyPerson`
- `shareholder`
- `invest`
- `belongsToGroup`
- `childOrganization`
- `supplier`
- `customer`
- `coreTechnology`
- `corePatent`

### 4.8 Technology

- `nameEn`
- `maturityLevel`
- `applicationScenario`
- `belongsToIndustry`
- `belongsToProduct`

### 4.9 Patent

- `patentNo`
- `patentType`
- `status`
- `applicationDate`
- `publicationDate`
- `grantDate`
- `belongsToTechnology`
- `belongsToProduct`
- `belongsToEnterprise`
- `belongsToOrganization`

### 4.10 Organization

- `nameEn`
- `officialWebsite`
- `category`
- `locatedIn`

### 4.11 Person

- `nameEn`
- `gender`
- `jobTitle`
- `eduDegree`
- `birthYear`
- `honors`
- `category`
- `nationality`
- `worksForEnterprise`
- `worksForOrganization`

### 4.12 Region

- `regionCode`
- `category`
- `belongToRegion`

### 4.13 Policy

- `policyNo`
- `policyLevel`
- `category`
- `publishTime`
- `effectiveTime`
- `expiryTime`
- `issuedBy`
- `appliesToRegion`
- `appliesToIndustry`

### 4.14 Index

- `category`

### 4.15 DataSource

- `confidence`

### 4.16 Document

- `category`
- `publishTime`
- `source`

### 4.17 Chunk

- `name`（schema 字段 `label` 的落库名）
- `description`
- `content`
- `sourceDocument`

### 4.18 EnterpriseEvent / OrganizationEvent

事件节点共用基础字段：

- `name`（schema 字段 `label` 的落库名）
- `description`
- `category`
- `publishTime`
- `subject`
- `location`
- `source`

## 5. 新闻与脉络结构

### 5.1 Episodic

新闻/资讯单元，核心字段：

- `uuid`
- `name`
- `title`
- `content`
- `raw_text`
- `source`
- `news_source`
- `news_url`
- `source_description`
- `publish_time`
- `valid_at`
- `created_at`
- `ingested_at`
- `news_hotness_score`
- `news_hotness_updated_at`
- `entity_edges`
- `structured_facts_json`

### 5.2 StoryThread

脉络聚合节点，核心字段：

- `uuid`
- `thread_type`
- `anchor_entity_uuid`
- `anchor_entity_name`
- `title`
- `summary`
- `first_seen_at`
- `last_seen_at`
- `episode_count`
- `thread_hotness`
- `updated_at`

## 6. 关系结构

### 6.1 `RELATES_TO`

实体间事实关系，常见字段：

- `uuid`
- `name`
- `fact`
- `fact_embedding`
- `episodes`
- `valid_at`
- `expired_at`
- `invalid_at`
- `reference_time`
- `created_at`
- `group_id`
- `source_node_uuid`
- `target_node_uuid`

### 6.2 `MENTIONS`

`Episodic -> Entity`

字段：

- `uuid`
- `created_at`
- `group_id`

### 6.3 `KEY_ENTITY`

`StoryThread -> Entity`

字段：

- `rank`
- `weight`

### 6.4 `IN_THREAD`

`Episodic -> StoryThread`

字段：

- `membership_type`
- `membership_score`
- `similarity_score`
- `similarity_entity`
- `similarity_event`
- `similarity_semantic`
- `similarity_time`
- `is_primary`
- `joined_reason`
- `rank`
- `score`

## 7. 当前库的结构特征

- 目前没有显式 Neo4j 约束
- 已有 Graphiti 内置索引，主要围绕 `Entity`、`Episodic`、`StoryThread`、`RELATES_TO`
- 历史节点里可能残留旧字段，如 `attributes__*`、`website`、`legacy_event_kind`
- 这些残留字段不作为 v2 融合契约的一部分

## 8. 与 Wikidata 大图的融合建议

- `Enterprise` 对接企业类 Wikidata 实体
- `Product` / `ProductModel` 对接产品类实体
- `Technology` 对接技术/概念类实体
- `Person` 对接人物实体
- `Organization` 对接组织机构实体
- `Region` 对接地理实体
- `Patent` 对接专利实体
- `Policy` 对接政策/法规实体

推荐优先匹配字段：

- 企业：`unifiedSocialCreditCode`、`officialName`、`shortName`、`alias`、`officialWebsite`
- 产品：`name`、`officialName`、`brand`、`series`、`model`
- 技术：`name`、`nameEn`、`alias`
- 人物：`name`、`nameEn`、`jobTitle`
- 区域：`regionCode`、`name`
- 专利：`patentNo`
- 政策：`policyNo`

## 9. 融合边界建议

- 保留你的新闻子图为独立命名空间
- 用 `Episodic` 作为资讯证据层
- 用 `RELATES_TO` 作为事实层
- 用 `StoryThread` 作为聚合层
- 外部 Wikidata 主图只做实体主干，你的新闻图作为证据与增量事实层接入

## 10. 结论

这套 v2 结构的核心是：

- 实体层统一到 `Enterprise/Product/Technology/...`
- 资讯层保留 `Episodic`
- 脉络层保留 `StoryThread`
- 关系层以 `RELATES_TO` 承载事实

如果要和 Wikidata 大图融合，建议按“实体主干 + 资讯证据 + 关系事实”三层对接。
