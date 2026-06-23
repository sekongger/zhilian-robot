# Wikipedia / Wikidata 产业网链基础图谱构建方案

## 1. 背景与目标

本文档设计一条“百科开放数据 -> 产业网链基础图谱”的构建路线，目标是效仿 OntoKG 论文中的 ontology-oriented knowledge graph construction 思路，先从 Wikipedia 生态中的结构化知识里筛选产业相关数据，再通过声明式 schema 完成实体分类、属性/关系路由和 OpenSPG 图谱导入。

这里的核心判断是：

**第一版不直接从 Wikipedia 正文开始抽取，而是采用 Wikidata-first、DBpedia-assisted、Wikipedia-text-enhanced 的路线。**

原因如下：

1. 产业网链基础图谱需要稳定的实体、概念和长期关系，不应该从一开始就依赖正文抽取的不稳定结果。
2. Wikidata 已经提供实体、属性、关系、别名、跨语言链接、Wikipedia 页面链接等结构化数据，更适合做基础图谱底座。
3. DBpedia 的 mapping-based ontology 数据来自 Wikipedia infobox 映射，适合补充公司属性、行业类型、对象关系和摘要。
4. Wikipedia 正文更适合作为第二阶段的证据增强和长尾关系补充，而不是第一阶段的主数据源。

最终目标是构建一张能支撑产业网链推理的基础图谱，包括：

- 企业主体图谱
- 产品/材料/技术对象图谱
- 行业/产业环节概念层
- 区域分布图谱
- 母子公司、控股、制造、产品、行业归属等稳定关系
- 后续可与资讯、研报、公告事实层融合的常识底座

## 2. 与 OntoKG 论文方法的对应关系

OntoKG 论文的关键思想不是单纯抽取实体和关系，而是先建立一个可迭代的 ontology schema，再用 schema 决定每个属性应该如何进入图谱。

本文档将其迁移为产业网链场景中的三层设计：

1. `Category`  
   判断实体属于哪类产业对象，例如 `Company`、`ProductObject`、`Technology`、`IndustrySector`、`Region`。

2. `Module`  
   判断某类实体有哪些语义模块，例如企业有基础画像、行业定位、产品组合、区域分布、股权关系等模块。

3. `Routing`  
   判断某个字段是节点属性还是图关系。

路由规则分为四类：

| 路由类型 | 含义 | 入图方式 |
|---|---|---|
| `core` | 主键、名称、别名、来源标识等核心字段 | 节点核心属性 |
| `intrinsic` | 实体自身属性 | 节点属性 |
| `relational` | 可遍历关系 | 图边 |
| `unclaimed` | 暂未被 schema 接住的字段 | 待分析池 |

例如：

| Wikidata / DBpedia 字段 | 产业语义 | 路由 |
|---|---|---|
| 成立时间 | 企业自身属性 | `intrinsic` |
| 员工数 | 企业规模属性 | `intrinsic` |
| 所属行业 | 企业到行业概念 | `relational` |
| 生产产品 | 企业到产品对象 | `relational` |
| 总部地点 | 企业到区域 | `relational` |
| 母公司 | 企业到企业 | `relational` |

这样做的价值是：后续推理需要走图的字段会被转成边，检索过滤需要的字段保留为属性。

## 3. 数据源设计

### 3.1 Wikidata

Wikidata 是第一优先级数据源。

官方数据下载页：

- https://www.wikidata.org/wiki/Wikidata:Database_download/en
- https://dumps.wikimedia.org/wikidatawiki/entities/

使用建议：

- 优先使用 JSON dump。
- JSON dump 是推荐格式，可以逐行读取，每一行解析为一个 Wikidata entity。
- RDF truthy dump 可用于大规模三元组批处理，但第一版建议用 JSON dump，因为 JSON 保留 labels、aliases、descriptions、claims、qualifiers、references、sitelinks，更适合构建带证据和别名的产业图谱。

第一版使用字段：

| 字段 | 用途 |
|---|---|
| `id` | Wikidata QID，作为外部主键 |
| `labels` | 多语言名称 |
| `aliases` | 别名 |
| `descriptions` | 简介 |
| `claims` | 属性和关系主来源 |
| `sitelinks` | 对应 Wikipedia 页面链接 |

### 3.2 DBpedia

DBpedia 是第二优先级数据源。

官方资源：

- https://www.dbpedia.org/resources/ontology/
- https://www.dbpedia.org/resources/latest-core/

使用建议：

- 优先使用 DBpedia Ontology 下的 mapping-based 数据。
- mapping-based properties 优于 raw infobox properties，因为前者经过 DBpedia ontology 规范化。
- DBpedia 可作为 Wikidata 的补充来源，尤其适合补 Wikipedia infobox 中的公司属性、组织类型、行业类型、摘要和外链。

第一版关注的数据：

| DBpedia 数据 | 用途 |
|---|---|
| Mapping-based Types | DBpedia resource 到 ontology class 的类型 |
| Mapping-based Object Relations | 对象关系，例如公司、地点、行业等 |
| Mapping-based Literal Facts | 字面属性，例如成立时间、网站、员工数 |
| Short / Extended Abstracts | Wikipedia 摘要证据 |
| Inter-language / Wikidata links | 与 Wikidata QID 对齐 |

### 3.3 Wikipedia 正文

Wikipedia 正文作为第二阶段增强数据源。

可用来源：

- Wikimedia dumps `pages-articles-multistream`
- Wikipedia API
- Wikimedia Enterprise Structured Contents

第一版不直接全量处理正文，仅在需要证据增强时通过 Wikidata sitelinks 找到对应页面。

适合抽取的内容：

- 页面摘要
- Infobox
- 表格
- 产业相关段落
- 参考来源

## 4. 第一版建设范围

第一版建议选择一个产业做 MVP，不要全行业铺开。

建议 MVP：**机器人产业链基础图谱**。

选择原因：

1. 与当前项目中的产业资讯、研报和机器人场景较契合。
2. Wikipedia/Wikidata 中已有较多机器人、自动化、传感器、控制器、制造商和高校机构数据。
3. 机器人产业链天然包含企业、产品、技术、材料、应用场景、区域和概念层，能验证图谱建模能力。

第一版目标规模：

| 类型 | 目标数量 |
|---|---:|
| Company / Organization | 500 - 3000 |
| ProductObject | 300 - 1000 |
| Technology | 100 - 500 |
| IndustrySector / ProductCategory / TechnologyCategory | 100 - 300 |
| Region | 100 - 500 |
| 稳定关系 | 5000 - 50000 |

第一版先不追求全量，而是追求 schema 可解释、路径可推理、结果可导入。

## 5. 目标图谱结构

目标图谱继续落到 `IncCore.schema` / `IncCore.v2.schema` 的核心骨架，不另起孤立图谱。

### 5.1 节点类型

| 目标节点 | IncCore 类型 | 说明 |
|---|---|---|
| 企业 | `Company` | 公司、制造商、上市公司、子公司 |
| 机构 | `Organization` | 高校、研究院、协会、交易所 |
| 产品 | `ProductObject` | 产品、设备、组件、机器人型号 |
| 技术 | `Technology` | 技术、工艺、算法、平台 |
| 行业概念 | `IndustrySector` | 行业、产业环节、经济部门 |
| 产品概念 | `ProductCategory` | 产品类别 |
| 技术概念 | `TechnologyCategory` | 技术类别 |
| 区域 | `Region` | 国家、省、市、行政区 |
| 文档证据 | `Document` | Wikipedia / DBpedia / Wikidata 来源 |
| 文本块 | `Chunk` | 摘要、正文段落、infobox 表格 |

### 5.2 关系类型

第一版关系应控制数量，优先保留产业网链推理需要的强关系。

| 关系 | 起点 | 终点 | 来源 |
|---|---|---|---|
| `industry` / `belongsToIndustry` | Company | IndustrySector | Wikidata `P452`、DBpedia industry |
| `hasProduct` / `produces` | Company | ProductObject | Wikidata `P1056` |
| `manufacturer` / `manufacturedBy` | ProductObject | Company | Wikidata `P176` |
| `hasTechnology` | Company | Technology | DBpedia / Wikipedia text / 后续抽取 |
| `coreTechnology` | ProductObject | Technology | Wikipedia text / 后续抽取 |
| `region` / `headquarteredIn` | Company | Region | Wikidata `P159` |
| `locatedIn` | Entity | Region | Wikidata `P17`、`P131`、`P276` |
| `shareholder` / `ownedBy` | Company | Company | Wikidata `P127` |
| `branch` / `subsidiary` | Company | Company | Wikidata `P355`、`P749` |
| `isA` | ConceptType | ConceptType | Wikidata `P279`、人工 taxonomy |
| `category` | Entity | ConceptType | Wikidata `P31`、`P279`、DBpedia type |

## 6. Wikidata 属性映射

第一版重点支持以下 Wikidata 属性。

| Wikidata 属性 | 名称 | 入图规则 | IncCore 映射 |
|---|---|---|---|
| `P31` | instance of | 分类、概念挂载 | `category` / `semanticType` |
| `P279` | subclass of | 概念上下位 | `ConceptType.isA` |
| `P452` | industry | 企业行业关系 | `Company.industry` |
| `P1056` | product or material produced | 企业生产产品/材料 | `Company.hasProduct` |
| `P176` | manufacturer | 产品制造商 | `ProductObject.manufacturer` |
| `P178` | developer | 产品/技术开发者 | `ProductObject.manufacturer` 或 `Organization.focusTechnology` |
| `P127` | owned by | 被控股/拥有 | `Company.shareholder` / `ownedBy` |
| `P749` | parent organization | 母公司 | `Company.shareholder` / `subsidiaryOf` |
| `P355` | subsidiary | 子公司 | `Company.branch` |
| `P159` | headquarters location | 总部区域 | `Company.region` |
| `P17` | country | 所属国家 | `Region` |
| `P131` | located in admin entity | 所属行政区 | `Region` |
| `P276` | location | 所在地 | `Region` |
| `P571` | inception | 成立时间 | `Company.foundedDate` |
| `P1128` | employees | 员工数 | `Company.companyScale` 或扩展属性 |
| `P2139` | total revenue | 营收 | 扩展指标或 `Index` |
| `P414` | stock exchange | 交易所 | `Organization` / 扩展关系 |
| `P856` | official website | 官网 | `Company.website` / `Organization.website` |

说明：

- 第一版不强行把所有 Wikidata 属性都接入。
- 未命中的属性进入 `unclaimed`，后续用覆盖率报告驱动 schema 迭代。
- 对于暂时没有 IncCore 明确关系的位置，可以先使用扩展关系名，但要在导入前统一收敛。

## 7. 产业 Routing Schema 草案

建议新增文件：

```text
configs/industry_wiki/IncIndustryWiki.routing.schema.yaml
```

草案如下：

```yaml
version: "0.1"
name: "IncIndustryWikiRoutingSchema"
description: "Wikipedia/Wikidata 产业网链基础图谱路由 schema"

categories:
  Company:
    target_type: "IncCore.Company"
    seed_rules:
      wikidata_instance_of:
        - company
        - business
        - enterprise
        - manufacturer
      dbpedia_types:
        - dbo:Company
        - dbo:Organisation
    core_props:
      wikidata_id: id
      label: labels
      aliases: aliases
      description: descriptions
      wikipedia_url: sitelinks
    modules:
      basic_profile:
        route: intrinsic
        properties:
          foundedDate: P571
          website: P856
          companyScale: P1128
      industry_position:
        route: relational
        properties:
          industry: P452
        edge: industry
        target_type: "IncCore.IndustrySector"
      product_portfolio:
        route: relational
        properties:
          product: P1056
        edge: hasProduct
        target_type: "IncCore.ProductObject"
      ownership:
        route: relational
        properties:
          owned_by: P127
          parent_organization: P749
          subsidiary: P355
        edges:
          owned_by: shareholder
          parent_organization: shareholder
          subsidiary: branch
        target_type: "IncCore.Company"
      region_presence:
        route: relational
        properties:
          headquarters: P159
          country: P17
          admin_region: P131
        edge: region
        target_type: "IncCore.Region"

  ProductObject:
    target_type: "IncCore.ProductObject"
    seed_rules:
      wikidata_instance_of:
        - product
        - robot
        - machine
        - vehicle
        - device
        - component
    modules:
      product_profile:
        route: intrinsic
        properties:
          brand: brand
          model: model
      manufacturer:
        route: relational
        properties:
          manufacturer: P176
          developer: P178
        edge: manufacturer
        target_type: "IncCore.Company"
      product_category:
        route: relational
        properties:
          instance_of: P31
          subclass_of: P279
        edge: category
        target_type: "IncCore.ProductCategory"

  Technology:
    target_type: "IncCore.Technology"
    seed_rules:
      wikidata_instance_of:
        - technology
        - process
        - method
        - algorithm
    modules:
      technology_category:
        route: relational
        properties:
          instance_of: P31
          subclass_of: P279
        edge: category
        target_type: "IncCore.TechnologyCategory"

  IndustrySector:
    target_type: "IncCore.IndustrySector"
    seed_rules:
      wikidata_instance_of:
        - industry
        - economic sector
        - manufacturing industry
    modules:
      hierarchy:
        route: relational
        properties:
          subclass_of: P279
        edge: isA
        target_type: "IncCore.IndustrySector"

  Region:
    target_type: "IncCore.Region"
    seed_rules:
      wikidata_instance_of:
        - country
        - city
        - administrative territorial entity
    modules:
      hierarchy:
        route: relational
        properties:
          admin_parent: P131
          country: P17
        edge: isA
        target_type: "IncCore.RegionCategory"
```

## 8. DTO 设计

建议新增百科基础图谱专用 DTO，放在：

```text
backend/app/wiki_industry_pipeline/dto.py
```

### 8.1 WikiDumpRecordDTO

```python
class WikiDumpRecordDTO(BaseModel):
    source: str
    entity_id: str
    raw: dict
```

职责：

- 承接 Wikidata JSON line 或 DBpedia RDF record。
- 不做业务判断，只保留来源和原始 payload。

### 8.2 WikiEntityCandidateDTO

```python
class WikiEntityCandidateDTO(BaseModel):
    source: str
    entity_id: str
    label: str
    aliases: list[str] = []
    description: str | None = None
    language: str = "en"
    sitelinks: dict[str, str] = {}
    claims: dict[str, list[dict]] = {}
    matched_reasons: list[str] = []
    candidate_categories: list[str] = []
```

职责：

- 表示通过产业筛选后的候选实体。
- 保存为什么被选中的原因，例如 type match、property match、keyword match。

### 8.3 WikiClaimDTO

```python
class WikiClaimDTO(BaseModel):
    source: str
    subject_id: str
    subject_label: str
    property_id: str
    property_label: str | None = None
    value_id: str | None = None
    value_label: str | None = None
    value_literal: object | None = None
    value_datatype: str | None = None
    qualifiers: dict = {}
    references: list[dict] = []
```

职责：

- 把 Wikidata claim / DBpedia triple 统一成“主语、属性、值”的候选事实。

### 8.4 RoutedClaimDTO

```python
class RoutedClaimDTO(BaseModel):
    source: str
    subject_id: str
    subject_label: str
    subject_category: str
    property_id: str
    route: str
    module: str | None = None
    target_type: str | None = None
    edge_type: str | None = None
    value_id: str | None = None
    value_label: str | None = None
    value_literal: object | None = None
    confidence: float = 1.0
    route_reason: str = ""
```

职责：

- 表示 OntoKG-style 路由结果。
- 后续图构建只消费 `RoutedClaimDTO`，不直接消费 Wikidata 原始字段。

### 8.5 WikiGraphBuildBatchDTO

```python
class WikiGraphBuildBatchDTO(BaseModel):
    source_batch_id: str
    entities: list[WikiEntityCandidateDTO] = []
    claims: list[WikiClaimDTO] = []
    routed_claims: list[RoutedClaimDTO] = []
    unclaimed: list[WikiClaimDTO] = []
    metadata: dict = {}
```

职责：

- 承载一次百科产业图谱构建批次的全量中间结果。

## 9. 算子目录设计

建议新增模块：

```text
backend/app/wiki_industry_pipeline/
```

第一版算子如下：

| 算子名 | 输入 | 输出 | 功能 |
|---|---|---|---|
| `wiki_dump_source` | dump 路径 / 文件句柄 | `WikiDumpRecordDTO` | 流式读取 Wikidata / DBpedia dump |
| `wiki_entity_candidate_filter` | `WikiDumpRecordDTO` | `WikiEntityCandidateDTO` | 筛选产业相关实体 |
| `wiki_claim_extract` | `WikiEntityCandidateDTO` | `list[WikiClaimDTO]` | 从 claims/triples 抽出候选事实 |
| `industry_claim_route` | `WikiClaimDTO` | `RoutedClaimDTO` | 根据 routing schema 判断 core/intrinsic/relational/unclaimed |
| `wiki_entity_resolve` | `WikiEntityCandidateDTO` | `NormalizedEntityDTO` | QID、DBpedia URI、Wikipedia URL 对齐 |
| `wiki_stub_node_build` | `RoutedClaimDTO` | `NormalizedEntityDTO` | 为边引用但未完整入库的对象生成 stub node |
| `industry_concept_build` | `RoutedClaimDTO` | `NormalizedConceptSeedDTO` | 从 P31/P279/DBpedia type 构建概念层 |
| `wiki_graph_map` | `WikiGraphBuildBatchDTO` | `GraphImportBatchDTO` | 映射到 IncCore/OpenSPG 图导入批次 |
| `wiki_graph_import` | `GraphImportBatchDTO` | `GraphImportResultDTO` | 导入 OpenSPG 或 dry-run |
| `wiki_coverage_report` | `WikiGraphBuildBatchDTO` | `CoverageReportDTO` | 统计覆盖率、未路由属性、stub 比例 |

这些算子应接入当前知识计算工作台，但可以先作为后端 pipeline 独立实现。

## 10. Pipeline 设计

### 10.1 离线构建 Pipeline

```text
wiki_dump_source
  -> wiki_entity_candidate_filter
  -> wiki_claim_extract
  -> industry_claim_route
  -> wiki_entity_resolve
  -> wiki_stub_node_build
  -> industry_concept_build
  -> wiki_graph_map
  -> wiki_graph_import
```

### 10.2 质量分析 Pipeline

```text
WikiGraphBuildBatchDTO
  -> wiki_coverage_report
  -> unclaimed_property_rank
  -> schema_refine_suggestion
```

### 10.3 Wikipedia 正文增强 Pipeline

第二阶段再做：

```text
RoutedClaimDTO / WikiEntityCandidateDTO
  -> wikipedia_page_fetch
  -> wikipedia_structured_parse
  -> kag_schema_constrained_extract
  -> industry_claim_route
  -> wiki_graph_map
```

注意：正文抽取得到的结果仍必须经过 `industry_claim_route`，不能绕过 schema 直接进图。

## 11. 产业相关实体筛选规则

候选实体筛选由三类规则共同决定。

### 11.1 类型闭包规则

通过 `P31` 和 `P279` 判断实体是否属于产业相关类型。

种子类型示例：

| 类别 | 英文种子 |
|---|---|
| 企业 | company, business, enterprise, manufacturer |
| 行业 | industry, economic sector, manufacturing industry |
| 产品 | product, robot, machine, vehicle, device, component |
| 技术 | technology, process, method, algorithm, platform |
| 材料 | material, raw material, chemical substance, component |
| 区域 | country, city, administrative territorial entity |
| 机构 | university, research institute, association, stock exchange |

实现建议：

- 先加载种子 QID。
- 通过 `P279` 向下展开 2 到 4 层。
- 对候选实体的 `P31` 命中展开后的类型集合即可入选。

### 11.2 属性命中规则

即使类型不明确，只要命中关键产业属性，也进入候选。

关键属性：

```text
P452 industry
P1056 product or material produced
P176 manufacturer
P178 developer
P127 owned by
P749 parent organization
P355 subsidiary
P159 headquarters location
P414 stock exchange
```

### 11.3 关键词召回规则

关键词用于补召回，不作为最终分类依据。

机器人 MVP 关键词：

```text
robotics
industrial robot
humanoid robot
service robot
automation
sensor
actuator
servo motor
controller
machine vision
lidar
motion control
manufacturing
factory automation
```

中文关键词：

```text
机器人
工业机器人
人形机器人
服务机器人
自动化
传感器
执行器
伺服电机
控制器
机器视觉
激光雷达
运动控制
智能制造
```

## 12. OpenSPG / IncCore 映射

### 12.1 Entity Mapping

| Routed Category | IncCore 类型 | graph_id |
|---|---|---|
| `Company` | `Company` | `Company:wiki:{qid}` |
| `Organization` | `Organization` | `Organization:wiki:{qid}` |
| `ProductObject` | `ProductObject` | `ProductObject:wiki:{qid}` |
| `Technology` | `Technology` | `Technology:wiki:{qid}` |
| `IndustrySector` | `IndustrySector` | `IndustrySector:wiki:{qid}` |
| `Region` | `Region` | `Region:wiki:{qid}` |
| `ProductCategory` | `ProductCategory` | `ProductCategory:wiki:{qid}` |
| `TechnologyCategory` | `TechnologyCategory` | `TechnologyCategory:wiki:{qid}` |

### 12.2 Property Mapping

| 来源字段 | IncCore 属性 |
|---|---|
| Wikidata QID | `externalId` 或 `_wikidataId` |
| label | `name` |
| aliases | `alias` |
| description | `description` |
| official website | `website` |
| inception | `foundedDate` |
| sitelink | `url` |
| source | `DataSource` |

### 12.3 Edge Mapping

| Routed edge | IncCore 关系 |
|---|---|
| `belongsToIndustry` | `Company.industry` |
| `produces` | `Company.hasProduct` |
| `manufacturedBy` | `ProductObject.manufacturer` |
| `headquarteredIn` | `Company.region` |
| `ownedBy` | `Company.shareholder` |
| `subsidiaryOf` | `Company.shareholder` 或扩展边 |
| `parentOf` | `Company.branch` |
| `category` | `Entity.category` |
| `isA` | `ConceptType.hypernymPredicate` |

## 13. Stub Node 策略

Wikidata 中经常出现这种情况：

```text
Company A - produces -> Product B
```

但 `Product B` 未被当前批次选为核心实体。

此时不能丢弃关系，否则产业链会断；也不能把所有对象都完整入库，否则噪声会爆炸。

建议采用 stub node：

| 字段 | 值 |
|---|---|
| `graph_id` | `ProductObject:wiki:{qid}` |
| `name` | Wikidata label |
| `semanticType` | `stub` |
| `description` | 简短描述 |
| `source` | wikidata |
| `completionStatus` | `stub` |

后续当该对象被更多关系引用，或命中更强分类规则时，再升级为核心节点。

## 14. 概念层构建

概念层由三类来源融合：

1. Wikidata `P279 subclass of`
2. DBpedia ontology class hierarchy
3. 我们自己的产业 taxonomy

机器人产业链 MVP 建议先定义：

```text
IndustrySector
  -> IntelligentEquipment
  -> RoboticsIndustry
  -> IndustrialAutomation

ProductCategory
  -> Robot
  -> IndustrialRobot
  -> HumanoidRobot
  -> ServiceRobot
  -> Sensor
  -> Controller
  -> Actuator

TechnologyCategory
  -> MachineVision
  -> MotionControl
  -> Navigation
  -> ArtificialIntelligence
  -> Lidar

ApplicationScenarioCategory
  -> AutomotiveManufacturing
  -> ElectronicsManufacturing
  -> Logistics
  -> Healthcare
  -> HomeService
```

概念层的作用：

- 为企业和产品分类。
- 为产业链上中下游推理提供抽象节点。
- 为问答和图检索提供召回扩展。
- 为新闻/研报事实层融合提供稳定锚点。

## 15. 质量评估指标

第一版必须输出质量报告，不能只输出节点边数量。

建议指标：

| 指标 | 含义 |
|---|---|
| `raw_record_count` | 读取原始记录数 |
| `candidate_count` | 候选产业实体数 |
| `category_coverage` | 能分类到目标 category 的比例 |
| `claim_count` | 候选 claim 数 |
| `claim_routing_rate` | claim 被 schema 接住的比例 |
| `relational_claim_rate` | claim 被路由为关系边的比例 |
| `intrinsic_claim_rate` | claim 被路由为属性的比例 |
| `unclaimed_rate` | 未路由 claim 比例 |
| `stub_node_rate` | stub node 占比 |
| `edge_density` | 每个核心实体平均边数 |
| `reasoning_path_coverage` | 典型产业问题可查询路径覆盖率 |
| `manual_precision_sample` | 人工抽样边准确率 |

重点关注：

- `unclaimed_rate` 太高，说明 schema 不够覆盖。
- `stub_node_rate` 太高，说明候选筛选太窄或实体补全不足。
- `edge_density` 太低，说明图谱对推理支持不足。
- `manual_precision_sample` 低，说明路由或类型判定噪声大。

## 16. 第一版推理验证问题

机器人产业链基础图谱构建后，至少应能回答以下问题：

1. 某公司属于哪些产业或产品类别？
2. 某公司生产哪些机器人、设备或关键部件？
3. 某产品由哪些公司制造？
4. 某机器人产品属于哪个产品分类？
5. 某公司总部位于哪里，所属区域有哪些同类企业？
6. 某公司有哪些母公司、子公司或控股关系？
7. 某技术类别关联了哪些产品或企业？
8. 某产业环节下有哪些代表性企业和产品？

典型路径：

```text
Company -> hasProduct -> ProductObject -> category -> ProductCategory
Company -> industry -> IndustrySector
Company -> region -> Region
Company -> shareholder / branch -> Company
ProductObject -> manufacturer -> Company
ProductObject -> coreTechnology -> Technology -> category -> TechnologyCategory
```

## 17. 实施阶段

### 阶段一：样本验证

目标：

- 不下载完整 dump，先用小样本或 SPARQL/API 拉取机器人产业链种子实体。
- 验证 routing schema 和 IncCore 映射是否合理。

任务：

1. 固化机器人产业种子 QID 和关键词。
2. 抽取 1000 到 5000 个候选实体。
3. 生成 `WikiClaimDTO` 和 `RoutedClaimDTO`。
4. 输出 dry-run 图谱节点边统计。
5. 输出未路由属性排行榜。

产物：

- `IncIndustryWiki.routing.schema.yaml`
- `robotics_seed_entities.json`
- `wiki_industry_sample_routed_claims.jsonl`
- `wiki_industry_coverage_report.json`

### 阶段二：离线 dump 处理

目标：

- 支持 Wikidata JSON dump 流式读取和筛选。

任务：

1. 实现 dump reader。
2. 实现类型闭包缓存。
3. 实现候选筛选。
4. 实现 claim 抽取。
5. 实现 routing schema 加载。
6. 实现 GraphImportBatchDTO 生成。

产物：

- 可执行 CLI：

```bash
python -m app.wiki_industry_pipeline.cli build \
  --source wikidata \
  --dump data/wiki/wikidata-latest-all.json.bz2 \
  --routing-schema configs/industry_wiki/IncIndustryWiki.routing.schema.yaml \
  --domain robotics \
  --limit 50000 \
  --dry-run
```

### 阶段三：OpenSPG 小批量导入

目标：

- 将机器人产业链基础图谱导入 OpenSPG 项目。

任务：

1. 生成 `GraphImportBatchDTO`。
2. dry-run 检查节点和边。
3. 小批量 live import。
4. 在 OpenSPG 查询节点、关系和概念层。
5. 验证典型路径。

产物：

- OpenSPG 项目中的百科产业基础图谱。
- 图谱查询样例。
- 导入报告。

### 阶段四：Wikipedia 正文证据增强

目标：

- 为核心节点和关键边补充 Wikipedia 页面证据。

任务：

1. 通过 sitelinks 获取 Wikipedia URL。
2. 抽取摘要、infobox、表格和相关段落。
3. 用 KAG schema-constrained extractor 补充技术、产品、应用场景。
4. 所有抽取结果重新经过 `industry_claim_route`。
5. 将证据写入 `Document` / `Chunk`。

产物：

- 带证据链的产业基础图谱。

## 18. 代码目录建议

```text
backend/app/wiki_industry_pipeline/
  __init__.py
  cli.py
  dto.py
  schema_loader.py
  wikidata_reader.py
  dbpedia_reader.py
  candidate_filter.py
  claim_extractor.py
  claim_router.py
  concept_builder.py
  entity_resolver.py
  graph_mapper.py
  coverage_reporter.py

configs/industry_wiki/
  IncIndustryWiki.routing.schema.yaml
  robotics_seed_terms.yaml
  wikidata_property_mapping.yaml

backend/tests/
  wiki_industry_pipeline_dto_test.py
  wiki_industry_candidate_filter_test.py
  wiki_industry_claim_router_test.py
  wiki_industry_graph_mapper_test.py
  wiki_industry_cli_test.py
```

## 19. 与当前知识计算工作台的关系

百科产业基础图谱 pipeline 可以分两步接入工作台：

1. 第一阶段作为后端离线 pipeline。
2. 第二阶段把每个步骤注册成知识计算算子。

接入工作台后的分类建议：

| 算子 | knowledge_category | operator_class |
|---|---|---|
| `wiki_dump_source` | `data_ingestion_loading` | `general` |
| `wiki_entity_candidate_filter` | `data_preprocessing_structuring` | `business` |
| `wiki_claim_extract` | `knowledge_extraction` | `general` |
| `industry_claim_route` | `knowledge_alignment_standardization` | `business` |
| `wiki_entity_resolve` | `knowledge_alignment_standardization` | `business` |
| `wiki_stub_node_build` | `knowledge_fusion_graph_build` | `business` |
| `industry_concept_build` | `knowledge_fusion_graph_build` | `business` |
| `wiki_graph_map` | `knowledge_fusion_graph_build` | `business` |
| `wiki_graph_import` | `knowledge_fusion_graph_build` | `general` |

## 20. 风险与约束

| 风险 | 说明 | 应对 |
|---|---|---|
| Wikidata dump 体积大 | 全量 JSON dump 非常大 | 第一版先样本和 limit，后续流式处理 |
| 类型体系与产业体系不一致 | Wikidata 的类型不是产业分析 taxonomy | 使用 concept mapper 做归并 |
| 产品和技术边界模糊 | 很多实体既像产品又像技术 | routing schema 允许多候选，但落图前要确定主类型 |
| 长尾实体噪声 | 大量被引用对象质量不一 | 使用 stub node 和引用次数阈值 |
| 中英文名称混杂 | Wikidata 多语言 label 不完整 | 优先中文 label，其次英文 label，保留 alias |
| 与 IncCore.schema 不完全匹配 | 某些关系未定义 | 第一版先映射到已有关系，必要时提出 schema v3 扩展 |
| Wikipedia 正文抽取噪声 | 正文抽取容易引入幻觉或弱关系 | 正文结果必须经过 routing schema 和证据约束 |

## 21. Schema 迭代机制

每次构建后输出三类分析：

1. 未路由属性排行榜  
   哪些 Wikidata 属性经常出现但未被 schema 接住。

2. 高引用 stub node 排行榜  
   哪些 stub node 被大量关系引用，应该升级为核心节点。

3. 低置信关系样本  
   哪些关系路径可能噪声高，需要调整路由或过滤规则。

迭代方式：

```text
构建样本图谱
  -> 生成 coverage report
  -> 分析 unclaimed / stub / low-confidence
  -> 修改 routing schema
  -> 重跑 pipeline
  -> 对比指标
```

这就是 OntoKG 论文中 schema refinement 思路在我们产业场景里的落地形式。

## 22. 推荐下一步

建议下一步直接进入 MVP 实现，范围不要超过以下边界：

1. 只做机器人产业链。
2. 只支持 Wikidata JSON 小样本或 limit 流式读取。
3. 只支持 `Company`、`ProductObject`、`Technology`、`IndustrySector`、`Region` 五类。
4. 只支持本文档第 6 节列出的核心 Wikidata 属性。
5. 先输出 dry-run `GraphImportBatchDTO` 和 coverage report，不立即全量导入。

第一期成功标准：

- 能从 Wikidata 样本中筛出机器人相关产业实体。
- 能把关键 claims 路由为 intrinsic / relational / unclaimed。
- 能生成符合 IncCore/OpenSPG 的节点边批次。
- 能回答至少 5 个典型产业链路径问题。
- 能输出 schema 迭代所需的覆盖率和未路由报告。

