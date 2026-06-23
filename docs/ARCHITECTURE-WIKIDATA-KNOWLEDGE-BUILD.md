# Wikidata 知识构建架构文档

更新时间：2026-05-24

## 1. 文档目的

这份文档是当前项目中“基于 Wikidata 构建产业知识图谱”链路的主架构说明。

以后所有围绕 `wiki_industry_pipeline` 的开发，都应先参考本文档；每次完成开发后，也必须回到本文档，更新以下内容：

- 当前架构是否发生变化
- 新增或删除了哪些模块
- 哪些字段映射、关系映射、输出链路发生了变化
- 当前实现状态、已知问题、运行方式是否需要调整

这份文档的定位不是汇报材料，而是研发主文档。目标是让任何一个接手这个链路的人，在不先通读代码的前提下，也能快速理解：

- 我们在做什么
- 为什么这样做
- 代码主要在哪里
- 数据如何流动
- 当前做到什么程度
- 改完代码后应该更新文档的哪些位置

## 2. 一句话架构

当前 Wikidata 知识构建链路的核心架构是：

`Wikidata 原始结构化数据 -> 类型白名单筛选 -> claim 标准化 -> IncCoreV2 字段/关系映射 -> 图分片 -> OpenSPG 落图 -> MySQL 发布`

这条链路的目标不是从自由文本做开放式抽取，而是从 Wikidata 的结构化实体记录中，筛选产业相关对象，并按照 `IncCoreV2.schema` 映射为企业、产品型号、标准产品、行业、区域等图谱对象。

## 3. 架构范围与非目标

### 3.1 当前范围

本文档只覆盖与 Wikidata 产业知识构建直接相关的部分：

- Wikidata 数据读取
- 候选实体筛选
- 类型白名单体系
- claim 抽取与标准化
- 按 `IncCoreV2.schema` 做字段和关系映射
- 图分片生成
- OpenSPG 导图
- MySQL 业务表发布

### 3.2 非目标

以下内容不属于本文档重点：

- 通用资讯抽取 pipeline
- 研报/资讯事实层抽取的详细实现
- 全平台前端工作台总架构
- OpenKS 其他模块的完整产品架构
- DataFlow 全量设计

如果这些系统与 Wikidata 构图链路发生交互，只在本文档中描述它们与当前链路的边界，不展开完整设计。

### 3.3 与 Neo4j v2 资讯融合链路的边界

本文档仍然以 `Wikidata -> IncCoreV2 -> OpenSPG/MySQL` 这条主构图链为核心，但从 `2026-05-10` 开始，代码库里已经补入了一条“以 Wikidata 图为 canonical 骨架，对接 `Neo4j v2` 资讯子图”的第一版融合骨架。

这里的边界是：

- `wiki_industry_pipeline`
  - 负责构建 Wikidata 常识骨架
- `incore_fusion_pipeline`
  - 负责把外部子图映射、匹配并链接到 canonical 骨架

当前这两条链路是前后衔接关系，不是互相替代关系。

### 3.4 与 Graphiti 资讯收集链路的边界

从 `2026-05-24` 开始，根目录下引入 `graphiti_news_pipeline` 作为独立资讯收集子项目。它来自 `lyw/graphiti` 分支，负责执行“资讯源接入、清洗、去重、压缩、Graphiti 抽取、Graphiti Neo4j 写入”。

这条链路不直接修改 Wikidata canonical 节点。标准接入方式是：

```text
graphiti_news_pipeline
-> crawler run_id 作为 Graphiti group_id / fusion_batch_id
-> Graphiti Neo4j 中的 Entity / Episodic / 关系
-> GraphitiNewsNeo4jLoader 按 group_id 读取本批数据及相邻实体
-> GraphitiNewsFusionRunner
-> WikidataV2FusionRunner
-> NewsEntityProfile:graphiti:* / ...:fusion:graphiti:*
-> refersTo / candidate-like 动态挂接关系
-> OpenSPG 或 Neo4j 大图
```

也就是说，Graphiti 负责“从资讯文本抽取动态事实”，`incore_fusion_pipeline` 负责“把动态事实挂到 Wikidata 常识骨架上”。二者的边界必须保持清晰，避免高频资讯字段直接覆盖低频常识节点。

从 `2026-05-24` 的最新实现开始，Graphiti 资讯链路要求每次 crawler run 都带上批次边界：`graphiti_group_id = crawler run_id`。`/api/add-text` 会把这个值透传给 `Graphiti.add_episode(group_id=...)`，同时写入 Episodic 的 `group_id / fusion_batch_id` 元数据。后续融合脚本默认用该 `group_id` 读取本批次 Graphiti 输出，避免把历史资讯图谱误融合进当前批次。

## 4. 核心目标

当前这条链路服务的核心目标有四个：

1. 从 Wikidata 中尽可能稳定地筛出产业相关实体，避免把无关对象大规模带入图谱。
2. 严格按 `IncCoreV2.schema` 的字段和关系定义进行映射，而不是自由拼装一套临时字段。
3. 构建既能落到 OpenSPG 图数据库、又能同步发布到业务 MySQL 表的统一数据产物。
4. 让生成的企业、产品、行业、区域节点不只是“有一个名字和几条边”，而是尽可能贴近 schema 中定义的标准结构。

## 5. 系统分层

从实现上看，当前 Wikidata 知识构建架构可拆成 6 层。

### 5.1 数据源层

负责提供原始结构化输入。

当前主要数据源：

- Wikidata dump
- Wikidata HTTP 拉取结果

当前实现特点：

- 支持远程流式读取
- 支持本地文件读取
- 支持 `.bz2` / `.gz` / 普通文本

对应模块：

- [wikidata_reader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/wikidata_reader.py)
- [wikidata_fetcher.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/wikidata_fetcher.py)

### 5.2 候选筛选层

负责回答两个问题：

- 这个 Wikidata 实体是否值得进入后续构图
- 如果进入，它初步属于哪一类对象

当前主要类别：

- `Enterprise`
- `ProductModel`
- `Product`
- `Industry`
- `Technology`
- `Region`

对应模块：

- [candidate_filter.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/candidate_filter.py)
- [type_whitelist.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/type_whitelist.py)
- [type_taxonomy_expander.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/type_taxonomy_expander.py)

### 5.3 claim 标准化层

负责把 Wikidata 原始 `claims` 中的 snak 结构解析成统一的内部 claim DTO，屏蔽日期、实体引用、数量、字符串等底层格式差异。

对应模块：

- [claim_extractor.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/claim_extractor.py)

### 5.4 schema 路由层

负责把“Wikidata property”翻译成“IncCoreV2 的字段或关系”，是整条链路最关键的语义映射层。

对应模块和配置：

- [claim_router.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/claim_router.py)
- [schema_loader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/schema_loader.py)
- [IncIndustryWiki.routing.schema.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/IncIndustryWiki.routing.schema.yaml)
- [wikidata_property_mapping.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_property_mapping.yaml)

### 5.5 图对象构建层

负责把候选实体基础上下文和路由后的 claim 合成最终图对象。

输出对象包括：

- `entity_nodes`
- `concept_nodes`
- `event_nodes`
- `edges`

当前 Wikidata 链路主要聚焦：

- 实例层节点
- 关系层边
- 部分标准产品和区域层级

对应模块：

- [graph_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/graph_mapper.py)
- [concept_builder.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/concept_builder.py)
- [entity_resolver.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/entity_resolver.py)
- [dto.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/dto.py)

### 5.6 输出与发布层

负责把图对象变成可消费产物。

当前有三类主要输出：

1. 图分片 JSON
2. OpenSPG 图数据库
3. 远程 MySQL 业务表

对应模块和脚本：

- [sharded_export.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/sharded_export.py)
- [coverage_reporter.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/coverage_reporter.py)
- [kag_adapter.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/kag_adapter.py)
- [import_graph_batch_to_mysql.py](/Users/caixudong/Downloads/zhilian-robot/scripts/wiki_industry/import_graph_batch_to_mysql.py)

## 6. 关键目录与代码责任

### 6.1 后端主目录

Wikidata 知识构建的主实现集中在：

- [backend/app/wiki_industry_pipeline](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline)

这个目录内模块职责建议理解为：

- `wikidata_reader.py`
  - 负责读原始数据流
- `wikidata_fetcher.py`
  - 负责按 Wikidata API / 拉取方式补充数据
- `candidate_filter.py`
  - 负责候选准入和类型归类
- `type_whitelist.py`
  - 负责加载白名单配置
- `type_taxonomy_expander.py`
  - 负责把种子类型扩展成更完整的子类集合
- `claim_extractor.py`
  - 负责 claim 标准化抽取
- `claim_router.py`
  - 负责按 schema 路由字段和关系
- `graph_mapper.py`
  - 负责组装最终图对象
- `entity_resolver.py`
  - 负责实体层面补充和对齐
- `concept_builder.py`
  - 负责概念层相关生成逻辑
- `kag_adapter.py`
  - 负责接 OpenSPG/KAG 导图链
- `sharded_export.py`
  - 负责分片导出
- `cli.py`
  - 负责统一命令行入口
- `dto.py`
  - 负责全链路 DTO 定义

### 6.2 配置目录

Wikidata 构图相关配置集中在：

- [configs/industry_wiki](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki)

当前关键配置包括：

- [wikidata_type_whitelist.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.yaml)
  - 种子白名单
- [wikidata_type_whitelist.expanded.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.expanded.yaml)
  - 可执行扩展白名单
- [IncIndustryWiki.routing.schema.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/IncIndustryWiki.routing.schema.yaml)
  - Wikidata 到 `IncCoreV2` 的主路由配置
- [wikidata_property_mapping.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_property_mapping.yaml)
  - 属性映射补充配置

### 6.3 发布脚本目录

Wikidata 链路相关脚本集中在：

- [scripts/wiki_industry](/Users/caixudong/Downloads/zhilian-robot/scripts/wiki_industry)

当前关键脚本：

- [expand_wikidata_type_whitelist.py](/Users/caixudong/Downloads/zhilian-robot/scripts/wiki_industry/expand_wikidata_type_whitelist.py)
  - 用于生成 expanded 白名单
- [import_graph_batch_to_mysql.py](/Users/caixudong/Downloads/zhilian-robot/scripts/wiki_industry/import_graph_batch_to_mysql.py)
  - 用于把图分片中的企业/产品型号发布到远程 MySQL
- [import_fusion_batch_to_neo4j.py](/Users/caixudong/Downloads/zhilian-robot/scripts/fusion/import_fusion_batch_to_neo4j.py)
  - 用于把链接式融合后的 `fusion_batch.json` 直接写入 Neo4j，便于在 Neo4j Browser 中查看 `NewsEntityProfile -> refersTo -> WikidataNode` 结构

### 6.4 Neo4j v2 融合骨架目录

与 Wikidata 主图衔接的第一版融合骨架位于：

- [backend/app/incore_fusion_pipeline](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline)

当前新增的关键模块包括：

- [neo4j_v2_export_loader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/loaders/neo4j_v2_export_loader.py)
  - 负责读取 `Neo4j v2` 导出包中的 `manifest.json / nodes.jsonl / edges.jsonl`
- [wikidata_shard_canonical_index_loader.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/loaders/wikidata_shard_canonical_index_loader.py)
  - 负责从现有 `graph_batch_*.json` 中抽取 Wikidata canonical 节点索引，直接复用当前 shard 产物作为融合骨架
- [wikidata_v2_fusion_dto.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/dto/wikidata_v2_fusion_dto.py)
  - 负责承接 `v2` 输入、匹配决策和融合运行结果
- [wikidata_v2_source_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/mappers/wikidata_v2_source_mapper.py)
  - 负责把 `v2` 节点拆成 `match_keys / canonical_candidates / source_profiles / analytics / fact_payload`
- [wikidata_canonical_matcher.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/resolvers/wikidata_canonical_matcher.py)
  - 负责基于名称和别名做第一版骨架匹配
- [fusion_relation_planner.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/resolvers/fusion_relation_planner.py)
  - 负责把 `v2` 边归类为 `canonical / fact / evidence`
- [wikidata_v2_fusion_runner.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/runners/wikidata_v2_fusion_runner.py)
  - 负责把一个 `v2` 导出包跑成 `GraphImportBatchDTO`
  - 当前已经支持直接输入 `wikidata_shard_dir + v2_export_dir`，不需要重新整理一份中间 Wikidata 索引文件
  - 当前采用链接式融合：匹配成功的资讯实体会生成 `NewsEntityProfile` 节点，再通过 `refersTo` 关系指向 Wikidata canonical 节点

当前状态需要明确：

- 这条融合骨架已经能读取真实 `neo4j_v2` 导出包
- 已经能读取现有 `29` 个 Wikidata shard 并构造成 canonical index
- 已经能把 `MENTIONS`、`RELATES_TO.properties.name` 归一进内部 predicate
- 已经能生成统一 `GraphImportBatchDTO`
- 已经能基于真实样本完成第一版 match/create 决策，并将 match 结果落为 `NewsEntityProfile -> refersTo -> WikidataNode`
- 已经能把链接式融合 batch 写入本地 OpenSPG Neo4j 的 `inccore` 库做图形化查看
- 还没有完成完整的实体强匹配、属性冲突裁决和 OpenSPG schema 级导入执行

当前真实样本运行结果：

- 输入：
  - `neo4j_v2_octopus_only_20260510`
  - `all_industry_20260426_schema_v2` 下的 `29` 个 shard
- 输出：
  - `29` 个资讯节点中，当前规则下 `2` 个节点匹配到 Wikidata 骨架，并生成 `2` 个 `NewsEntityProfile` 与 `2` 条 `refersTo` 身份链接
  - 其余 `27` 个节点保持 `fusion:v2` 新建节点

### 6.5 Graphiti 资讯接入目录

Graphiti 资讯收集项目已放在根目录：

- [graphiti_news_pipeline](/Users/caixudong/Desktop/zhilian-robot/graphiti_news_pipeline)

它保持独立运行边界，不直接并入 `backend/app`。主工程只新增适配层：

- [graphiti_news_neo4j_loader.py](/Users/caixudong/Desktop/zhilian-robot/backend/app/incore_fusion_pipeline/loaders/graphiti_news_neo4j_loader.py)
  - 负责从 Graphiti Neo4j 中读取 `Entity / Episodic / Relationship`，转换成统一的 `V2SourceNodeDTO / V2SourceEdgeDTO`
  - 当指定 `group_id` 时，会读取本批 `group_id / fusion_batch_id` 命中的节点，并补齐它们的一跳相邻实体，避免 Graphiti 只在 Episodic 上写批次字段时丢失实体
- [graphiti_news_fusion_runner.py](/Users/caixudong/Desktop/zhilian-robot/backend/app/incore_fusion_pipeline/runners/graphiti_news_fusion_runner.py)
  - 负责复用 `WikidataV2FusionRunner`，把 Graphiti 动态资讯层挂接到 Wikidata canonical 骨架
- [run_graphiti_news_big_graph_fusion.py](/Users/caixudong/Desktop/zhilian-robot/backend/scripts/run_graphiti_news_big_graph_fusion.py)
  - 负责一条命令执行“可选跑 Graphiti crawler -> 读取 Graphiti Neo4j -> 融合 Wikidata shard -> 输出/落图”
  - 当前已经承担 Graphiti API 健康检查、数据库初始化、crawler JSON 摘要解析、ingest 全失败保护、自动按 crawler run id 设置 `group_id`、融合报告输出

Graphiti 接入生成的图 ID 使用 `graphiti` namespace，例如：

- `NewsEntityProfile:graphiti:{graphiti_uuid}`
- `Enterprise:fusion:graphiti:{graphiti_uuid}`
- `Episodic:fusion:graphiti:{graphiti_uuid}`

这样可以和历史 `Neo4j v2` 接入的 `...:v2:...` 区分开。
- 说明：
  - 当前规则已经能打通真实链接链路，但匹配规则仍偏保守，后续需要继续补企业别名、英文名、品牌/型号组合等规则

## 7. 核心数据流

当前主数据流如下：

```text
Wikidata dump / API
-> wikidata_reader / wikidata_fetcher
-> candidate_filter
-> claim_extractor
-> claim_router
-> graph_mapper
-> graph_batch_xxxxxx.json / coverage_report / manifest
-> kag_adapter / OpenSPG
-> import_graph_batch_to_mysql.py
```

与之并行的 `Neo4j v2 -> Wikidata 骨架` 融合数据流如下：

```text
Neo4j v2 export package
-> neo4j_v2_export_loader
-> wikidata_v2_source_mapper
-> wikidata_shard_canonical_index_loader
-> wikidata_canonical_matcher
-> fusion_property_merger / fusion_relation_planner
-> wikidata_v2_fusion_runner
-> GraphImportBatchDTO / 链接决策报告
```

新增的 `Graphiti 资讯 -> Wikidata 骨架` 融合数据流如下：

```text
graphiti_news_pipeline crawler
-> run_id 注入 Graphiti add-text payload(group_id / fusion_batch_id)
-> Graphiti add_episode / entity extraction
-> Graphiti Neo4j
-> graphiti_news_neo4j_loader(group_id scoped)
-> wikidata_shard_canonical_index_loader
-> wikidata_v2_source_mapper
-> wikidata_canonical_matcher
-> graphiti_news_fusion_runner
-> GraphImportBatchDTO / NewsEntityProfile:graphiti:* / refersTo
-> OpenSPG 或 Neo4j 可视化图
```

对应语义可以拆成 7 步：

1. 读取 Wikidata 实体记录
2. 根据类型白名单和少量属性规则筛选候选实体
3. 把原始 claims 展开成统一 claim DTO
4. 按 `IncCoreV2.schema` 路由字段和关系
5. 生成图节点和图边
6. 按 shard 输出中间图产物
7. 导入 OpenSPG，并向业务 MySQL 表发布核心对象

## 8. 白名单体系如何服务过滤任务

### 8.1 白名单的职责

白名单不是为了描述 schema，而是为了决定“哪些 Wikidata 实体应该进入这条知识构建链路”。

它服务的是候选筛选阶段，而不是字段映射阶段。

白名单主要回答两个问题：

- 这个实体是否应该进入候选集
- 这个实体进入候选集后，应该先按哪个 `IncCore` 类别处理

### 8.2 种子白名单与 expanded 白名单

当前有两层配置：

- [wikidata_type_whitelist.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.yaml)
- [wikidata_type_whitelist.expanded.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/wikidata_type_whitelist.expanded.yaml)

它们的分工是：

- `wikidata_type_whitelist.yaml`
  - 人工维护的种子白名单
  - 表达“哪些大类是我们认可的”
- `wikidata_type_whitelist.expanded.yaml`
  - 在种子白名单基础上沿 `subclass of` 展开的可执行白名单
  - 用于真正跑全量过滤

### 8.3 代码调用链

`--type-whitelist` 参数的实际使用链路是：

```text
CLI --type-whitelist
-> cli.py
-> sharded_export.py / build / stream-import
-> WikiEntityCandidateFilter.for_domain(...)
-> WikiEntityCandidateFilter.all_industry(type_whitelist_path)
-> WikidataTypeWhitelist.load(whitelist_path, profile="all_industry")
```

这意味着：

- 不传 `--type-whitelist` 时，默认使用基础白名单
- 传入 `wikidata_type_whitelist.expanded.yaml` 时，过滤逻辑实际就会使用 expanded 白名单

### 8.4 当前过滤规则

当前筛选主要依赖：

- `P31`：instance of
- `P279`：subclass of
- 少量属性触发，如 `P176 manufacturer`

当前白名单/过滤逻辑的价值是：

- 减少城市、学校、体育组织等误入企业层
- 扩大真实企业、制造商、产品型号等的覆盖率
- 为后续 schema 路由提供初始类别

## 9. Schema 映射原则

当前 Wikidata 构图链路严格遵循以下原则：

1. 优先对齐 [IncCoreV2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCoreV2.schema) 中已定义字段，不额外发明新字段。
2. 能由 Wikidata 原始字段直接给出的属性，优先一对一映射。
3. 不能稳定从 Wikidata 直接获得的字段，当前允许留空，不用主观拼装替代。
4. 先保证“字段含义正确”，再追求“字段数量丰富”。

当前主映射入口：

- [IncIndustryWiki.routing.schema.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/IncIndustryWiki.routing.schema.yaml)
- [graph_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/graph_mapper.py)

## 10. 当前主要映射对象

### 10.1 Enterprise

当前 `Enterprise` 节点已稳定接入的字段包括：

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

当前已接入的主要关系包括：

- `belongsToIndustry`
- `region`
- `shareholder`
- `childOrganization`
- `manufacturer` 反向补边

### 10.2 ProductModel

当前 `ProductModel` 节点已稳定接入的字段包括：

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

当前已接入的主要关系包括：

- `manufacturer`
- `belongsToProduct`

### 10.3 Product

当前 `Product` 节点主要承担“标准产品/上位产品”角色。

当前能力：

- 可承接 `ProductModel.belongsToProduct`
- 可承接 `subclassOf`
- 可通过同批原始实体上下文补全 `name / description / alias / officialName / shortName / nameEn`

### 10.4 Industry / Region / Technology

这几类节点当前主要承担：

- 企业和产品的挂载目标
- 层级或归属关系目标
- 行业/区域主干语义支撑

`Region` 当前还承担了较多 stub 节点角色，但已经支持优先使用同批实体上下文补 `name` 和 `description`，降低图中只显示 `Qxxxx` 的情况。

## 11. DTO 设计

当前 DTO 的目标，不是简单承载某一层中间结果，而是让整条链路的输入、处理中间态、输出对象边界清晰。

DTO 集中定义在：

- [dto.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/dto.py)

当前 DTO 设计大致分三类：

### 11.1 原始候选 DTO

用于承接候选筛选后的实体基础上下文，通常包含：

- Wikidata `id`
- 主显示名
- 多语言 `labels`
- `aliases`
- `description`
- 初步归类后的 category

这层 DTO 的作用是：

- 让后续 schema 映射不用反复读原始 JSON
- 让节点构建时可以优先拿到“名字、英文名、别名、描述”等基础语义信息
- 为 stub 节点补充上下文

### 11.2 claim DTO

用于承接标准化后的单条 claim。作用是把 Wikidata 中各种底层 snak 表示方式统一掉，让路由逻辑只面向一个稳定结构工作。

### 11.3 图导入 DTO

用于承接最终图对象，典型上会组织：

- `entity_nodes`
- `concept_nodes`
- `event_nodes`
- `edges`
- 元数据和统计信息

这层 DTO 的价值是：

- 统一本地分片导出
- 统一 OpenSPG 导入
- 统一 MySQL 发布的数据来源

### 11.4 资讯融合 DTO

Graphiti 与 Neo4j v2 的资讯接入复用同一组融合 DTO：

- `V2SourceNodeDTO`
- `V2SourceEdgeDTO`
- `MappedV2NodeDTO`
- `CanonicalNodeIndexDTO`
- `FusionNodeDecisionDTO`
- `FusionRelationDecisionDTO`
- `FusionRunResultDTO`

这里的 `V2` 名称是历史命名，当前已经扩展为“外部动态子图接入 DTO”。Graphiti loader 会把 Graphiti Neo4j 中的节点和边先转成这组 DTO，再交给统一的 canonical matching 和链接式融合逻辑处理。

## 12. 图分片、落图与发库链路

### 12.1 图分片

当前全量或大样本运行，不会把所有结果聚到一个超大 JSON，而是通过 shard 输出。

典型文件：

- `graph_batch_000001.json`
- `coverage_report_000001.json`
- `manifest.json`

作用：

- 便于中间检查
- 便于阶段性导图
- 便于断点恢复
- 便于发布到 MySQL

### 12.2 OpenSPG 落图

当前图分片可以通过 `kag_adapter` 写入 OpenSPG / Neo4j。

这一步的核心目标是：

- 将 schema 对齐后的 Wikidata 结果转成正式图对象
- 让企业、产品、行业、区域等节点可在图数据库中查询和可视化

### 12.3 MySQL 发布

当前已经支持把图分片中的核心对象发布到远程 MySQL 表：

- `wiki_enterprise_cxd`
- `wiki_product_model_cxd`

MySQL 发布使用：

- [import_graph_batch_to_mysql.py](/Users/caixudong/Downloads/zhilian-robot/scripts/wiki_industry/import_graph_batch_to_mysql.py)

脚本当前已具备：

- 清表重发能力
- 按 shard 逐批导入
- 按目标表字段长度裁剪字符串
- 过滤非法枚举值

## 13. 当前实现状态

截至 2026-05-24，当前 Wikidata 链路的实现状态如下。

### 13.1 已实现

- 支持 Wikidata dump 远程流式读取
- 支持本地/远程输入
- 已形成类型白名单 + expanded 白名单体系
- 已形成候选筛选逻辑
- 已形成 claim 标准化逻辑
- 已形成按 `IncCoreV2.schema` 的主映射逻辑
- 已形成图分片导出能力
- 已形成 OpenSPG 导图链路
- 已形成远程 MySQL 发布链路
- 已对企业、产品型号字段做过一轮重点补齐
- 已支持用同批实体上下文补充 stub 节点可读性
- 已引入 `graphiti_news_pipeline` 作为根目录独立资讯收集子项目
- 已新增 Graphiti Neo4j 输出到大图融合 DTO 的 loader
- 已新增 Graphiti 资讯融合 runner 和 CLI，可把 Graphiti 动态实体链接到 Wikidata canonical 节点
- 已打通 Graphiti crawler run id 到 `Graphiti.add_episode(group_id=...)` 的批次透传
- 已将 Graphiti 资讯融合 CLI 收敛为一键编排入口，支持 API preflight、crawler 执行、按本批 group_id 融合、失败保护和报告输出

### 13.2 当前数据状态

最近一次基于新 schema 映射跑出的分片目录为：

- [all_industry_20260426_schema_v2](/Users/caixudong/Downloads/zhilian-robot/tmp/wiki_industry_full_export/all_industry_20260426_schema_v2)

当前已有阶段性成果：

- 已抽取并保留 29 个 shard
- 已基于这批 shard 重新落图
- 已将企业和产品型号发布到远程 MySQL 表

### 13.3 当前验证基线

当前 Wikidata pipeline 相关测试位于：

- [backend/tests/wiki_industry_candidate_filter_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_candidate_filter_test.py)
- [backend/tests/wiki_industry_claim_extractor_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_claim_extractor_test.py)
- [backend/tests/wiki_industry_claim_router_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_claim_router_test.py)
- [backend/tests/wiki_industry_graph_mapper_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_graph_mapper_test.py)
- [backend/tests/wiki_industry_sharded_export_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_sharded_export_test.py)
- [backend/tests/wiki_industry_cli_test.py](/Users/caixudong/Downloads/zhilian-robot/backend/tests/wiki_industry_cli_test.py)

## 14. 已知问题

当前这条链路已经可用，但还存在几个明确问题。

### 14.1 远程 Wikidata 流稳定性不足

当前远程 `.bz2` 流式读取在长时间全量运行时，仍可能出现：

- `EOFError: Compressed file ended before the end-of-stream marker was reached`
- `socket.timeout`

这意味着：

- 全量抽取仍可能中断
- 当前 resume 仍偏慢

### 14.2 企业与产品候选仍有噪声

即使有白名单，仍可能把部分“广义组织”“广义产品对象”带入 `Enterprise` 或 `ProductModel`。

后续仍需要：

- 持续补白名单
- 强化黑名单
- 强化 `P31 / P279` 门控

### 14.3 Product 层仍偏轻

当前 `Product` 仍更多承担“上位分类节点”角色，字段和层级关系还不够丰富。

### 14.4 概念层和事件层尚未在当前 Wikidata 链路中真正做强

当前主产物仍是：

- 实例层
- 关系层

概念层和事件层在这条 Wikidata 链路中还不是强产出。

## 15. 后续演进方向

当前最值得继续推进的方向有：

1. 继续补 `IncCoreV2.schema` 中剩余字段的稳定映射。
2. 提升 `Product` 层的标准产品能力。
3. 强化企业分类和产品分类的白名单质量。
4. 改善远程全量抽取的稳定性和恢复能力。
5. 逐步把概念层、事件层纳入统一产出。
6. 将当前链路与更通用的知识计算工作台、算子体系进一步接轨。

## 16. 开发前必读清单

每次开始修改 Wikidata 知识构建相关代码前，至少检查以下内容：

1. 本文档的“当前实现状态”和“已知问题”是否仍然成立。
2. 这次修改属于哪一层：
   - 数据源层
   - 候选筛选层
   - claim 标准化层
   - schema 路由层
   - 图对象构建层
   - 输出与发布层
3. 这次修改是否会影响：
   - 白名单配置
   - `IncCoreV2` 字段映射
   - DTO 结构
   - OpenSPG 导图
   - MySQL 表发布
4. 是否需要同步更新测试。
5. 是否需要同步更新运行命令、脚本或样例路径。

## 17. 开发后必更新清单

每次完成开发后，必须检查并更新本文档中的以下部分：

1. `更新时间`
2. “关键目录与代码责任”
3. “核心数据流”
4. “白名单体系如何服务过滤任务”
5. “Schema 映射原则”与“当前主要映射对象”
6. “DTO 设计”
7. “图分片、落图与发库链路”
8. “当前实现状态”
9. “已知问题”
10. “后续演进方向”

如果本次改动没有影响某一段，也应确认“不需要改”的原因，而不是跳过检查。

## 18. 相关文档

与本文档直接相关的现有文档包括：

- [2026-04-26-wiki-industry-pipeline-overview.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-04-26-wiki-industry-pipeline-overview.md)
- [2026-04-26-incorev2-wikidata-schema-mapping.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-04-26-incorev2-wikidata-schema-mapping.md)
- [2026-03-19-overall-architecture-and-implementation-proposal.md](/Users/caixudong/Downloads/zhilian-robot/docs/2026-03-19-overall-architecture-and-implementation-proposal.md)

后续如果本文档内容足够稳定，其他零散说明文档应尽量向本文档收敛，避免多份文档同时维护导致口径漂移。
