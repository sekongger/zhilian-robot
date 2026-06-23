# Wikidata 主图与 Neo4j v2 资讯图融合实施方案

更新时间：2026-05-13

## 1. 文档目的

本文档给出一版可直接落地的融合方案，用于将外部 `Neo4j v2` 资讯图接入我们当前以 `Wikidata` 为骨架构建的大图中。

本文重点回答 4 个问题：

1. `v2` 的数据如何导入进来
2. 哪些节点可以匹配到 Wikidata 骨架，如何建立链接
3. 哪些节点不应直接并入骨架，应如何组织
4. 如何尽量保留全部字段，包括 `momentum_score`、`pageRank`、`communityId` 等运行时字段

本文档是研发落地版，后续可以在此基础上继续收敛规则并实施代码。

---

## 2. 结论先行

本次融合建议采用：

`Wikidata canonical 骨架 + v2 资讯画像层 + v2 事实增强层 + 来源字段快照层`

具体原则如下：

1. `Wikidata` 节点作为主骨架，不被外部资讯图直接替换。
2. `v2` 中能对齐到骨架实体的业务节点，不直接改写骨架节点，而是生成 `NewsEntityProfile`，再通过 `refersTo` 指向 Wikidata 节点。
3. `v2` 中不应直接并入骨架的节点，如 `Document`、`Chunk`、`Episodic`、`StoryThread`、`EnterpriseEvent`，保留为事实/证据层节点，通过关系挂接到骨架实体。
4. 外部来源字段尽量不丢失；即使不进入 canonical 属性，也要以“来源快照属性”或“断言/证据对象”的形式保留。
5. 融合过程必须显式产出：
   - 匹配结果
   - 链接结果
   - 冲突结果
   - 未匹配结果

一句话概括：

`v2 图不是替换或改写 Wikidata 图，而是通过资讯画像节点为 Wikidata 骨架补事实、补证据、补时态、补运行指标。`

---

## 3. 融合目标与非目标

### 3.1 融合目标

本次融合目标是：

1. 把 `v2` 图中的企业、产品、技术、区域、组织、人物等业务实体尽量匹配到已有的 `Wikidata` 骨架，并以链接方式挂接。
2. 把 `v2` 图中的资讯文本、chunk、event、episode、thread 等事实性对象挂到对应骨架实体上。
3. 尽量保留 `v2` 字段，不只保留最终主值。
4. 为后续推理、问答、证据回溯、增量更新保留来源信息。

### 3.2 非目标

本次不追求：

1. 一次性把所有 `v2` 字段都强行映射进 `IncCoreV2.schema` 的 canonical 字段中。
2. 一次性解决全部实体歧义问题。
3. 直接在线把两个 Neo4j 库硬 merge。
4. 一次性做完所有多源冲突裁决策略。

---

## 4. 当前两套图的角色定位

### 4.1 Wikidata 图的角色

当前 Wikidata 图适合作为：

- 常识骨架层
- 标准化业务实体层
- 稳定关系层

强项：

- 实体覆盖广
- 结构稳定
- 更适合做 canonical node

弱项：

- 企业业务描述不够充分
- 动态事实弱
- 证据链弱
- 时态信息弱

### 4.2 Neo4j v2 图的角色

根据 [Neo4j_v2_数据结构说明.md](/Users/caixudong/Downloads/zhilian-robot/Neo4j_v2_数据结构说明.md)，`v2` 图适合作为：

- 事实增强层
- 文档证据层
- 事件层
- 脉络聚合层
- 运行分析层

强项：

- 有 `summary`
- 有 `mainBusiness` / `businessScope`
- 有 `Document` / `Chunk` / `Episodic` / `StoryThread`
- 有 `momentum_score` / `pageRank` / `communityId`

弱项：

- 实体标准化未必与 Wikidata 一致
- 节点主键是内部 `uuid`
- 外部标准标识不一定齐全

### 4.3 基于当前节点样本的额外判断

根据 [neo4j_v2_node_samples.md](/Users/caixudong/Downloads/zhilian-robot/neo4j_v2_node_samples.md)，当前 `v2` 图有几个会直接影响融合实现的现实约束。

#### 约束一：大多数实体没有强外部主键

样本里几乎看不到以下强标识：

- `unifiedSocialCreditCode`
- 标准官网域名
- 标准产品编码
- 标准行业编码

能稳定使用的字段主要是：

- `name`
- `summary`
- `description`
- 少量业务字段，例如 `brand`、`mainBusiness`、`applicationScenario`
- 内部 `uuid`

结论：

1. `v2.uuid` 只能作为来源侧内部 ID，不能作为跨图融合主键。
2. 第一阶段实体匹配必须以 `name/alias/context` 为主，不能假设大规模主键直连。

#### 约束二：标签质量不稳定，必须先做类型重分类

样本里已经出现明显标签漂移：

- `Person` 样本实际内容是“某企业宣布新品”，更像企业新闻片段
- `Industry` 样本 `警务场景` 更像应用场景，不像标准行业
- `Product` 样本 `高德途途` 更像具体产品实例或型号，不一定是标准 `Product`

因此，融合前必须增加一层：

- `type_reclassifier`

输出：

- `original_type`
- `normalized_type`
- `reclassify_reason`
- `reclassify_confidence`

#### 约束三：`summary` 经常承载事实，不只是摘要

样本里的 `summary` 往往混合了：

- 企业业务事实
- 产品发布事实
- 技术能力事实
- 涨价、退出市场等动态事实

因此：

1. `summary` 不能简单当 canonical 主值
2. `summary` 同时要被视为：
   - 可读增强属性
   - 潜在事实证据
   - 可继续二次结构化抽取的输入

#### 约束四：`attributes__*` 字段必须整体保留

样本里存在大量半结构化字段：

- `attributes__应用功能`
- `attributes__应用案例`
- `attributes__合作方`
- `attributes__推广计划`
- `attributes__value`
- `attributes__source`

这类字段第一阶段不做强映射，但必须整体保留到：

- `source_profiles.v2.attributes`

#### 约束五：运行时字段必须保留，但不应混入主事实层

样本中高频出现：

- `momentum_score`
- `momentum_updated_at`
- `pageRank`
- `communityId`
- `created_at`

这些字段对排序、热点分析、社区分析有价值，因此必须保留；但它们不是稳定知识事实，不应直接覆盖 canonical 属性。

---

## 5. 总体融合架构

建议最终统一图分成 4 层。

### 5.1 Canonical 实体层

骨架实体，优先由 `Wikidata` 维护主身份。

主要类型：

- `Enterprise`
- `Product`
- `ProductModel`
- `Technology`
- `Industry`
- `Region`
- `Organization`
- `Person`

特征：

- 每个实体有统一 `graph_id`
- 主属性以 canonical 形式维护
- 面向推理、检索、问答

### 5.2 事实与事件层

保留来自 `v2` 的时态事实和事件对象。

主要类型：

- `EnterpriseEvent`
- `OrganizationEvent`
- `Episodic`
- `StoryThread`

特征：

- 不替代 canonical entity
- 通过 `subject`、`mentions`、`anchor_entity` 等关系连接实体层
- 适合做脉络分析与时序推理

### 5.3 文档证据层

保留原始资讯结构。

主要类型：

- `Document`
- `Chunk`
- `DataSource`

特征：

- 所有抽取事实都尽量能回溯到文档和 chunk
- 适合做证据展示、追溯、纠错、重跑

### 5.4 来源快照层

用于保留“不能直接进 canonical 主属性，但又不能丢”的字段。

建议用两种方式之一：

1. 节点 `source_profiles` 属性
2. 独立 `SourceSnapshot` / `PropertyAssertion` 对象

第一阶段建议先用节点属性承接，后续如有需要再提升为独立对象。

---

## 6. v2 数据如何导入

### 6.1 不建议直接在线图到图 merge

不建议直接把 `v2` Neo4j 库和当前 Wikidata Neo4j 库做在线 Cypher merge，原因是：

1. 两边主键体系不同
2. 匹配逻辑复杂，不能只靠 `MERGE (n {name: ...})`
3. 需要先产出匹配结果和冲突结果
4. 需要保留来源快照和证据对象

### 6.2 推荐导入方式

建议采用：

`v2 Neo4j 导出 -> 中间 DTO -> 融合决策 -> 统一图导入`

推荐流程：

1. 从 `v2 Neo4j` 导出节点和边
2. 转换为统一的 `FusionInputDTO`
3. 在离线融合 pipeline 中完成匹配、融合、证据挂接
4. 输出为新的 `GraphImportBatchDTO`
5. 再统一写入 OpenSPG / Neo4j

### 6.2.1 当前已确认的真实导出包形态

基于真实样本目录 [neo4j_v2_octopus_only_20260510](/Users/caixudong/Downloads/zhilian-robot/neo4j_v2_octopus_only_20260510)，当前 `v2` 导出包已经具备可直接接入的基本条件。

当前包结构：

- `manifest.json`
- `nodes.jsonl`
- `edges.jsonl`
- `README.md`

当前已确认的样本规模：

- 节点：`29`
- 边：`52`

节点标签分布：

- `Enterprise = 9`
- `Product = 10`
- `ProductModel = 2`
- `Technology = 3`
- `Industry = 1`
- `Document = 1`
- `Episodic = 3`

边类型分布：

- `MENTIONS = 26`
- `RELATES_TO = 26`

这里有一个非常关键的实现约束：

- `MENTIONS` 本身就是显式语义边
- `RELATES_TO` 只是通用壳类型
- 真实关系语义存放在 `edges.jsonl.properties.name`

例如当前真实样本里已经出现：

- `IS_A`
- `MANUFACTURES`
- `RELEASES`
- `CONTAINS`
- `ADAPTED_TO`
- `USED_BY`
- `HAS_PRICE_INCREASE`

因此，导入层必须做两步：

1. 先解析 `MENTIONS / RELATES_TO`
2. 对 `RELATES_TO` 再读取 `properties.name` 做二次 predicate 归一

### 6.2.2 当前已落地的第一版接入骨架

当前代码里已经补了一版可运行的最小接入骨架，位置在：

- [neo4j_v2_export_loader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/loaders/neo4j_v2_export_loader.py)
- [wikidata_v2_source_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/mappers/wikidata_v2_source_mapper.py)
- [wikidata_canonical_matcher.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/resolvers/wikidata_canonical_matcher.py)
- [fusion_relation_planner.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/resolvers/fusion_relation_planner.py)
- [wikidata_v2_fusion_runner.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/runners/wikidata_v2_fusion_runner.py)

第一版已经支持：

- 读取 `manifest.json + nodes.jsonl + edges.jsonl`
- 从节点 `labels` 中选出业务 `source_label`
- 从节点属性中提取 `uuid / name / summary`
- 把 `MENTIONS` 归一为 `mentions`
- 把 `RELATES_TO.properties.name` 归一为内部 predicate，例如 `IS_A -> is_a`
- 在融合阶段把 `is_a` 进一步映射为 `belongsToProduct`
- 把整包数据直接转成 `GraphImportBatchDTO`

这版骨架的定位是：

- 先打通真实输入格式
- 再逐步细化关系语义和实体匹配

不是：

- 已经完成所有 `v2` 关系的 canonical 化
- 已经解决所有资讯节点分类问题

### 6.3 导出格式建议

建议对方提供以下任一格式：

1. 推荐：节点 CSV + 关系 CSV
2. 可接受：节点 JSONL + 关系 JSONL
3. 次优：Neo4j APOC 导出的 JSON

推荐表结构：

#### 节点表

- `source_system`
- `source_label`
- `source_uuid`
- `name`
- `summary`
- `properties_json`

#### 关系表

- `source_system`
- `source_predicate`
- `source_edge_uuid`
- `subject_source_uuid`
- `object_source_uuid`
- `properties_json`

### 6.4 中间接入 DTO

建议统一构造成：

- `FusionSourceNodeDTO`
- `FusionSourceEdgeDTO`
- `FusionCandidateDTO`
- `FusionDecisionDTO`
- `FusionEvidenceDTO`

节点 DTO 至少包含：

- `source_system`
- `source_type`
- `source_uuid`
- `name`
- `summary`
- `properties`
- `raw_labels`

边 DTO 至少包含：

- `source_system`
- `predicate`
- `subject_source_uuid`
- `object_source_uuid`
- `properties`

### 6.5 融合映射总原则

本次映射不是要求 `v2` 和 `Wikidata` 字段一一对应，而是采用：

`非对称映射 + 分层保留`

含义如下：

1. `Wikidata` 作为 canonical 骨架，字段更偏标准化、稳定事实。
2. `v2` 作为资讯增强层，字段更偏动态事实、摘要、运行指标。
3. 两边字段不必完全对齐，只要 `v2` 能提供足够的“匹配锚点”和“增强字段”，就可以融合。

这里的“融合”采用链接式实现：匹配阶段仍然判断 `v2` 节点对应哪个 Wikidata canonical 节点，但落图时不把 `v2` 字段直接写入 canonical 节点，而是创建 `NewsEntityProfile` 节点承载动态字段，并建立：

```text
NewsEntityProfile:v2:{source_uuid}
-> refersTo
Wikidata canonical node
```

因此，`v2` 每个字段进入系统后，不是只有“映射到 schema 字段”这一种去向，而是有 5 种去向：

1. `match_keys`
   - 用于实体匹配，不一定落图
2. `canonical_properties`
   - 作为匹配和候选主值使用；当前链接式融合不直接写入 Wikidata canonical 节点
3. `source_profiles`
   - 作为来源增强属性保存到 `NewsEntityProfile`
4. `analytics`
   - 作为运行分析属性保存到 `NewsEntityProfile`
5. `fact_payload`
   - 作为事件/证据/二次抽取输入保存到 `NewsEntityProfile`

### 6.6 通用字段映射表

先定义一张所有节点都适用的通用映射表。

| v2 字段 | 主要用途 | 进入层 | 处理规则 |
| --- | --- | --- | --- |
| `uuid` | 来源内部唯一标识 | `source_profiles.v2.uuid` | 永久保留，不作为跨图主键 |
| `name` | 实体显示名、主匹配键 | `NewsEntityProfile.name` + `match_keys` | 参与匹配；命中后保留在资讯画像节点 |
| `summary` | 可读增强、事实输入 | `source_profiles.v2.summary` + `fact_payload.summary` | 不直接默认进入 canonical 主值 |
| `description` | 可读增强、事实输入 | `source_profiles.v2.description` + `fact_payload.description` | 不直接默认进入 canonical 主值 |
| `labels` | 来源标签 | `source_profiles.v2.labels` | 原样保留 |
| `entity_types` | 来源类型细分 | `source_profiles.v2.entity_types` | 原样保留 |
| `created_at` | 来源写入时间 | `analytics.v2.created_at` | 原样保留 |
| `momentum_score` | 运行分析值 | `analytics.v2.momentum_score` | 不进入 canonical |
| `momentum_updated_at` | 运行分析时间 | `analytics.v2.momentum_updated_at` | 不进入 canonical |
| `pageRank` | 图算法值 | `analytics.v2.pageRank` | 不进入 canonical |
| `communityId` | 社区聚类值 | `analytics.v2.communityId` | 不进入 canonical |
| `name_embedding` | 向量检索值 | `analytics.v2.name_embedding` | 不进入 canonical |
| `group_id` | 来源侧分组信息 | `source_profiles.v2.group_id` | 原样保留 |
| `attributes__*` | 半结构化扩展字段 | `source_profiles.v2.attributes` | 按字典整体保留 |

### 6.7 Enterprise 字段映射表

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是，一级主匹配键 | `name` 候选 | `source_profiles.v2.name` | 企业第一匹配键 |
| `mainBusiness` | 是，辅助重排 | `mainBusiness` 候选 | `source_profiles.v2.mainBusiness` | 若语义稳定，可补主值 |
| `status` | 是，弱辅助 | 不默认直写 | `source_profiles.v2.status` | 更像资讯状态，不等于工商状态 |
| `summary` | 是，行业/身份辅助 | 不默认直写 | `source_profiles.v2.summary` | 也进 `fact_payload` |
| `description` | 是，辅助 | 不默认直写 | `source_profiles.v2.description` | 若后续有可读摘要策略再提升 |
| `officialWebsite` | 若存在则强匹配 | `officialWebsite` | `source_profiles.v2.officialWebsite` | 目前样本少，但一旦有应优先使用 |
| `nameEn` | 是，辅助匹配 | `nameEn` 候选 | `source_profiles.v2.nameEn` | 样本中不稳定时只保留 |
| `unifiedSocialCreditCode` | 若存在则强匹配 | `unifiedSocialCreditCode` | `source_profiles.v2.unifiedSocialCreditCode` | 样本中基本缺失，但保留入口 |
| `region` | 是，辅助重排 | `region` 关系候选 | `source_profiles.v2.region` | 不直接靠字符串落边，需先对齐 Region |
| `belongsToIndustry` | 是，辅助重排 | `belongsToIndustry` 关系候选 | `source_profiles.v2.belongsToIndustry` | 需先对齐 Industry |

### 6.8 Product / ProductModel 字段映射表

#### ProductModel

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是，一级主匹配键 | `name` 候选 | `source_profiles.v2.name` | 具体型号/实例名 |
| `brand` | 是，强辅助 | `brand` | `source_profiles.v2.brand` | 当前样本最有价值的型号锚点 |
| `series` | 是，若存在 | `series` | `source_profiles.v2.series` | 当前样本缺失时允许为空 |
| `model` | 是，若存在 | `model` | `source_profiles.v2.model` | 当前样本缺失时不能作为硬条件 |
| `description` | 否，主要用于增强 | `description` 候选 | `source_profiles.v2.description` | 默认不覆盖 canonical |
| `summary` | 否，主要用于事实提取 | 不默认直写 | `source_profiles.v2.summary` | 也进 `fact_payload` |
| `belongsToProduct` | 是，辅助过滤 | `belongsToProduct` 关系候选 | `source_profiles.v2.belongsToProduct` | 需先对齐 Product |
| `manufacturer` | 是，辅助过滤 | `manufacturer` 关系候选 | `source_profiles.v2.manufacturer` | 需先对齐 Enterprise |

#### Product

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是 | `name` 候选 | `source_profiles.v2.name` | 但第一阶段先尝试重分类为 `ProductModel` |
| `classificationCode` | 若存在则强匹配 | `classificationCode` | `source_profiles.v2.classificationCode` | 当前样本基本缺失 |
| `classificationName` | 是，若存在 | `classificationName` | `source_profiles.v2.classificationName` | 当前样本基本缺失 |
| `description` | 否 | `description` 候选 | `source_profiles.v2.description` | 仅在确认是标准产品时使用 |
| `summary` | 否 | 不默认直写 | `source_profiles.v2.summary` | 用作事实增强 |

### 6.9 Technology / Region / Organization 字段映射表

#### Technology

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是，一级主匹配键 | `name` 候选 | `source_profiles.v2.name` | 当前样本可直接使用 |
| `applicationScenario` | 否，主要用于增强 | `applicationScenario` 候选 | `source_profiles.v2.applicationScenario` | 第一阶段建议保留，不作为强匹配键 |
| `belongsToProduct` | 是，强辅助 | `belongsToProduct` 关系候选 | `source_profiles.v2.belongsToProduct` | 对 `ABot -> 高德途途` 这类很关键 |
| `summary` | 否 | 不默认直写 | `source_profiles.v2.summary` | 进 `fact_payload` |
| `description` | 否 | `description` 候选 | `source_profiles.v2.description` | 若后续摘要策略稳定再提升 |

#### Region

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是，一级主匹配键 | `name` 候选 | `source_profiles.v2.name` | 例如“印尼” |
| `regionCode` | 若存在则强匹配 | `regionCode` | `source_profiles.v2.regionCode` | 当前样本少，但要预留 |
| `category` | 是，辅助 | `category` 候选 | `source_profiles.v2.category` | 国家、省、市等 |
| `attributes__related_news` | 否 | 不进入 canonical | `source_profiles.v2.attributes.related_news` | 典型来源增强字段 |

#### Organization

| v2 字段 | 用于匹配 | canonical 去向 | 其他保留去向 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | 是，一级主匹配键 | `name` 候选 | `source_profiles.v2.name` | 当前样本主要靠它 |
| `officialWebsite` | 若存在则强匹配 | `officialWebsite` | `source_profiles.v2.officialWebsite` | 未来有就优先用 |
| `description` | 否 | `description` 候选 | `source_profiles.v2.description` | 增强属性 |
| `summary` | 否 | 不默认直写 | `source_profiles.v2.summary` | 也进 `fact_payload` |

### 6.10 映射结果对象建议

每个进入融合 pipeline 的 `v2` 节点，建议先被转换成如下结构：

```json
{
  "source_system": "neo4j_v2",
  "source_uuid": "...",
  "original_type": "Product",
  "normalized_type": "ProductModel",
  "match_keys": {
    "name": "高德途途",
    "brand": null,
    "name_en": null,
    "region": null,
    "industry_terms": []
  },
  "canonical_candidates": {
    "name": "高德途途",
    "description": "四足机器人，协助视障人士完成避障、穿行等任务"
  },
  "source_profiles": {
    "v2": {
      "uuid": "...",
      "summary": "...",
      "description": "...",
      "labels": ["Entity", "Product"],
      "attributes": {}
    }
  },
  "analytics": {
    "v2": {
      "momentum_score": 1.0,
      "pageRank": 0.92,
      "communityId": 497
    }
  },
  "fact_payload": {
    "summary": "...",
    "description": "..."
  }
}
```

---

## 7. 关系融合映射表

字段映射解决的是“节点怎么进图”，关系映射解决的是“边怎么进图、进哪一层、怎么保留来源”。

当前建议把 `v2` 关系分成 4 类处理：

1. `canonical_relation`
   - 可以直接进入骨架实体层的稳定关系
2. `canonical_relation_with_evidence`
   - 可以进入骨架实体层，但必须同时保留来源证据
3. `fact_relation`
   - 只进入事实层，不直接写成骨架主边
4. `attach_only_relation`
   - 只作为来源挂接或分析连接，不进入主语义边

### 7.1 Canonical 业务关系映射表

这类关系如果两端节点都已完成实体对齐，可以进入 canonical 图层。

| v2 关系 | 融合后关系 | 进入层 | 是否需要证据 | 说明 |
| --- | --- | --- | --- | --- |
| `belongsToEconomicSector` | `belongsToEconomicSector` | canonical | 是 | 分类关系，较稳定 |
| `belongsToIndustryGroup` | `belongsToIndustryGroup` | canonical | 是 | 分类关系，较稳定 |
| `belongsToIndustry` | `belongsToIndustry` | canonical | 是 | 分类关系，较稳定 |
| `subclassOf` | `subclassOf` | canonical | 是 | 产品层级关系 |
| `manufacturer` | `manufacturer` | canonical | 是 | 产品型号 -> 企业 |
| `coreTechnology` | `coreTechnology` | canonical | 是 | 企业/产品/型号 -> 技术 |
| `corePatent` | `corePatent` | canonical | 是 | 企业 -> 专利 |
| `legalPerson` | `legalPerson` | canonical | 是 | 企业 -> 人物 |
| `personShareholder` | `personShareholder` | canonical | 是 | 企业 -> 人物 |
| `keyPerson` | `keyPerson` | canonical | 是 | 企业 -> 人物 |
| `shareholder` | `shareholder` | canonical | 是 | 企业 -> 企业/组织 |
| `invest` | `invest` | canonical | 是 | 企业 -> 企业/组织 |
| `belongsToGroup` | `belongsToGroup` | canonical | 是 | 企业 -> 组织/集团 |
| `childOrganization` | `childOrganization` | canonical | 是 | 企业/组织层级 |
| `supplier` | `supplier` | canonical_with_evidence | 强制 | 更偏事实关系，但业务价值高 |
| `customer` | `customer` | canonical_with_evidence | 强制 | 更偏事实关系，但业务价值高 |
| `belongsToProduct` | `belongsToProduct` | canonical | 是 | 技术/型号 -> 标准产品 |
| `belongToRegion` | `belongToRegion` | canonical | 是 | 区域层级关系 |
| `locatedIn` | `locatedIn` | canonical | 是 | 组织 -> 区域 |
| `worksForEnterprise` | `worksForEnterprise` | canonical | 是 | 人物 -> 企业 |
| `worksForOrganization` | `worksForOrganization` | canonical | 是 | 人物 -> 组织 |

### 7.2 Canonical 关系的融合规则

对于 `7.1` 中的关系，统一采用以下规则：

1. 两端实体都已对齐到 canonical 节点时，才允许落 canonical 边。
2. 如果 Wikidata 已有同构边：
   - 不重复建边
   - 在边的来源集合中追加 `neo4j_v2`
3. 如果 Wikidata 没有该边：
   - 新建边
   - 在边属性中保留 `source_system=neo4j_v2`
4. 关系来源一律保留：
   - `source_system`
   - `source_edge_uuid`
   - `source_subject_uuid`
   - `source_object_uuid`
   - `confidence`（若有）
   - `evidence_refs`

建议 canonical 关系边的统一附加属性为：

- `_sources`
- `_source_edge_ids`
- `_evidence_refs`
- `_last_merged_at`

### 7.3 事实层关系映射表

这类关系不建议直接抽平为骨架主边，而是保留在文档/事件/episode/thread 层。

| v2 关系 | 融合后关系 | 进入层 | 说明 |
| --- | --- | --- | --- |
| `Document -> hasChunk` | `hasChunk` | evidence | 文档结构关系 |
| `Chunk -> partOf -> Document` | `partOf` | evidence | 文档结构关系 |
| `Document -> mentions -> Entity` | `mentions` | evidence | 文档提及关系 |
| `Chunk -> mentions -> Entity` | `mentions` | evidence | chunk 提及关系 |
| `Chunk -> supports -> Event/Relation` | `supports` | evidence | 证据支持关系 |
| `Episodic -> mentions -> Entity` | `mentions` | fact | 资讯事实提及关系 |
| `Episodic -> describes -> Event` | `describes` | fact | 资讯单元描述事件 |
| `Episodic -> fromDocument -> Document` | `fromDocument` | evidence | 资讯到文档 |
| `StoryThread -> anchorEntity -> Entity` | `anchorEntity` | fact | 脉络锚点 |
| `StoryThread -> contains -> Episodic` | `contains` | fact | 脉络包含资讯单元 |
| `StoryThread -> relatedTo -> Entity` | `relatedTo` | fact | 脉络关联实体 |
| `EnterpriseEvent -> subject -> Enterprise` | `subject` | fact | 企业事件主语 |
| `EnterpriseEvent -> location -> Region` | `location` | fact | 企业事件地点 |
| `OrganizationEvent -> subject -> Organization` | `subject` | fact | 机构事件主语 |
| `OrganizationEvent -> location -> Region` | `location` | fact | 机构事件地点 |
| `EnterpriseEvent -> source -> Document/Episodic` | `source` | evidence | 事件来源 |
| `OrganizationEvent -> source -> Document/Episodic` | `source` | evidence | 事件来源 |

### 7.4 Attach-only 关系映射表

这类关系当前不进入核心知识语义，只做附加连接或后续分析用。

| v2 关系 | 融合后关系 | 进入层 | 说明 |
| --- | --- | --- | --- |
| `Index -> relatedTo -> Entity` | `relatedTo` | analytics | 指标挂接 |
| `DataSource -> supports -> Technology` | `supports` | analytics/evidence | 数据集支撑技术或文档 |
| `DataSource -> supports -> Document` | `supports` | analytics/evidence | 来源对象挂文档 |
| `Entity -> sameCommunity -> Entity` | `sameCommunity` | analytics | 若后续从 `communityId` 派生，不进主图事实层 |

### 7.5 非对称关系融合原则

和字段一样，关系融合也要按“非对称”处理：

1. `Wikidata -> v2`
   - Wikidata 的稳定关系优先保留为 canonical 主边
2. `v2 -> Wikidata`
   - v2 的关系只有在满足稳定业务语义时才升级为 canonical
3. 对于偏动态、偏文本、偏证据的关系：
   - 不强行抽平
   - 保留到事实层/证据层

### 7.6 关系升级策略

有些关系第一阶段不宜直接进 canonical，但可以设升级通道。

建议升级条件：

1. 多来源重复支持
   - 同一边被多篇资讯、多批次抽到
2. 与 Wikidata 骨架语义一致
   - 例如反复出现稳定的 `manufacturer`、`belongsToIndustry`
3. 有明确时间范围且能证明长期成立

例如：

- `supplier`
- `customer`
- `invest`

第一阶段建议：

- 直接保留 `canonical_with_evidence`
- 后续再根据多来源支持度决定是否提升为更稳定的主边

### 7.7 关系边保留字段

无论边进入哪一层，建议统一保留以下字段：

- `source_system`
- `source_edge_uuid`
- `source_subject_uuid`
- `source_object_uuid`
- `source_relation_type`
- `ingested_at`
- `confidence`
- `evidence_refs`
- `valid_from`
- `valid_to`

如果 `v2` 当前没有其中某些字段，先留空，不影响结构设计。

### 7.8 关系融合输出对象建议

建议在 `FusionDecisionDTO` 之外，再单独产出：

- `FusionRelationDecisionDTO`

最少字段：

```json
{
  "source_relation_type": "manufacturer",
  "source_edge_uuid": "edge-001",
  "subject_source_uuid": "node-a",
  "object_source_uuid": "node-b",
  "resolved_subject_graph_id": "ProductModel:wiki:Q2001",
  "resolved_object_graph_id": "Enterprise:wiki:Q1001",
  "decision": "merge_canonical",
  "target_layer": "canonical",
  "predicate": "manufacturer",
  "evidence_refs": ["Document:v2:...", "Chunk:v2:..."]
}
```

---

## 8. 哪些节点可以直接融合

“可以直接融合”不是指直接按名字 merge，而是指：

- 节点语义与 canonical 实体层一致
- 融合后仍然是稳定业务实体，而不是一次性事实对象

建议分为三类。

### 8.1 A 类：直接对齐到 canonical entity

可直接对齐的类型：

- `Enterprise`
- `Product`
- `ProductModel`
- `Technology`
- `Industry`
- `Region`
- `Organization`
- `Person`

这些节点的处理方式是：

1. 先匹配已有 Wikidata 实体
2. 命中则融合到已有节点
3. 未命中则按统一命名空间新建 canonical 节点

### 8.2 B 类：不并入 canonical，但直接挂到 canonical

这类对象是事实增强对象，不适合作为主骨架节点替代实体。

包括：

- `EnterpriseEvent`
- `OrganizationEvent`
- `Document`
- `Chunk`
- `Episodic`
- `StoryThread`
- `DataSource`

处理方式：

1. 保持原对象独立存在
2. 用关系挂接到 canonical entity
3. 不把这类对象的属性写回实体主值

### 8.3 C 类：过渡节点或弱语义节点

例如：

- `Index`
- `labels`
- 一些纯运行分析对象

处理方式：

1. 第一阶段先原样保留
2. 挂到来源快照层或分析层
3. 不进入 canonical 实体层

### 8.4 基于当前样本的标签重分类规则

在进入实体匹配前，建议先增加一层样本驱动的重分类。

#### `Enterprise`

满足任一条件时，优先视为 `Enterprise`：

- `mainBusiness` 非空
- `status` 非空且语义指向企业经营状态
- `name` 呈现明确企业名或品牌主体名
- `summary/description` 中包含企业经营、发布、融资、合作、退出市场等企业语义

#### `ProductModel`

满足任一条件时，优先视为 `ProductModel`，即使原标签是 `Product`：

- 有 `brand`
- 有 `series`
- 有 `model`
- `name` 指向具体商品/型号实例
- `description` 明显描述具体产品能力，而不是抽象产品类别

当前样本中的 `高德途途`、`闪迪外置固态硬盘` 都应优先尝试映射到 `ProductModel`。

#### `Technology`

满足以下特征时保留为 `Technology`：

- 有 `applicationScenario`
- `summary/description` 描述技术体系、模型能力、技术突破
- 有 `belongsToProduct`

#### `Region`

如果 `name` 能映射到国家、省、市、区域名，保留为 `Region`。

#### `Industry`

样本中的 `警务场景` 不建议直接进 canonical `Industry`。

建议处理为：

1. `normalized_type = Industry`
   - 仅在当前 schema 暂时没有更合适类型时使用
2. 同时记录：
   - `source_profiles.v2.semantic_subtype = application_scenario`

后续如果 schema 增加“应用场景”概念节点，再迁移出去。

#### `Person`

如果 `Person` 样本缺少人物特征，且 `summary/description` 明显在描述企业或新闻片段：

- 不直接并入 canonical `Person`
- 标记为：
  - `normalized_type = UnknownEntity`
  - 或转入 `attach_only / review`

当前样本中的 `某企业` 不应作为 `Person` 融合进主图。

---

## 9. 实体匹配怎么做

这是整个方案最关键的部分。

### 9.1 匹配原则

不能假设 `v2` 和 `Wikidata` 字段完全匹配。尤其像：

- `unifiedSocialCreditCode`
- `officialWebsite`
- `nameEn`
- `alias`
- `region`
- `belongsToIndustry`

在两边的完整度都可能不同。

所以要采用：

`强键优先 + 规则匹配 + 语义校验 + 分级决策`

匹配结果不应只有“匹配/不匹配”，而应输出：

- `exact_match`
- `rule_match`
- `candidate_match`
- `new_entity`
- `manual_review`

### 9.2 企业匹配规则

#### 一级强匹配

满足任一即可直接 merge：

1. `unifiedSocialCreditCode` 一致
2. `officialWebsite` 归一化域名一致
3. 已存在外部映射表命中

说明：

- 即使 `Wikidata` 很多节点没有 `unifiedSocialCreditCode`，`v2` 里有的话仍然应优先利用
- 所以接入时需要把 `v2` 的信用代码保留到匹配索引中

#### 二级规则匹配

需要组合命中：

1. `officialName == officialName`
2. `name == name`
3. `name == alias`
4. `nameEn == nameEn`
5. `name + region`
6. `name + belongsToIndustry`

建议评分示例：

- 官网域名一致：100
- 信用代码一致：100
- 标准名一致：90
- 名称一致 + 区域一致：85
- 名称一致 + 行业一致：80
- 别名一致 + 区域一致：75
- 高相似度名称 + 行业 + 区域：70

阈值建议：

- `>= 90`：自动融合
- `75 ~ 89`：候选融合，生成 review 结果
- `< 75`：不自动融合

#### 样本驱动的额外规则

因为当前 `v2` 企业样本常常只有：

- `name`
- `summary`
- `mainBusiness`
- `status`

所以第一阶段企业匹配建议再加入：

1. `name` 与 Wikidata `name` 完全一致时，优先召回
2. `name` 与 Wikidata `alias` 命中时，次优召回
3. 若 `summary/mainBusiness` 中出现明显行业词，则用行业词作为辅助过滤条件

例如：

- `美光`
  - 先召回所有 `name/alias` 命中“美光/Micron”的 Wikidata 企业
  - 再用 `NAND厂商` 这类行业语义做过滤和加分

### 9.3 产品型号匹配规则

优先级：

1. `brand + model`
2. `brand + series + model`
3. `officialName`
4. `manufacturer + model`
5. `belongsToProduct + manufacturer + model`

#### 样本驱动的额外规则

当前 `v2` 的 `ProductModel` 很可能字段稀疏，只带：

- `name`
- `brand`
- `summary`
- `description`

因此匹配时建议：

1. 如果有 `brand`，优先走 `brand + name`
2. 没有 `model` 时，不要求强制命中 `model`
3. 若 `summary/description` 出现“涨价”“发布”“上市”等事件性信息，不把它写入 canonical 主属性，而转入事实证据层

### 9.4 产品匹配规则

优先级：

1. `classificationCode`
2. `classificationName`
3. `name`
4. `subclassOf + name`

#### 样本驱动的额外规则

当前 `v2` 中原标签为 `Product` 的节点，很可能实际上是：

- 具体产品实例
- 具体产品型号
- 可消费产品名

所以第一阶段处理顺序建议改成：

1. 先尝试把 `Product` 样本重分类为 `ProductModel`
2. 只有在其明显代表标准产品类别时，才进入 canonical `Product` 匹配

### 9.5 技术匹配规则

优先级：

1. `name`
2. `nameEn`
3. `belongsToIndustry + name`
4. `belongsToProduct + name`

#### 样本驱动的额外规则

对于像 `ABot` 这样的技术节点，建议加入：

1. `name` 直接匹配
2. `belongsToProduct` 作为强辅助条件
3. `applicationScenario` 不参与主匹配，但要保留到来源增强属性

### 9.6 区域匹配规则

优先级：

1. `regionCode`
2. `name`
3. `name + category`
4. `name + belongToRegion`

### 9.7 组织与人物匹配

#### Organization

优先级：

1. `officialWebsite`
2. `name`
3. `name + category`
4. `name + locatedIn`

#### Person

优先级：

1. `name + worksForEnterprise`
2. `name + worksForOrganization`
3. `name + jobTitle`

---

## 10. 匹配不到时怎么办

### 10.1 可新建 canonical 节点

对于这些类型，如果没有匹配到 Wikidata，但确实是稳定实体，允许新建：

- `Enterprise`
- `Product`
- `ProductModel`
- `Technology`
- `Organization`
- `Person`
- `Region`

新建时建议 ID 规则：

- `Enterprise:fusion:v2:<uuid>`
- `Product:fusion:v2:<uuid>`

也就是说：

- 仍然进入 canonical 实体层
- 但来源标记为 `fusion:v2`

### 10.2 不应新建成 canonical 的对象

这些对象不应和 Wikidata 实体争同一层：

- `Document`
- `Chunk`
- `Episodic`
- `StoryThread`
- `EnterpriseEvent`
- `OrganizationEvent`
- `DataSource`

它们无论是否匹配，都应以独立事实/证据对象存在。

---

## 11. 哪些字段要怎么保留

### 11.1 字段保留原则

本方案不建议只保留最终主值，而是分 3 层保留：

1. `canonical_properties`
2. `source_overlay_properties`
3. `runtime_analytics_properties`

### 11.2 Canonical 主属性

用于统一检索、推理、问答。

例如企业：

- `name`
- `officialName`
- `alias`
- `nameEn`
- `officialWebsite`
- `status`
- `inception`
- `companyScale`
- `mainBusiness`
- `businessScope`
- `region`
- `belongsToIndustry`

规则：

- 能进入 schema 主字段的尽量进入
- 冲突时保留主值和来源

#### 样本驱动的限制

根据当前样本，以下字段不要直接无条件写进 canonical 主属性：

- `summary`
- `description`
- `status`

原因：

1. `summary` 常常是事件事实拼接，不一定是稳定定义
2. `description` 可能来自单篇资讯视角
3. `status` 在 `v2` 里可能是业务动态状态，例如“已退出消费级市场”，不一定等于工商状态

建议：

- `summary`：进入 `source_profiles.v2.summary`
- `description`：进入 `source_profiles.v2.description`
- `status`：若无法明确映射为标准企业状态，进入 `source_profiles.v2.status`

### 11.3 来源增强属性

对于不方便直接写入 canonical 主字段、但又非常有价值的字段，建议保留在：

- `source_profiles.v2.*`

例如：

- `source_profiles.v2.summary`
- `source_profiles.v2.labels`
- `source_profiles.v2.uuid`
- `source_profiles.v2.raw_properties`

针对当前样本，建议额外固定保留：

- `source_profiles.v2.description`
- `source_profiles.v2.entity_types`
- `source_profiles.v2.attributes`
- `source_profiles.v2.original_type`
- `source_profiles.v2.normalized_type`
- `source_profiles.v2.reclassify_reason`

这类字段特点：

- 不一定是 schema 主字段
- 但对业务分析和后续回溯有价值

### 11.4 运行分析属性

这些字段不建议直接并入知识主事实字段，但必须保留：

- `momentum_score`
- `momentum_updated_at`
- `pageRank`
- `communityId`
- `name_embedding`

建议统一存到：

- `analytics.v2.momentum_score`
- `analytics.v2.pageRank`
- `analytics.v2.communityId`
- `analytics.v2.name_embedding`

原因：

1. 它们是运行派生值，不是稳定业务事实
2. 以后可能会被重新计算
3. 但对排序、分析、展示仍然有价值

当前样本里建议固定保留：

- `analytics.v2.momentum_score`
- `analytics.v2.momentum_updated_at`
- `analytics.v2.pageRank`
- `analytics.v2.communityId`
- `analytics.v2.created_at`

### 11.5 文档和事件字段

这些字段应全部尽量保留原样：

#### Document / Episodic

- `title`
- `content`
- `raw_text`
- `source`
- `news_source`
- `news_url`
- `publish_time`
- `valid_at`
- `structured_facts_json`

#### StoryThread

- `thread_type`
- `anchor_entity_uuid`
- `anchor_entity_name`
- `title`

#### Event

- `name`
- `description`
- `category`
- `publishTime`
- `subject`
- `location`
- `source`

---

## 12. 关系怎么融合

### 12.1 可融合为 canonical 关系的边

这些边可以并入实体骨架：

- `belongsToEconomicSector`
- `belongsToIndustryGroup`
- `belongsToIndustry`
- `region`
- `subclassOf`
- `manufacturer`
- `coreTechnology`
- `corePatent`
- `legalPerson`
- `shareholder`
- `invest`
- `belongsToGroup`
- `childOrganization`
- `supplier`
- `customer`

规则：

1. 如果和 Wikidata 已有边同构，则合并来源
2. 如果 Wikidata 没有，则新增
3. 边属性上保留：
   - `source_system`
   - `evidence_ref`
   - `confidence`

### 12.2 应保留为事实层边的关系

这些关系不建议简单抽平到骨架上：

- `Document -> mentions -> Entity`
- `Chunk -> mentions -> Entity`
- `Episodic -> mentions -> Entity`
- `StoryThread -> anchor_entity -> Entity`
- `EnterpriseEvent -> subject -> Enterprise`
- `EnterpriseEvent -> location -> Region`

原因：

1. 它们是事实/证据语义
2. 有时间性
3. 有上下文依赖

---

## 13. 文档、Chunk、Episodic、StoryThread 怎么组织

这几个对象不应该直接并入 Wikidata 骨架，但必须纳入统一大图。

建议组织方式如下。

### 13.1 Document

独立节点保留。

关系建议：

- `Document -> hasChunk -> Chunk`
- `Document -> fromSource -> DataSource`
- `Document -> mentions -> Enterprise/Product/...`

### 13.2 Chunk

独立节点保留。

关系建议：

- `Chunk -> partOf -> Document`
- `Chunk -> mentions -> Entity`
- `Chunk -> supports -> Relation/Event`

### 13.3 Episodic

作为资讯事实单元保留。

关系建议：

- `Episodic -> mentions -> Entity`
- `Episodic -> describes -> Event`
- `Episodic -> fromDocument -> Document`

### 13.4 StoryThread

作为脉络聚合对象保留。

关系建议：

- `StoryThread -> anchorEntity -> Enterprise`
- `StoryThread -> contains -> Episodic`
- `StoryThread -> relatedTo -> Industry/Product/Technology`

这样可以让大图同时支持：

- 常识检索
- 资讯证据回溯
- 脉络追踪

### 13.5 Index 和 DataSource 的组织方式

根据当前样本：

- `Index` 更像指标概念或指标值承载节点
- `DataSource` 更像数据集实体或来源对象

建议第一阶段处理方式：

#### Index

- 不进入 canonical 主业务实体层
- 作为增强节点保留
- 可挂到：
  - `Technology`
  - `Product`
  - `EnterpriseEvent`
  - `Document`

同时保留：

- `attributes__value`
- `attributes__source`

#### DataSource

- 不直接并入 canonical `Product/Technology/Enterprise`
- 作为独立来源对象保留
- 可连接到：
  - `Technology`
  - `Document`
  - `Chunk`

---

## 14. 建议的融合输出结构

建议每次融合运行输出 4 类结果。

### 14.1 matched_entities.jsonl

记录：

- `source_uuid`
- `source_type`
- `matched_graph_id`
- `match_method`
- `match_score`

### 14.2 new_entities.jsonl

记录：

- `source_uuid`
- `source_type`
- `new_graph_id`

### 14.3 conflict_report.jsonl

记录：

- `entity_graph_id`
- `field_name`
- `canonical_value`
- `incoming_value`
- `source_system`
- `resolution`

### 14.4 graph_batch.json

最终统一导入批次。

---

## 15. 基于当前样本的第一阶段具体融合策略

为了让方案能直接实施，第一阶段建议按下面的方式落。

### 15.1 Enterprise

处理方式：

1. 先重分类确认仍是 `Enterprise`
2. 使用 `name/alias/nameEn/summary行业词` 做匹配
3. 命中 Wikidata 企业则融合
4. `mainBusiness` 优先作为增强属性补充
5. `status` 不直接写主值，先保留到 `source_profiles.v2.status`

### 15.2 ProductModel

处理方式：

1. 原 `Product` 和 `ProductModel` 都先尝试归一到 `ProductModel`
2. 用 `brand + name` 和 `name` 匹配
3. `description` 保留到 `source_profiles.v2.description`
4. 若 `summary` 描述涨价、发布等动态事件，则转入事件/事实层

### 15.3 Technology

处理方式：

1. 用 `name` 做主匹配
2. 用 `belongsToProduct` 做辅助过滤
3. `applicationScenario` 整体保留
4. 若匹配到产品型号，建立 `Technology -> belongsToProduct -> ProductModel`

### 15.4 Region

处理方式：

1. 用 `name` 或后续补充的 `regionCode` 匹配
2. `attributes__related_news` 不进入主值，保留到 `source_profiles`

### 15.5 Organization

处理方式：

1. 用 `name` 直接匹配
2. `description` 和 `summary` 作为增强属性
3. 后续若和 `Enterprise` 有边，再通过关系辅助判断是否需要进一步归并

### 15.6 Industry

处理方式：

1. 暂不直接并入 canonical `Industry`
2. 先保留原节点
3. 在 `source_profiles.v2.semantic_subtype` 中标记其更像：
   - `application_scenario`
4. 等 schema 扩展后再正式迁移

### 15.7 Person

处理方式：

1. 当前样本这种明显错误类型不自动并入
2. 进入 `review` 集合
3. 暂不生成 canonical `Person`

---

## 16. 融合 Pipeline 设计

建议实现成如下 8 步：

1. `v2_export_reader`
   - 读取 `v2` 导出节点和边
2. `v2_schema_normalizer`
   - 转成统一 DTO
3. `fusion_candidate_builder`
   - 为每个业务实体生成匹配候选 key
4. `entity_matcher`
   - 去 canonical 图里做匹配
5. `merge_planner`
   - 生成 merge / create / attach-only / review 决策
6. `property_merger`
   - 融合字段并保留来源快照
7. `relationship_merger`
   - 融合稳定边并组织事实层边
8. `fusion_graph_writer`
   - 输出统一图批次并导入 OpenSPG

---

## 17. 第一阶段建议实施范围

不要一上来融合全部对象，建议分阶段。

### 第一阶段

先做：

- `Enterprise`
- `Product`
- `ProductModel`
- `Technology`
- `Region`
- `Document`
- `Chunk`
- `EnterpriseEvent`
- `Episodic`

原因：

- 企业是主轴
- 产品和技术是产业链核心
- 区域是常见约束条件
- 文档/事件是资讯价值主要来源

### 第二阶段

再做：

- `Organization`
- `Person`
- `StoryThread`
- `Policy`
- `Patent`

---

## 18. 实施前需要补齐的数据要求

在真正实施前，建议从对方拿到：

1. `v2` 节点导出
2. `v2` 关系导出
3. 每个标签的字段字典
4. 是否有标准化字段说明
5. 是否有唯一标识字段说明
6. `Document / Chunk / Episodic / Event` 与实体的连接关系导出

如果对方可以直接给：

- 节点 CSV
- 关系 CSV
- 字段说明表

就足够启动第一阶段实施。

---

## 19. 最终建议

这次融合不应理解为：

`把 v2 图导进 Wikidata 图`

而应理解为：

`基于 Wikidata canonical 骨架，把 v2 的业务实体、事件、文档、脉络和运行分析信息有规则地并入统一大图`

实施上最关键的不是导入工具本身，而是：

1. 实体匹配规则
2. 字段保留策略
3. 事实层与骨架层分层组织
4. 冲突与来源保留

只要这四件事设计对了，后续不只是 `v2` 资讯图，其他资讯子图、研报子图、政策子图也都能沿用同一套融合框架接进来。
