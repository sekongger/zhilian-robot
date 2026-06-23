# 知识抽取算子目录设计表

## 1. 目标

这份目录表的目的不是把 `DataFlow` 原样搬到知识抽取链里，而是把它的“算子化”思想提炼出来，用于我们自己的知识抽取业务。

这里的“知识抽取算子”覆盖四层：

1. 文档理解与切块
2. 实体/关系/事件抽取
3. 结构化数据映射建图
4. 实体融合、概念挂载、事件归一与统一落图

设计原则：

- 每个算子只承担一个明确职责
- 输入输出使用稳定 DTO，而不是随意传 dict
- 尽量复用 KAG 已有组件
- KAG 没覆盖的融合逻辑，保留自研算子
- 后续每个算子都要能被 agent 发现、选择、调用

---

## 2. 总体判断

- `KAG` 当前已经是“半成型算子体系”：
  - 有统一组件基类
  - 有 `input_types / output_types`
  - 有 `invoke / ainvoke`
  - 有 chain 组合
  - 有 reader / splitter / extractor / mapping / writer 分层
- 但它还不是“DataFlow 风格 agent 算子平台”：
  - 缺少业务可读的算子目录元数据
  - 缺少统一 DTO 规范
  - 缺少路由条件、成本描述、观测指标
  - 缺少给 agent 用的稳定调用协议

因此，最合理的做法不是重写 KAG，而是：

- 把 KAG 现有组件包装成标准知识抽取算子
- 把我们自己的 resolver / mapper / builder 也纳入同一算子目录
- 统一成可注册、可路由、可监控、可被 agent 调用的体系

---

## 3. 知识抽取算子目录设计表

### 3.1 文档理解类算子

| 算子名 | 输入 | 输出 | 对应 KAG 实现 | 是否需新增包装 | 是否可被 agent 调用 |
|---|---|---|---|---|---|
| `DocumentReaderOperator` | `DocumentSourceDTO(file_path/url/content)` | `DocumentDTO` | `PDFReader` / `DocxReader` / `MarkDownReader` / `TXTReader` / `MixReader` | 是。需要统一输入源协议和文档元数据 | 是，补齐元数据后可直接调用 |
| `DocumentChunkSplitOperator` | `DocumentDTO` 或 `ChunkDTO` | `ChunkDTO[]` | `LengthSplitter` / `SemanticSplitter` / `OutlineSplitter` / `PatternSplitter` | 是。需要统一 chunk schema 和分块策略参数 | 是 |
| `OutlineExtractOperator` | `ChunkDTO` 或 `DocumentDTO` | `OutlineDTO` / enriched `ChunkDTO[]` | `OutlineExtractor` | 是。需要把输出转为统一章节结构 DTO | 是 |
| `TableExtractOperator` | `DocumentDTO` / `ChunkDTO` | `TableSeedDTO[]` | `TableExtractor` | 是。需要把表格结果转为业务可用 seed | 是 |
| `ChunkPassThroughOperator` | `ChunkDTO` | `ChunkDTO` 或 `ChunkGraphSeedDTO` | `ChunkExtractor` | 是。需要弱化 KAG 内部 graph 形式，转成统一 DTO | 是 |
| `SummaryExtractOperator` | `ChunkDTO` / `DocumentDTO` | `SummaryDTO` | `SummaryExtractor` | 是。需要把摘要挂到文档上下文而不是直接图输出 | 是 |

### 3.2 核心知识抽取类算子

| 算子名 | 输入 | 输出 | 对应 KAG 实现 | 是否需新增包装 | 是否可被 agent 调用 |
|---|---|---|---|---|---|
| `EntityExtractOperator` | `ChunkDTO` | `EntitySeedDTO[]` | `SchemaConstraintExtractor.named_entity_recognition()` / `SchemaFreeExtractor` | 是。建议拆成独立 NER 算子，不直接输出 `SubGraph` | 是 |
| `EntityStandardizeOperator` | `ChunkDTO + EntitySeedDTO[]` | standardized `EntitySeedDTO[]` | `SchemaConstraintExtractor.named_entity_standardization()` | 是。需要统一别名、官方名、标准名字段 | 是 |
| `RelationExtractOperator` | `ChunkDTO + EntitySeedDTO[]` | `RelationSeedDTO[]` | `SchemaConstraintExtractor.relations_extraction()` / `SchemaFreeExtractor` | 是。需要输出统一关系 seed，而不是直接边 | 是 |
| `EventExtractOperator` | `ChunkDTO` | `EventSeedDTO[]` | `SchemaConstraintExtractor.event_extraction()` / `SchemaFreeExtractor` | 是。需要统一事件 schema 和证据字段 | 是 |
| `SubGraphAssembleOperator` | `ChunkDTO + EntitySeedDTO[] + RelationSeedDTO[] + EventSeedDTO[]` | `GraphSeedDTO` | `SchemaConstraintExtractor.assemble_subgraph()` | 是。建议保留为内部图组装算子 | 是，但更适合内部编排调用 |
| `GraphPostprocessOperator` | `GraphSeedDTO` | normalized `GraphSeedDTO` | `SchemaConstraintExtractor.postprocess_graph()` | 是。需要把节点去重、属性合并逻辑显式化 | 是 |
| `SchemaFreeKnowledgeExtractOperator` | `ChunkDTO` | `EntitySeedDTO[] + RelationSeedDTO[] + EventSeedDTO[]` | `SchemaFreeExtractor` | 是。需要把当前黑盒式输出拆成标准 seed 输出 | 是 |
| `SchemaConstraintKnowledgeExtractOperator` | `ChunkDTO + SchemaRef` | `EntitySeedDTO[] + RelationSeedDTO[] + EventSeedDTO[]` | `SchemaConstraintExtractor` | 是。建议保留为组合算子，内部调用 NER/STD/REL/EVT 四个细算子 | 是 |

### 3.3 结构化知识映射类算子

| 算子名 | 输入 | 输出 | 对应 KAG 实现 | 是否需新增包装 | 是否可被 agent 调用 |
|---|---|---|---|---|---|
| `StructuredEntityMapOperator` | `StructuredRowDTO` | `GraphSeedDTO` | `SPGTypeMapping` | 是。需要把输入统一到 `StructuredRowDTO`，并补业务字段映射声明 | 是 |
| `StructuredRelationMapOperator` | `StructuredRelationRowDTO` | `GraphSeedDTO` | `SPOMapping` / `RelationMapping` | 是。需要统一关系表 schema 和属性字段 | 是 |
| `ConceptHierarchyMapOperator` | `ConceptRowDTO` | `GraphSeedDTO` | `SPGTypeMapping.hypernym_predicate()` | 是。建议从 `SPGTypeMapping` 中独立出概念层导入语义 | 是 |
| `StructuredGraphWriteOperator` | `GraphSeedDTO` | `GraphImportResultDTO` | `KGWriter` | 是。需要统一导入回执和错误处理 DTO | 是 |

### 3.4 融合与统一大图类算子

| 算子名 | 输入 | 输出 | 对应 KAG 实现 | 是否需新增包装 | 是否可被 agent 调用 |
|---|---|---|---|---|---|
| `SourceRecordMapOperator` | `SourceRecordDTO[]` | `EntitySeedDTO[] + RelationSeedDTO[] + EventSeedDTO[] + ConceptSeedDTO[]` | 无直接对应 | 否，已有自研 `SourceMapper`，但需补 operator 封装 | 是 |
| `EventSeedEnrichOperator` | `EventSeedDTO[]` | enriched `EventSeedDTO[]` | 无直接对应 | 否，已有自研 `EventMapper`，但需补 operator 封装 | 是 |
| `EntityResolveOperator` | `EntitySeedDTO[]` | `CanonicalEntityDTO[]` | 无直接对应 | 否，已有自研 `EntityResolver`，但需补 operator 封装 | 是 |
| `EventResolveOperator` | `EventSeedDTO[] + CanonicalEntityDTO[]` | `CanonicalEventDTO[]` | 无直接对应 | 否，已有自研 `EventResolver`，但需补 operator 封装 | 是 |
| `ConceptBindOperator` | `CanonicalEntityDTO[] + CanonicalEventDTO[] + ConceptSeedDTO[]` | concept-enriched entities/events | 无直接对应 | 否，已有自研 `ConceptBatchBuilder` 及相关映射逻辑，但需补 operator 封装 | 是 |
| `EntityGraphBuildOperator` | `CanonicalEntityDTO[]` | `GraphNodeUpsertDTO[] + GraphEdgeUpsertDTO[]` | 无直接对应 | 否，已有自研 `EntityBatchBuilder`，但需补 operator 封装 | 是 |
| `EventGraphBuildOperator` | `CanonicalEventDTO[]` | `GraphNodeUpsertDTO[] + GraphEdgeUpsertDTO[]` | 无直接对应 | 否，已有自研 `EventBatchBuilder`，但需补 operator 封装 | 是 |
| `EvidenceGraphBuildOperator` | `DocumentDTO[] + ChunkDTO[] + CanonicalEventDTO[]` | evidence graph DTOs | 无直接对应 | 否，已有自研 `EvidenceBatchBuilder`，但需补 operator 封装 | 是 |
| `FusionGraphImportOperator` | `GraphImportBatchDTO` | `GraphImportResultDTO` | 无直接对应 KAG；功能上近似 `KGWriter` | 否，已有自研 `OpenSPGImporter`，但需补 operator 封装 | 是 |

### 3.5 建议新增的业务增强算子

| 算子名 | 输入 | 输出 | 对应 KAG 实现 | 是否需新增包装 | 是否可被 agent 调用 |
|---|---|---|---|---|---|
| `IndustryEntityExtractOperator` | `ChunkDTO` | `EntitySeedDTO[]` | 可复用 `SchemaConstraintExtractor` 的 NER 能力 | 是，需补产业实体类型白名单和 prompt 配置 | 是 |
| `IndustryRelationExtractOperator` | `ChunkDTO + EntitySeedDTO[]` | `RelationSeedDTO[]` | 可复用 `relations_extraction()` | 是，需补产业关系集合 | 是 |
| `IndustryEventExtractOperator` | `ChunkDTO` | `EventSeedDTO[]` | 可复用 `event_extraction()` | 是，需补产业事件 schema | 是 |
| `CompanyCategoryBindOperator` | `CanonicalEntityDTO[]` | entities with company category concepts | 无直接对应 | 是，建议从现有企业分类逻辑独立成算子 | 是 |
| `IndustrySectorBindOperator` | `CanonicalEntityDTO[] + CanonicalEventDTO[]` | concept-enriched entities/events | 无直接对应 | 是 | 是 |
| `EventImpactClassifyOperator` | `CanonicalEventDTO[]` | events with impact concepts | 无直接对应 | 是 | 是 |

---

## 4. 首期建议优先落地的算子集合

如果只做第一期，我建议优先做下面 10 个，它们足够支撑“资讯 + 研报 + 常识数据”的统一知识抽取：

1. `DocumentReaderOperator`
2. `DocumentChunkSplitOperator`
3. `EntityExtractOperator`
4. `EntityStandardizeOperator`
5. `RelationExtractOperator`
6. `EventExtractOperator`
7. `StructuredEntityMapOperator`
8. `StructuredRelationMapOperator`
9. `EntityResolveOperator`
10. `ConceptBindOperator`

理由：

- 文档型输入和结构化输入都覆盖到了
- KAG 现成能力复用率高
- 自研部分只集中在融合和概念层
- 后续最容易被 agent 编排

---

## 5. 面向 agent 调用，还需要补哪些标准

即使一个组件已经“技术上可调用”，也不能直接认为它已经适合 agent 使用。  
要真正支持类似 `DataFlow-Agent` 的调用，还需要补这些元数据：

### 5.1 算子注册元数据

每个算子都要补：

- `operator_name`
- `category`
- `description`
- `input_types`
- `output_types`
- `required_fields`
- `optional_fields`
- `applicable_sources`
- `cost_hint`
- `latency_hint`
- `deterministic`

### 5.2 统一 DTO

建议统一到下面这几类：

- `DocumentSourceDTO`
- `DocumentDTO`
- `ChunkDTO`
- `StructuredRowDTO`
- `EntitySeedDTO`
- `RelationSeedDTO`
- `EventSeedDTO`
- `ConceptSeedDTO`
- `CanonicalEntityDTO`
- `CanonicalEventDTO`
- `GraphSeedDTO`
- `GraphImportBatchDTO`
- `GraphImportResultDTO`

### 5.3 路由条件

agent 选择算子时要知道：

- 适用于 `news / report / fact_table`
- 适用于 `pdf / markdown / text / structured_row`
- 是否依赖 `schema`
- 是否依赖 `llm`
- 是否会直接写图

### 5.4 可观测性

每个算子执行后要输出：

- 输入数
- 输出数
- 跳过数
- 失败数
- 代表样本
- 质量指标

---

## 6. 最终建议

最合理的实现方式不是“新做一套 DataFlow”，而是：

1. 把 KAG 现有的 reader / splitter / extractor / mapping / writer 包装成标准知识算子
2. 把我们自己的 resolver / builder / importer 也纳入同一个算子目录
3. 提供统一 operator registry
4. 让 agent 调的是“知识抽取算子目录”，不是直接调底层类

一句话总结：

`KAG` 已经很接近“知识抽取算子库”，我们需要补的不是核心能力，而是统一封装、业务元数据和 agent 调用协议。

---

## 7. 相关实现参考

- KAG 组件基类：`modules/kag/kag/interface/builder/base.py`
- KAG builder chain：`modules/kag/kag/builder/default_chain.py`
- KAG schema 约束抽取器：`modules/kag/kag/builder/component/extractor/schema_constraint_extractor.py`
- KAG schema-free 抽取器：`modules/kag/kag/builder/component/extractor/schema_free_extractor.py`
- KAG 表格抽取：`modules/kag/kag/builder/component/extractor/table_extractor.py`
- KAG 结构化实体映射：`modules/kag/kag/builder/component/mapping/spg_type_mapping.py`
- KAG 结构化关系映射：`modules/kag/kag/builder/component/mapping/spo_mapping.py`
- KAG 写图组件：`modules/kag/kag/builder/component/writer/kg_writer.py`
- 我们当前融合主链：`backend/app/incore_fusion_pipeline/runners/fusion_pipeline_runner.py`
- 我们当前资讯抽取：`backend/app/news_pipeline/extractor.py`

