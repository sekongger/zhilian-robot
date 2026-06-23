# Wikidata 产业知识构建 Pipeline 说明

## 1. 文档目的

本文档用于正式说明当前基于 Wikidata 的产业知识构建 pipeline，包括：

- 这条 pipeline 要解决什么问题
- 输入数据和输出数据分别是什么
- 中间经历了哪些处理步骤



---

## 2. 总体目标

当前这条 pipeline 的目标，不是从非结构化长文本中做开放式抽取，而是：

1. 从 Wikidata 原始结构化数据中筛选出与产业相关的实体；
2. 按照 [IncCoreV2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCoreV2.schema) 的定义，将 Wikidata 字段映射为企业、产品、行业、区域等标准化对象；
3. 构建可落入 OpenSPG 的图谱数据；
4. 同步将企业、产品型号等关键对象发布到远程业务数据库，便于后续检索、分析和复用。

一句话概括：

`Wikidata 结构化原始数据 -> IncCoreV2 标准化实体/关系 -> 图谱构建 -> 图数据库与业务数据库发布`

---

## 3. 输入与输出

### 3.1 输入

当前 pipeline 的输入是 Wikidata dump 中的原始实体记录。  
每条记录典型包含：

- `id`
- `labels`
- `aliases`
- `descriptions`
- `claims`
- `sitelinks`

数据读取方式为远程流式读取，不要求先将整个 Wikidata dump 完整下载到本地。

核心读取模块：

- [wikidata_reader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/wikidata_reader.py)

### 3.2 输出

当前 pipeline 有三类输出：

#### 输出一：图分片文件

用于本地检查、中间产物管理和断点恢复。

典型文件包括：

- `graph_batch_000001.json`
- `coverage_report_000001.json`
- `manifest.json`

输出目录示例：

- [all_industry_20260426_schema_v2](/Users/caixudong/Downloads/zhilian-robot/tmp/wiki_industry_full_export/all_industry_20260426_schema_v2)

#### 输出二：OpenSPG 图数据

图分片可以进一步导入本地 OpenSPG / Neo4j，形成可查询、可视化的知识图谱。

主要对象包括：

- `Enterprise`
- `ProductModel`
- `Product`
- `Industry`
- `Region`

#### 输出三：远程 MySQL 表

当前已经支持将关键业务对象发布到远程表：

- `wiki_enterprise_cxd`
- `wiki_product_model_cxd`

这两张表中的数据来自当前图分片的重新清表发布结果。

---

## 4. Pipeline 总体流程

当前 pipeline 可以拆成 6 个步骤。

### 4.1 步骤一：流式读取 Wikidata 数据

系统从 Wikidata dump 逐条读取原始实体记录，不要求先将 100GB 级别的大文件完整落盘。

主要能力：

- 支持本地文件读取
- 支持远程 URL 流式读取
- 支持 `.bz2` / `.gz` 压缩格式
- 支持 limit 与 skip_records

核心模块：

- [wikidata_reader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/wikidata_reader.py)

这一阶段的输出仍然是原始 Wikidata 记录，只是读取方式变成了可持续处理的流。

### 4.2 步骤二：候选实体筛选

不是所有 Wikidata 实体都进入产业图谱。  
系统会先按类型白名单筛选候选实体。

筛选主要依据：

- `P31`：instance of
- `P279`：subclass of
- 少量属性触发规则，例如 `P176 manufacturer`

当前主要筛出的候选类别包括：

- `Enterprise`
- `ProductModel`
- `Industry`
- `Technology`
- `Region`

同时，这一步还会保留实体的上下文信息：

- 主 label
- 多语言 label
- aliases
- description

这些上下文信息后续会用于：

- 填充节点基础属性
- 给 stub 节点补名称
- 提升图上节点可读性

核心模块：

- [candidate_filter.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/candidate_filter.py)
- [wikidata_type_whitelist.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.yaml)
- [wikidata_type_whitelist.expanded.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.expanded.yaml)

### 4.3 步骤三：Claim 标准化抽取

候选实体进入后，会把它的原始 Wikidata `claims` 转成统一的 claim 结构。

例如：

- 时间值转换为标准化日期候选
- 实体引用转换为目标 QID
- 数值、字符串、URL 转成统一字段值

这一阶段的目标不是直接构图，而是把 Wikidata 原始 snak 变成统一结构的 `WikiClaimDTO`，便于后续按 schema 路由。

核心模块：

- [claim_extractor.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/claim_extractor.py)

### 4.4 步骤四：按 IncCoreV2.schema 做字段与关系路由

这是整个 pipeline 中最关键的一层。

我们不是按自由规则去抽字段，而是按 [IncCoreV2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCoreV2.schema) 中定义的字段和关系，将 Wikidata property 路由到标准 schema 字段。

核心配置：

- [IncIndustryWiki.routing.schema.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/IncIndustryWiki.routing.schema.yaml)

当前已接入的典型映射包括：

#### 企业字段映射

- `P1448 -> officialName`
- `P1813 -> shortName`
- `P856 -> officialWebsite`
- `P571 -> inception`
- `P1128 -> companyScale`
- `P576 -> status`
- `description -> mainBusiness`
- `description -> businessScope`

#### 企业关系映射

- `P452 -> belongsToIndustry`
- `P159 / P17 / P131 / P276 -> region`
- `P127 -> shareholder`
- `P355 -> childOrganization`
- `P1056 -> 反向补 manufacturer`

#### 产品型号字段映射

- `P1448 -> officialName`
- `P1813 -> shortName`
- `P1716 -> brand`
- `P179 -> series`
- `P528 -> model`
- `P577 -> publishDate`
- `publishDate -> productLifecycleStatus=launched`

#### 产品型号关系映射

- `P176 / P178 -> manufacturer`
- `P31 -> belongsToProduct`

#### 标准产品关系映射

- `P279 -> subclassOf`

这一阶段输出的是“路由后的 claim”，本质上完成了：

`Wikidata Property -> IncCoreV2 字段/关系`

### 4.5 步骤五：图对象构建

路由后的结果会进一步映射成统一图对象，形成标准的图导入批次。

输出对象包括：

- `entity_nodes`
- `concept_nodes`
- `event_nodes`
- `edges`

当前这条 Wikidata pipeline 的重点，主要在实例层和关系层。

核心模块：

- [graph_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/graph_mapper.py)

这一阶段做了几项关键增强：

#### 1. 节点字段补齐

企业节点当前已经可以落出：

- `name`
- `officialName`
- `shortName`
- `alias`
- `description`
- `nameEn`
- `officialWebsite`
- `inception`
- `companyScale`
- `status`
- `mainBusiness`
- `businessScope`

产品型号节点当前已经可以落出：

- `name`
- `officialName`
- `shortName`
- `alias`
- `description`
- `nameEn`
- `brand`
- `series`
- `model`
- `publishDate`
- `productLifecycleStatus`

#### 2. Stub 节点可读性增强

以前很多关系目标节点只会显示成 `Q3001` 这种 QID。  
现在同批原始记录中的上下文信息会传入 mapper，因此像 `Region`、`Product` 这类 stub 节点，也能补出：

- `name`
- `officialName`
- `shortName`
- `alias`
- `description`
- `nameEn`

例如 `Region:wiki:Q3001` 现在可以显示为“深圳”，不再只是 QID。

