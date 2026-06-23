# IncCore v2 扩展草案变更说明

## 1. 本次新增产物

本次围绕 `IncCore` 大图融合层设计，新增了三份配套产物：

1. 源数据映射表  
   [2026-03-22-incore-source-to-schema-mapping.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-source-to-schema-mapping.md)
2. `v2` schema 草案  
   [IncCore.v2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.v2.schema)
3. Pipeline DTO 与导入流程设计  
   [2026-03-22-incore-fusion-pipeline-dto-design.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-fusion-pipeline-dto-design.md)
4. 本变更说明  
   [2026-03-22-incore-v2-change-log.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-v2-change-log.md)

同时更新了大图融合层总方案文档，补充了对这些产物的引用：

- [2026-03-22-incore-big-graph-fusion-layer-design.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-03-22-incore-big-graph-fusion-layer-design.md)

## 2. 本次修改目标

本次修改不是重写 `IncCore.schema` 的全部建模，而是在现有 v1 基础上，重点补强三块能力：

1. 概念层之间的语义关系
2. 事件层的公共属性
3. 事件层与证据层、实体层、概念层之间的关系

这样做的目的是让统一大图更适合：

- 多源事实融合
- 事件聚合与事件传导分析
- 概念层归纳和抽取约束
- 后续 KAG / OpenKS 抽取增强
- 证据可追溯的智能问答和推理

此外，这一轮还做了“收敛版”处理，目标是让 `IncCore.v2.schema` 更接近实际可提交的 OpenSPG schema，而不是把所有远期设想一次性写进 schema。

## 3. `IncCore.v2.schema` 具体修改内容

## 3.1 收敛原则

相对于上一版更宽的 `v2` 草案，这次收敛主要做了四件事：

1. 只保留第一阶段融合层一定会用到的概念类型。
2. 只保留能直接支撑产业链、产品链、技术链、事件链的关键概念关系。
3. 删除一批当前还没有稳定来源支撑的前瞻性属性和关系。
4. 把 `Chunk` 从 `IndexType` 收敛为更通用的 `EntityType`，降低提交和接入复杂度。

具体来说：

- 保留：
  - 概念关系
  - 事件公共属性
  - 事件证据关系
  - 常识实体到产品/技术的关键关系
- 收敛掉：
  - 暂时用不上的 `TrendCategory`
  - `IndexCategory` 及其相关概念关系
  - 若干尚无明确输入来源支撑的实体属性
  - 一部分过于前瞻的事件属性，如 `importance`、`sentiment`、`postMoneyValuation`

## 3.2 新增概念类型

在原有概念类型之外，新增了以下概念：

- `ApplicationScenarioCategory`
- `ImpactCategory`

新增原因：

- `ApplicationScenarioCategory`
  - 用来承接“技术/产品适用于什么场景”。
- `ImpactCategory`
  - 用来表示事件影响的类型，如成本上升、供给紧张、需求增长等。

## 3.3 概念关系增强

本次给现有概念层直接补充了关系定义。

### `IndustrySector`

新增：

- `upstreamOf`
- `downstreamOf`
- `relatedProductCategory`
- `relatedTechnologyCategory`

意义：

- 为产业网链推理提供产业层级和上下游传播骨架。

### `CompanyCategory`

新增：

- `belongToIndustry`

意义：

- 让企业类型不再只是分类标签，而是能直接归到产业概念。

### `ProductCategory`

新增：

- `belongToIndustry`
- `upstreamOf`
- `downstreamOf`
- `coreTechnologyCategory`

意义：

- 让产品概念直接进入产业链推理路径，并和技术分类发生稳定联系。

### `TechnologyCategory`

新增：

- `belongToIndustry`
- `enableProductCategory`
- `applyToScenario`

意义：

- 把技术分类和产品、行业、应用场景打通，为抽取与归纳共用一个技术语义层。

### `TermCategory`

新增：

- `referToProductCategory`
- `referToTechnologyCategory`
- `referToEventCategory`

意义：

- 让术语层成为抽取词表、消歧词表和概念层之间的桥。

### `EventCategory`

新增：

- `affectIndustry`
- `affectProductCategory`
- `affectTechnologyCategory`
- `leadTo`

意义：

- 让事件分类本身就能承载影响传播和因果链的抽象规则。

## 3.4 实体层增强

这次没有大规模新增实体类型，但对现有实体做了几项增强，以便支持大图融合层。

### `Company`

新增：

- `hasProduct`
- `hasTechnology`

原因：

- 现在统一大图需要直接表达企业和产品、技术之间的联系，不能只依赖产品反向挂企业。

### `Organization`

新增：

- `focusTechnology`

原因：

- 便于表达机构在技术方向上的角色。

### `Technology`

调整：

- `applyScenarios` 从普通文本升级为 `ApplicationScenarioCategory`
- 新增 `relatedTerm`

原因：

- 让技术对象和概念层、术语层能直接联动。

### `ProductObject`

新增：

- `applyToScenario`

原因：

- 产品不只需要描述技术，还需要支持应用场景推理。

### `Chunk`

新增：

- `chunkIndex`
- `startOffset`
- `endOffset`

原因：

- 便于事件、结论精确回引到原文片段。
- 同时把 `Chunk` 收敛为通用 `EntityType`，降低 schema 提交复杂度。

### `Document`

新增：

- `externalId`
- `docType`
- `url`
- `publishTime`

原因：

- 资讯、研报、公文等事实层数据进入统一大图后，必须保留文档级主键、类型、链接和发布时间。

### `DataSource`

新增：

- `sourceType`
- `authorityLevel`

原因：

- 方便做来源优先级和冲突消解。

## 3.5 事件公共属性增强

对基础 `Event` 补充了以下公共属性：

- `name`
- `summary`
- `semanticType`
- `eventTime`
- `endTime`
- `confidence`
- `impactCategory`
- `relatedIndustry`
- `triggerTerms`

意义：

- `name/summary`
  - 让事件可展示、可检索、可直接用于问答。
- `eventTime/endTime`
  - 让事件有真正的发生时间，而不只是发布时间。
- `confidence`
  - 让融合层保留模型和规则对事件的判断强度。
- `impactCategory`
  - 用概念层表示影响类型。
- `relatedIndustry`
  - 让事件与产业层直接相连。
- `triggerTerms`
  - 保留触发术语，为抽取解释和事件聚类服务。

## 3.6 事件关系增强

对基础 `Event` 补充了以下关系：

- `relatedActor`
- `relatedProduct`
- `relatedTechnology`
- `mentionedIn`
- `evidenceChunk`
- `leadTo`
- `affectActor`
- `affectProduct`
- `affectTechnology`
- `affectRegion`
- `affectIndustry`

意义：

- `mentionedIn` / `evidenceChunk`
  - 保证事实可追溯。
- `leadTo`
  - 为事件链和传播链提供直接边。
- `affect*`
  - 为影响分析预留统一出口，不再把影响全塞在文本里。

## 3.7 细分事件增强

### `GovernmentPublishPolicyEvent`

新增：

- `name`
- `summary`
- `eventTime`
- `impactCategory`
- `triggerTerms`
- `policyNo`
- `policyLevel`
- `policyType`
- 以及统一的 `mentionedIn / evidenceChunk / affect* / causedBy / leadTo`

### `CompanyCooperationEvent`

新增：

- `name`
- `summary`
- `eventTime`
- `impactCategory`
- `triggerTerms`
- `cooperationMode`
- `contractAmount`
- 以及统一的事件关系

### `CompanyFinancingEvent`

新增：

- `name`
- `summary`
- `eventTime`
- `impactCategory`
- `triggerTerms`
- `financingPurpose`
- 以及统一的事件关系

## 4. 没有做的修改

这次没有做以下几类变更：

1. 没有删除现有 v1 对象
2. 没有直接覆盖 [IncCore.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.schema)
3. 没有一次性新增大量一等实体，如 `PatentAsset`、`StandardAsset`、`ResearchProject`
4. 没有把所有推导关系都写死成 schema 规则
5. 没有引入更多新的一等实体，如 `PatentAsset`、`StandardAsset`、`ResearchProject`

原因是当前优先级仍然是：

- 先把统一大图骨架和事件层打稳
- 再根据接入数据类型逐步扩实体

## 5. 兼容性判断

`IncCore.v2.schema` 是在当前 v1 基础上的增强草案，不是推翻重写。

兼容性判断如下：

- 对已有对象：
  - 以补充关系和属性为主
- 对概念层：
  - 以新增关键概念关系为主，并做了收敛
- 对事件层：
  - 以增强事件公共属性和证据关系为主

因此，后续落地时建议采用：

1. 先在测试项目提交 `v2` schema
2. 再按 source mapping 表逐步接入常识层和事件层
3. 最后再决定是否继续补充新的细分实体和事件族

## 6. 一句话结论

这次 `v2` 草案的本质，是把当前 `IncCore` 从“能承载统一大图的基础 schema”，提升为“更适合做多源融合、事件建模、概念传播和证据可追溯推理”的融合层 schema。
