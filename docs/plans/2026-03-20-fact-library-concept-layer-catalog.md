# FactLibrary 概念层概念字典

## 1. 说明

这份文档是 [FactLibrary 概念层建设方案](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-20-fact-library-concept-layer-design.md) 的配套文档，重点说明每个概念为什么要引入、如何获取、挂载到哪些实例、以及如何服务后续推理流程。

约定：

- “引入”回答的是为什么这个概念值得建设。
- “获取”回答的是这个概念从哪里来。
- “使用”回答的是这个概念进入图谱之后怎么参与检索、约束和推理。

## 2. 通用概念层

### 2.1 RegionTaxonomy

**引入目的**

- 统一省、市、区县、园区等地域口径。
- 支撑区域聚集、区域配套、区域产业带分析。
- 为后续“同区域替代”“跨区域传导”提供空间维度约束。

**当前可用来源**

- `Company.province/city`
- `Institution.province/city`
- `Person.province/city`
- 标准和项目中的地区字段

来源字段见：

- [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L47)
- [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L85)
- [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L153)

**推荐获取方式**

- 第一优先：结构化字段直接映射
- 第二优先：引入行政区划标准表
- 第三优先：对文本地址做标准化归一

**建议挂载的实例**

- `Company`
- `Institution`
- `Person`
- `Project`
- `RankingList`

**在推理中的用途**

- 区域产业集群识别
- 区域上下游配套分析
- 区域替代企业筛选
- 风险事件区域传播约束

**典型推理问题**

- 某产业链在长三角有哪些关键企业
- 某区域缺失某环节时，本地是否存在替代者
- 某地区政策变化优先影响哪些企业

### 2.2 OrganizationTypeTaxonomy

**引入目的**

- 统一组织类型口径，避免把高校、科研院所、企业、投资机构混在一起。
- 为组织角色判断和关系过滤提供类型边界。

**当前可用来源**

- `Institution.type1/type2`
- `Investor.type`
- 组织名称后缀规则

**推荐获取方式**

- 结构化字段直接映射
- 组织名称规则补充
- 后续用文本和图关系修正

**建议挂载的实例**

- `Company`
- `Institution`
- `Investor`

**在推理中的用途**

- 约束关系匹配范围
- 区分“研发主体”“投资主体”“生产主体”
- 降低企业/机构同名歧义

### 2.3 OrganizationStatusTaxonomy

**引入目的**

- 统一企业、标准等对象的状态表达。
- 为有效主体筛选和时效性推理提供基础。

**当前可用来源**

- `Company.status`
- `StandardLocal.status`
- `StandardIndustry.status`
- `StandardNation.status`

**推荐获取方式**

- 直接从结构化状态字段映射
- 对不同表的状态值做统一标准化

**建议挂载的实例**

- `Company`
- `StandardLocal`
- `StandardIndustry`
- `StandardNation`

**在推理中的用途**

- 过滤无效主体
- 区分现行标准与历史标准
- 限制风险与替代推理只作用于活跃主体

### 2.4 SubjectTaxonomy

**引入目的**

- 把文献和人物研究方向统一到学科体系下。
- 为技术主题聚类和知识传播提供上层学科边界。

**当前可用来源**

- `Article.subject`
- `Person.research_fields`

**推荐获取方式**

- 学科分类表直接映射
- 文本抽取补充细粒度学科主题

**建议挂载的实例**

- `Article`
- `Person`
- `Institution`

**在推理中的用途**

- 学术方向聚类
- 人才与机构能力归类
- 技术主题与产业主题对齐

### 2.5 StandardStatusTaxonomy

**引入目的**

- 将标准状态独立成统一概念，不再仅用字符串表达。
- 服务标准有效性判断和标准约束推理。

**当前可用来源**

- `Standard*.status`

**推荐获取方式**

- 结构化字段直接映射
- 建立统一标准状态枚举

**建议挂载的实例**

- `StandardLocal`
- `StandardIndustry`
- `StandardNation`

**在推理中的用途**

- 判断标准是否仍然可作为约束依据
- 过滤历史标准带来的噪声

### 2.6 StandardLevelTaxonomy

**引入目的**

- 区分国家标准、行业标准、地方标准及级别体系。
- 服务标准影响范围判断。

**当前可用来源**

- `Standard*.standard_level`

**推荐获取方式**

- 结构化字段直接映射
- 统一标准层级编码

**建议挂载的实例**

- `StandardLocal`
- `StandardIndustry`
- `StandardNation`

**在推理中的用途**

- 判断标准影响范围与约束强度
- 标准覆盖能力分析

### 2.7 IPCTaxonomy

**引入目的**

- 将专利从自由文本编码提升到标准技术分类体系。
- 让专利、企业、技术能力之间可通过同一分类体系联动。

**当前可用来源**

- `Patent.main_ipc`
- `Patent.patent_type`

**推荐获取方式**

- 直接接入 IPC 分类表
- 按 IPC 大类、小类做层级概念建模

**建议挂载的实例**

- `Patent`
- `Company`
- `Institution`

**在推理中的用途**

- 识别企业技术积累方向
- 发现相近技术企业
- 用于技术替代和研发能力分析

### 2.8 ResearchFieldTaxonomy

**引入目的**

- 统一研究领域、技术领域、应用领域的表达。
- 连接机构、人物、成果、文献之间的主题关系。

**当前可用来源**

- `Institution.domain`
- `Person.research_fields`
- `Achievement.technical_field`
- `Achievement.application_field`

**推荐获取方式**

- 结构化字段规则归一
- 文本抽取细化

**建议挂载的实例**

- `Institution`
- `Person`
- `Achievement`
- `Article`

**在推理中的用途**

- 机构能力画像
- 人才与成果聚类
- 技术方向迁移分析

## 3. 产业网链核心概念层

### 3.1 IndustryTaxonomy

**引入目的**

- 明确企业、产品、标准、成果属于哪个产业。
- 这是产业网链推理的入口概念。

**当前可用来源**

- 企业经营范围和简介
- 标准的 `industry_class/domain_name`
- 成果、项目、文献中的技术与应用描述

**推荐获取方式**

- 行业分类表
- 产业词表
- 文本抽取辅助

**建议挂载的实例**

- `Company`
- `Product`
- `Achievement`
- `Patent`
- `Standard*`

**在推理中的用途**

- 产业定位
- 产业内企业召回
- 产业图谱分域
- 产业影响分析

### 3.2 IndustryChainTaxonomy

**引入目的**

- 区分“行业分类”和“产业链分类”。
- 同一行业内部可能有多个链条，推理时需要链路视角。

**当前可用来源**

- `RankingList.lz_industry_chain`
- 企业主营产品、技术方向、行业标签
- 外部产业链目录

**推荐获取方式**

- 外部产业链知识库优先
- 榜单和行业目录补充
- 文本抽取校正

**建议挂载的实例**

- `Company`
- `Product`
- `RankingList`

**在推理中的用途**

- 产业链聚类
- 链内传播分析
- 链级检索入口

### 3.3 ChainStageTaxonomy

**引入目的**

- 明确企业和产品位于链条的上游、中游、下游或细分环节。
- 这是网链推理最核心的概念之一。

**当前可用来源**

- 产品分类
- 企业主营产品
- 企业简介
- 产业链目录

**推荐获取方式**

- 先依据产品到环节的映射表
- 再结合文本和图结构修正

**建议挂载的实例**

- `Company`
- `Product`
- `IndustryChainTaxonomy`

**在推理中的用途**

- 上游下游传播
- 供应风险分析
- 缺失环节识别
- 替代企业筛选

### 3.4 ChainRoleTaxonomy

**引入目的**

- 同一环节内企业角色并不相同，需要进一步区分。
- 例如：原料供应商、设备商、模组厂、整机厂、渠道商。

**当前可用来源**

- 企业简介
- 经营范围
- 主营产品
- 产业链角色词表

**推荐获取方式**

- 规则词表 + 文本抽取

**建议挂载的实例**

- `Company`
- `Institution`

**在推理中的用途**

- 更细粒度地表达企业在链上的职责
- 辅助识别核心节点与替代者

### 3.5 ProductTaxonomy

**引入目的**

- 统一产品概念，不让产品只停留在字符串层。
- 是连接企业、技术、链路环节的关键桥梁。

**当前可用来源**

- 派生实体 `Product`
- `CompanyMainProduct.main_product`
- 专利标题与摘要
- 成果内容

**推荐获取方式**

- 当前产品派生实体做第一版概念原型
- 再引入产品分类词表
- 后续用文本抽取提升粒度

**建议挂载的实例**

- `Company`
- `Patent`
- `Achievement`
- `Product`

**在推理中的用途**

- 产品上下游依赖分析
- 产品替代分析
- 产品到技术、产品到企业的归因分析

### 3.6 TechnologyTaxonomy

**引入目的**

- 将专利、成果、文献、企业能力统一到技术主题上。
- 是技术能力推理的中心概念。

**当前可用来源**

- `Patent.main_ipc`
- `Achievement.technical_field`
- `Article.abstract/keywords`
- `Company.description/business_scope`

**推荐获取方式**

- IPC 映射
- 技术词表
- 文本抽取
- 图结构归纳

**建议挂载的实例**

- `Patent`
- `Achievement`
- `Article`
- `Company`
- `Institution`

**在推理中的用途**

- 企业技术画像
- 技术替代路径分析
- 技术扩散和技术迁移推理

### 3.7 CapabilityTaxonomy

**引入目的**

- 用概念层表示企业和机构的能力，而不只是成果数量和专利数量。
- 让产业网链推理从“拥有什么”升级到“能做什么”。

**当前可用来源**

- 企业简介
- 经营范围
- 成果内容
- 专利布局
- 项目承担信息
- 标准参与信息

**推荐获取方式**

- 文本抽取为主
- 图结构归纳补充

**建议挂载的实例**

- `Company`
- `Institution`
- `Person`

**在推理中的用途**

- 识别链上关键能力节点
- 评估企业补位能力
- 替代能力分析

### 3.8 ApplicationScenarioTaxonomy

**引入目的**

- 统一产品和技术落地场景。
- 把技术、成果和产业需求连接起来。

**当前可用来源**

- `Achievement.application_field`
- `Article.keywords`
- 企业简介和成果描述

**推荐获取方式**

- 结构化字段映射
- 场景词表
- 文本抽取

**建议挂载的实例**

- `Achievement`
- `Product`
- `TechnologyTaxonomy`
- `Company`

**在推理中的用途**

- 场景驱动的企业筛选
- 技术到应用的落地分析

## 4. 推理增强概念层

### 4.1 RiskEventTaxonomy

**引入目的**

- 为后续风险事件层提供标准化的事件类别。

**典型内容**

- 供应中断
- 价格上涨
- 价格下跌
- 政策变化
- 质量事故
- 环保停产

**在推理中的用途**

- 作为影响传播的起点概念
- 将实例事件归到统一的风险类别

### 4.2 ImpactTaxonomy

**引入目的**

- 将“影响结果”标准化，便于做规则传播。

**典型内容**

- 成本上升
- 交付延迟
- 供给不足
- 利润承压
- 替代加速
- 需求提升

**在推理中的用途**

- 与 `RiskEventTaxonomy` 建立 `leadTo` 关系
- 作为实例层影响判断的目标概念

### 4.3 CompetitiveRelationTaxonomy

**引入目的**

- 明确竞争、替代、互补、协同等关系类别。

**在推理中的用途**

- 替代者发现
- 竞品关系识别
- 互补企业发现

### 4.4 QualificationTaxonomy

**引入目的**

- 把高新技术企业、专精特新、标准起草单位等资质标准化。

**当前可用来源**

- 榜单
- 标准
- 企业标签
- 外部资质库

**在推理中的用途**

- 质量筛选
- 企业能力加权
- 候选企业排序

## 5. 各概念在推理中的服务方式

概念层进入推理流程后，主要承担四类功能：

### 5.1 检索约束

先按概念缩小实例候选范围，再进入实例推理。

例子：

- 先筛 `IndustryTaxonomy = 新能源汽车`
- 再筛 `ChainStageTaxonomy = 上游材料`
- 再筛 `CapabilityTaxonomy = 正极材料制造`

### 5.2 规则骨架

概念层关系构成推理规则骨架。

例如：

- `ChainStageTaxonomy upstreamOf ChainStageTaxonomy`
- `TechnologyTaxonomy enables ProductTaxonomy`
- `RiskEventTaxonomy leadTo ImpactTaxonomy`

### 5.3 归纳与泛化

把实例层中分散的事实归纳成可复用概念。

例如：

- 多个专利和成果归纳为同一 `TechnologyTaxonomy`
- 多个产品归纳到同一 `ChainStageTaxonomy`

### 5.4 解释输出

让最终推理路径可解释。

例如：

- 企业A -> 产品概念 -> 上游环节 -> 风险影响概念 -> 推理结论

## 6. 当前建议的优先级

### 第一优先级

- `IndustryTaxonomy`
- `ChainStageTaxonomy`
- `ProductTaxonomy`
- `TechnologyTaxonomy`
- `CapabilityTaxonomy`
- `RegionTaxonomy`

### 第二优先级

- `IndustryChainTaxonomy`
- `ChainRoleTaxonomy`
- `ApplicationScenarioTaxonomy`
- `IPCTaxonomy`
- `SubjectTaxonomy`
- `ResearchFieldTaxonomy`

### 第三优先级

- `RiskEventTaxonomy`
- `ImpactTaxonomy`
- `CompetitiveRelationTaxonomy`
- `QualificationTaxonomy`
- `StandardStatusTaxonomy`
- `StandardLevelTaxonomy`

## 7. 建议结论

概念层不是给实例多打一组标签，而是把你们现有事实库升级为“可归类、可约束、可推理”的知识库。

各概念的引入顺序建议遵循：

1. 先做产业定位概念
2. 再做技术与能力概念
3. 再做风险与影响概念

一句话总结：

**实例层回答“有什么”，概念层回答“是什么、在哪一环、能做什么、会受什么影响”，而这正是产业网链推理真正需要的语义基础。**
