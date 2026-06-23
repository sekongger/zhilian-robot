# 源数据到 IncCore.schema 的对象映射表

## 1. 说明

本文件用于回答两个问题：

1. 当前已有的结构化常识数据、资讯/研报事实数据，应该如何映射到 [IncCore.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.schema)。
2. 哪些源数据可以直接落到现有 schema，哪些只能做过渡映射，哪些更适合在 `v2` 中补强后再作为一等对象入图。

配套文档：

- 大图融合层方案：[2026-03-22-incore-big-graph-fusion-layer-design.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-big-graph-fusion-layer-design.md)
- `v2` 扩展草案：[IncCore.v2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.v2.schema)
- 变更说明：[2026-03-22-incore-v2-change-log.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-v2-change-log.md)

## 2. 映射原则

### 2.1 三类映射状态

- `直接映射`
  - 当前 `IncCore.schema` 已经存在对应对象，可直接落图。
- `过渡映射`
  - 当前 schema 没有完全匹配的一等对象，需要先落到 `Document`、`Event`、`Technology` 等通用对象上。
- `v2 推荐映射`
  - 当前只能过渡处理，但在 [IncCore.v2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.v2.schema) 语义下已经更适合进入统一大图。

### 2.2 主键原则

- `Company`
  - 主键优先用统一社会信用代码，其次用标准企业名。
- `Organization`
  - 标准机构名 + 区域。
- `Person`
  - 姓名 + 机构 + 职务。
- `ProductObject`
  - 标准产品名 + 所属产业。
- `Technology`
  - 标准技术名。
- `Region`
  - 行政区划标准编码。
- `Document`
  - 来源系统文档 ID。
- `Chunk`
  - 文档 ID + chunk 序号。
- `Event`
  - 事件类别 + 主体 + 核心客体 + 时间窗口 + 地点。

### 2.3 入图总流程

所有数据统一按如下流程处理：

`源数据 -> 统一融合 DTO -> 主实体对齐 -> 映射到 IncCore.schema 对象 -> OpenSPG 入图`

不建议直接把原始字段表一对一灌入图谱。

## 3. 结构化常识源映射表

| 源数据 | 当前角色 | 映射到的 IncCore 对象 | 关键字段映射 | 关系 / 概念挂载 | 状态 |
|---|---|---|---|---|---|
| `dw_company_info_tyc` | 企业基础信息 | `Company`、`Region`、`CompanyCategory`、`IndustrySector` | `name -> Company.name`；`used_name -> alias`；`credit_code -> code`；`establish_date -> foundedDate`；`status -> status`；`website -> website`；`business_scope -> businessScope`；`description -> description`；`province/city -> Region` | `Company.region` 由省市标准化后挂接；`Company.category`、`Company.industry` 由规则/词表/抽取补齐 | 直接映射 |
| `dw_institution_2026` | 科研机构 / 高校 / 平台 | `Organization`、`Region`、`OrganizationCategory` | `name -> Organization.name`；`description/domain/achievement -> description`；`website -> website`；`province/city -> Region` | `type_1/type_2/level -> OrganizationCategory`；`support_org_name` 后续可转对企业/机构关系 | 直接映射 |
| `dw_investor` | 投资机构 | `Organization`、`OrganizationCategory` | `name -> Organization.name`；`intro -> description` | `type -> OrganizationCategory`，通常归为“投资机构” | 直接映射 |
| `dw_expert` | 人物 / 专家 | `Person`、`Organization` / `Company`、`Region`、`PersonCategory` | `name -> Person.name`；`prof_title -> jobTitle`；`research_fields + resume -> description`；`honors -> honors`；`province/city -> Region` | `org/orgs` 解析为 `relatedOrganization` 或 `relatedCompany`；`research_fields` 可挂 `TechnologyCategory` / `TermCategory` | 直接映射 |
| `dw_company_main_product` | 企业主营产品 | `ProductObject`、`Company`、`ProductCategory`、`IndustrySector` | `main_product -> ProductObject.name`；`credit_code/name -> manufacturer` | `ProductObject.manufacturer -> Company`；产品名归类后挂接 `ProductCategory` 和 `IndustrySector` | 直接映射 |
| `dw_project` | 科研 / 产业项目 | 当前建议先落 `Document` + 泛化 `Event`；`v2` 中可继续细分 | `name -> Document.name / Event.name`；`abstract_zh -> summary`；`start_date/end_date -> eventTime/endTime`；`approval_year -> publishTime` | `project_leader` 解析为主体人物；`org` 解析为主体机构/企业；`category` 可映射 `EventCategory` | 过渡映射 |
| `dw_patent_china` | 专利与技术知识 | 当前建议落 `Document` + `Technology` + `TermCategory` | `title_cn/title -> Document.name`；`abstract_cn -> Document.description / Technology.description`；`main_ipc -> TermCategory / TechnologyCategory` | `inventors -> Person`；`applicants_norm/patentees_norm -> Company/Organization`；`main_ipc` 反向增强技术概念 | 过渡映射 |
| `dw_article` | 文献 / 论文 | `Document`、`Person`、`Organization`、`TermCategory` | `title -> Document.name`；`abstract -> description`；`doi -> externalId`；`year -> publishTime` | `authors -> Person`；`applicants -> Organization/Company`；`subject/keywords -> TermCategory / TechnologyCategory` | 过渡映射 |
| `dw_achievement_info` | 技术成果 | `Technology`、`Document`、`Organization`、`Person` | `name -> Technology.name / Document.name`；`content -> Technology.description`；`technical_field/application_field -> 概念分类` | `unit/person` 连接到组织和人物；`technology_maturity` 可进入术语或事件标签 | 过渡映射 |
| `dw_standard_local` | 地方标准 | `Document`、`TermCategory`、`TechnologyCategory` | `standard_name -> Document.name`；`details -> description`；`standard_code -> externalId` | `industry_class/standard_type` 可进入术语或技术概念 | 过渡映射 |
| `dw_standard_industry` | 行业标准 | `Document`、`TermCategory`、`TechnologyCategory` | 同上 | `domain_name` 可辅助挂到产业和技术概念 | 过渡映射 |
| `dw_standard_nation` | 国家标准 | `Document`、`TermCategory`、`TechnologyCategory` | 同上 | 可增强术语体系和技术分类 | 过渡映射 |
| `dw_list` | 榜单信息 | 当前建议先落 `Document` + 泛化 `Event` | `name -> Document.name / Event.name`；`publish_time -> publishTime`；`description -> summary` | `publish_organization` 解析为 `Organization`；`indicator` 可映射到 `Index` | 过渡映射 |
| `dw_company_bidder` | 招投标 / 中标事实 | 当前建议先落泛化 `Event`；`v2` 可细化成采购/中标事件 | `title/project_name -> Event.name`；`public_date -> eventTime/publishTime`；`deal_money -> 金额属性` | `bidder/tender` 连接企业或机构；`industry` 可挂产业概念 | 过渡映射 |
| `dw_list_detail` | 榜单明细 | 当前建议先作为 `Document`/`Event` 的辅助明细，不单独成为一等实体 | `company_name/credit_code` 反向连接 `Company` | `sort_order`、`indicator_value` 可转 `Index` 或事件属性 | 过渡映射 |

## 4. 文本事实源映射表

| 源数据 | 当前角色 | 映射到的 IncCore 对象 | 关键字段映射 | 关系 / 概念挂载 | 状态 |
|---|---|---|---|---|---|
| 标准化资讯文档（MongoDB） | 资讯原文 | `Document`、`DataSource` | `doc_id -> Document.externalId`；`title -> name`；`summary/raw_text -> description`；`publish_time -> publishTime`；`source -> DataSource` | 文档抽取后再连接事件、实体和概念 | 直接映射 |
| 标准化研报文档 | 研报原文 | `Document`、`DataSource` | 同上，`docType = report` | 研报可提供更强的事件背景和行业概念 | 直接映射 |
| 文档分块结果 | 证据片段 | `Chunk` | `chunk_id -> external id`；`content -> content`；`chunk_index -> chunkIndex`；`doc_id -> source` | 后续通过 `Event.evidenceChunk` 或 `Event.mentionedIn` 回连证据 | 直接映射 |
| 资讯实体抽取结果 | 文本中抽到的主体 | `Company`、`Organization`、`Person`、`ProductObject`、`Technology`、`Region` | 抽取结果先经过主实体对齐，再回写统一实体节点 | 同时挂接 `CompanyCategory`、`IndustrySector`、`ProductCategory`、`TechnologyCategory` 等概念 | 直接映射 |
| 资讯术语抽取结果 | 文本中的技术 / 产品 / 行业术语 | `TermCategory`、`ProductCategory`、`TechnologyCategory`、`IndustrySector` | 术语标准名进入概念层，别名进入 `alias` | 反向为抽取和对齐提供词表 | 直接映射 |

## 5. Graphiti 事件产物映射表

| Graphiti 输出 | 映射到的 IncCore 对象 | 关键字段映射 | 备注 |
|---|---|---|---|
| 政策类事件 | `GovernmentPublishPolicyEvent` | 主体机构 -> `subject`；地域 -> `location`；发布时间 -> `publishTime`；事件摘要 -> `summary`；来源 -> `source` | 同时建议挂 `EventCategory` 和 `IndustrySector` |
| 合作类事件 | `CompanyCooperationEvent` | 主体企业 -> `subject`；合作方 -> `object`；事件时间 -> `eventTime` / `publishTime`；摘要 -> `summary` | 同时可挂 `relatedProduct`、`relatedTechnology` |
| 融资类事件 | `CompanyFinancingEvent` | 主体企业 -> `subject`；投资方 -> `object`；金额 -> `financingAmount`；轮次 -> `financingRound`；时间 -> `eventTime` | 同时可挂 `IndustrySector`、`ImpactCategory` |
| 其他事件 | `Event` | 当具体事件类型暂未建 schema 时，先进入泛化事件层 | 后续在 `v2+` 中细分成建设、产能、风险、产品发布等事件族 |

## 6. 关键字段级映射示例

### 6.1 `dw_company_info_tyc -> Company`

| 源字段 | 目标对象 | 目标字段 | 说明 |
|---|---|---|---|
| `name` | `Company` | `name` | 主名称 |
| `used_name` | `Company` | `alias` | 作为别名，多值保留 |
| `credit_code` | `Company` | `code` | 主锚点 |
| `description` | `Company` | `description` | 作为企业简介 |
| `business_scope` | `Company` | `businessScope` | 经营范围 |
| `status` | `Company` | `status` | 企业状态 |
| `website` | `Company` | `website` | 官网 |
| `establish_date` | `Company` | `foundedDate` | 成立日期 |
| `province/city` | `Region` | `name` | 先标准化区域，再挂接 `Company.region` |

### 6.2 `dw_company_main_product -> ProductObject`

| 源字段 | 目标对象 | 目标字段 | 说明 |
|---|---|---|---|
| `main_product` | `ProductObject` | `name` | 先拆分、标准化、去重 |
| `name/credit_code` | `Company` | `manufacturer` | 产品归属企业 |
| 产品归类规则 | `ProductCategory` | `ProductObject.category` | 由词表或规则映射 |
| 产业归类规则 | `IndustrySector` | `ProductObject.industry` | 由产品分类和产业规则映射 |

### 6.3 `资讯文档 -> Document/Chunk/Event`

| 源字段 | 目标对象 | 目标字段 | 说明 |
|---|---|---|---|
| `doc_id` | `Document` | `externalId` | 文档主键 |
| `title` | `Document` | `name` | 文档标题 |
| `source` | `DataSource` | `name` | 数据来源 |
| `publish_time` | `Document` | `publishTime` | 发布时间 |
| `content` | `Chunk` | `content` | 文档分块内容 |
| 抽取到的事件类型 | `EventCategory` | `category` | 事件分类 |
| 抽取到的主体/客体 | 事件对象 | `subject` / `object` | 经过主实体对齐后写入 |

## 7. 当前不能直接完整映射的对象

以下源数据在当前 `IncCore.schema` 下没有完全匹配的一等实体，因此建议采用过渡映射：

- `Patent`
- `Article`
- `Achievement`
- `StandardLocal`
- `StandardIndustry`
- `StandardNation`
- `Project`
- `RankingList`
- `CompanyBidder`

当前建议是：

1. 保留文档证据  
   先进入 `Document` / `Chunk` / `DataSource`。
2. 提取其中的技术、产品、人物、企业  
   进入统一实体层。
3. 提取其中的事件  
   进入统一事件层。
4. 通过概念层承接分类信息  
   进入 `TechnologyCategory`、`ProductCategory`、`EventCategory`、`TermCategory` 等。

## 8. 映射落地建议

建议按三阶段推进：

### 第一阶段

优先完成可直接映射对象：

- `Company`
- `Organization`
- `Person`
- `ProductObject`
- `Technology`
- `Region`
- `Document`
- `Chunk`
- `DataSource`
- 资讯中的三类核心事件

### 第二阶段

把过渡映射对象接入统一大图：

- `Patent`
- `Article`
- `Achievement`
- `Project`
- `Standard*`

这一步重点不是新增很多实体，而是把这些来源作为技术、产品、人物、事件和概念的补充来源。

### 第三阶段

再视业务需要决定是否把某些来源升级为一等实体：

- `PatentAsset`
- `StandardAsset`
- `ResearchProject`
- `RankingPublishEvent`
- `BiddingEvent`

## 9. 一句话结论

从当前源数据到 `IncCore.schema` 的映射，不应走“源表镜像式入图”，而应走“主实体锚定 + 事件化表达 + 概念层挂载 + 文档证据回连”的统一融合路径。
