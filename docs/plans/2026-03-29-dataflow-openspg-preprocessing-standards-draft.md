# 面向 OpenSPG/KAG 的前置处理层标准与草案

## 1. 文档范围

本文档给出前置处理层的详细标准和实现草案，目标是把总体设计进一步收敛成可执行的工程规范。

覆盖内容：

- 统一 DTO 标准
- 算子标准定义
- 算子注册与发现标准
- 三类输入的算子清单
- 算子输入输出约束
- agent 可调用协议草案
- 首期实现建议

## 2. 命名与分层标准

建议新增目录：

`backend/app/preprocess_pipeline/`

建议结构：

```text
backend/app/preprocess_pipeline/
  dto/
  operators/
  registry/
  pipelines/
  router/
  stats/
  examples/
```

说明：

- `dto/`：定义统一输入输出对象
- `operators/`：定义各类处理算子
- `registry/`：提供算子注册和发现能力
- `pipelines/`：定义静态编排模板
- `router/`：根据输入类型和文档类型做路径选择
- `stats/`：运行统计与追踪
- `examples/`：示例输入输出

## 3. DTO 标准

## 3.1 PreprocessRecord

统一输入对象。

字段建议：

```json
{
  "source_system": "eastmoney_report",
  "source_type": "report",
  "record_id": "rep_001",
  "record_type": "document",
  "content_type": "pdf",
  "title": "机器人行业深度报告",
  "content": "",
  "summary": "",
  "file_path": "/data/report.pdf",
  "url": "",
  "publish_time": "2026-03-20T10:00:00",
  "source_name": "东方财富",
  "metadata": {}
}
```

约束：

- `record_id` 必填
- `source_type` 必填
- `record_type` 必填
- `content_type` 必填
- `content / file_path / url` 至少一项存在

## 3.2 DocumentRecord

文档层中间对象。

字段建议：

```json
{
  "document_id": "doc_001",
  "source_record_id": "rep_001",
  "doc_category": "research_report",
  "title": "机器人行业深度报告",
  "raw_text": "",
  "cleaned_text": "",
  "markdown_path": "",
  "publish_time": "2026-03-20T10:00:00",
  "source_name": "东方财富",
  "metadata": {}
}
```

## 3.3 ChunkRecord

文档切块对象。

字段建议：

```json
{
  "chunk_id": "doc_001#3",
  "document_id": "doc_001",
  "chunk_index": 3,
  "content": "公司完成B轮融资，投资方为某产业基金。",
  "section_title": "融资事件",
  "page_no": 12,
  "chunk_type": "text",
  "metadata": {}
}
```

## 3.4 SeedRecord

统一种子对象父类。

通用字段：

```json
{
  "seed_id": "seed_001",
  "seed_type": "event",
  "source_document_ids": ["doc_001"],
  "source_chunk_ids": ["doc_001#3"],
  "confidence": 0.82,
  "metadata": {}
}
```

### EntitySeed

```json
{
  "seed_type": "entity",
  "entity_type": "Company",
  "name": "上海某某机器人科技有限公司",
  "aliases": ["某某机器人"],
  "properties": {}
}
```

### RelationSeed

```json
{
  "seed_type": "relation",
  "subject_name": "上海某某机器人科技有限公司",
  "predicate": "hasMainProduct",
  "object_name": "工业机器人控制器",
  "properties": {}
}
```

### EventSeed

```json
{
  "seed_type": "event",
  "event_type": "CompanyFinancingEvent",
  "name": "上海某某机器人科技有限公司完成B轮融资",
  "subject_name": "上海某某机器人科技有限公司",
  "object_name": "某产业基金",
  "event_time": "2026-03-20",
  "location": "上海",
  "properties": {
    "financing_round": "B轮",
    "financing_amount": 500000000
  }
}
```

### ConceptSeed

```json
{
  "seed_type": "concept",
  "concept_type": "IndustrySector",
  "name": "高端装备",
  "parent_name": "先进制造业",
  "binding_target": "上海某某机器人科技有限公司"
}
```

## 4. 算子标准定义

所有算子都必须满足下面的标准。

## 4.1 基本元数据

每个算子必须声明：

```python
{
  "name": "ChunkToEventSeedOperator",
  "category": "seed_builder",
  "version": "v1",
  "description": "从清洗后的chunk中提取事件候选seed",
  "input_types": ["ChunkRecord"],
  "output_types": ["EventSeed"],
  "required_fields": ["content"],
  "optional_fields": ["section_title", "page_no"],
  "applicable_source_types": ["news", "report"],
  "applicable_doc_categories": ["news", "research_report", "policy_document"]
}
```

## 4.2 运行接口

建议统一接口：

```python
class PreprocessOperatorABC:
    def run(self, records, **kwargs):
        ...
```

要求：

- 输入和输出必须是明确 DTO 列表
- 不允许直接把任意 dict 当通用接口
- 算子必须返回：
  - `records`
  - `stats`

## 4.3 运行统计

每个算子必须记录：

- `input_count`
- `output_count`
- `dropped_count`
- `error_count`
- `sample_outputs`
- `duration_ms`

## 4.4 错误处理

统一策略：

- 单条数据错误不应导致整批失败
- 必须把错误写入 stats
- 必须保留 `failed_record_ids`

## 5. 算子分类标准

前置处理算子统一按 6 类组织。

## 5.1 Adapter Operators

作用：

- 把不同来源数据适配为 `PreprocessRecord`

首期算子：

- `NewsAdapterOperator`
- `ReportAdapterOperator`
- `FactTableAdapterOperator`

## 5.2 Normalize Operators

作用：

- 标准化标题、来源、别名、时间、路径、编码

首期算子：

- `DocumentNormalizeOperator`
- `EntityAliasNormalizeOperator`

## 5.3 Clean & Filter Operators

作用：

- 清洗文本
- 去重
- 质量过滤

优先复用 DataFlow 思想：

- `TextNormalizationOperator`
- `ExactDeduplicateOperator`
- `MinHashDeduplicateOperator`
- `SimHashDeduplicateOperator`
- `QualityFilterOperator`
- `IndustryNoiseFilter`

## 5.4 Structuring Operators

作用：

- 切块
- 章节识别
- 表格识别

首期算子：

- `ChunkingOperator`
- `OutlineStructuringOperator`
- `TableStructuringOperator`

## 5.5 Enrichment Operators

作用：

- 文档分类
- 企业分类候选
- 行业概念候选
- 事件影响候选

首期算子：

- `DocumentClassificationOperator`
- `CompanyCategoryPreBinder`
- `IndustrySectorPreBinder`
- `EventImpactPreClassifier`

## 5.6 Seed Builder Operators

作用：

- 构造后续知识层统一可消费的种子对象

首期算子：

- `ChunkToEntitySeedOperator`
- `ChunkToEventSeedOperator`
- `StructuredRowToSeedOperator`
- `DocumentToSourceRecordConverter`

## 6. 三类输入的数据处理草案

## 6.1 常识数据

### 目标

- 保持结构化特征
- 先做规范化和别名清理
- 再生成统一 seed

### 推荐算子链

```text
FactTableAdapterOperator
-> DocumentNormalizeOperator
-> ExactDeduplicateOperator
-> EntityAliasNormalizeOperator
-> StructuredRowToSeedOperator
```

### 输出

- `EntitySeed`
- `RelationSeed`
- `ConceptSeed`

### 下游

- 进入 `IncCore fusion pipeline`
- 或进入 `KAG structured mapping`

## 6.2 研报数据

### 目标

- 完成 PDF / 网页转换
- 清洗文档噪声
- 保留大纲与表格信息
- 构造 entity/event seed

### 推荐算子链

```text
ReportAdapterOperator
-> FileToMarkdownOperator
-> TextCleaningOperator
-> OutlineStructuringOperator
-> TableStructuringOperator
-> ChunkingOperator
-> IndustrySectorPreBinder
-> ChunkToEntitySeedOperator
-> ChunkToEventSeedOperator
```

### 输出

- `DocumentRecord`
- `ChunkRecord`
- `EntitySeed`
- `EventSeed`
- `ConceptSeed`

### 下游

- `DocumentRecord / ChunkRecord` 给 `KAG`
- `SeedRecord` 给 `IncCore fusion pipeline`

## 6.3 资讯数据

### 目标

- 去重
- 标准化
- 事件候选前移
- 影响概念预分类

### 推荐算子链

```text
NewsAdapterOperator
-> DocumentNormalizeOperator
-> MinHashDeduplicateOperator
-> QualityFilterOperator
-> ChunkingOperator
-> EventImpactPreClassifier
-> ChunkToEventSeedOperator
```

### 输出

- `DocumentRecord`
- `ChunkRecord`
- `EventSeed`
- `ConceptSeed`

### 下游

- `IncCore event_resolver`

## 7. 可复用 DataFlow 能力与新增算子判断

## 7.1 建议复用的能力

应当优先借用 `DataFlow` 思路或逻辑的模块：

- 文档接入与 Markdown 转换
- 文本切块
- 去重过滤
- 文本规范化
- Prompt 驱动改写与清洗

## 7.2 必须自研的能力

必须新增的产业场景算子：

- `EntityAliasNormalizeOperator`
- `DocumentClassificationOperator`
- `QualityFilterOperator`
- `IndustryNoiseFilter`
- `OutlineStructuringOperator`
- `TableStructuringOperator`
- `ChunkToEntitySeedOperator`
- `ChunkToEventSeedOperator`
- `StructuredRowToSeedOperator`
- `CompanyCategoryPreBinder`
- `IndustrySectorPreBinder`
- `EventImpactPreClassifier`

原因：

- 这些能力都直接绑定产业知识图谱场景
- 通用 `DataFlow` 算子没有业务语义
- 后续还要与 `IncCore` 的概念层、事件层保持一致

## 8. Agent 调用标准草案

## 8.1 算子注册清单接口

建议统一输出：

```json
{
  "name": "ChunkToEventSeedOperator",
  "category": "seed_builder",
  "desc": "从chunk中提取事件seed",
  "inputs": ["ChunkRecord"],
  "outputs": ["EventSeed"],
  "params": {
    "event_types": "list[str]",
    "strict_mode": "bool"
  },
  "routing_rules": {
    "source_type": ["news", "report"]
  }
}
```

## 8.2 Agent 选算子逻辑

agent 的选择流程建议为：

1. 判断输入对象类型
2. 判断 `source_type`
3. 判断 `doc_category`
4. 查询适配算子
5. 构造候选 pipeline
6. 读取算子 stats，决定是否重试或换路由

## 8.3 Agent 可用的三类能力

### 静态编排

按固定模板运行：

- `news_preprocess_pipeline`
- `report_preprocess_pipeline`
- `fact_preprocess_pipeline`

### 动态删减

例如：

- 无 PDF 则跳过 `FileToMarkdownOperator`
- 短资讯则跳过 `ChunkingOperator`

### 动态增强

例如：

- 研报表格密集，则追加 `TableStructuringOperator`
- 企业文本密集，则追加 `CompanyCategoryPreBinder`

## 9. 首期实现建议

### 9.1 目录草案

```text
backend/app/preprocess_pipeline/
  dto/
    preprocess_record.py
    document_record.py
    chunk_record.py
    seed_record.py
  operators/
    adapter/
    normalize/
    clean/
    structuring/
    enrichment/
    seed_builder/
  registry/
    operator_registry.py
  router/
    pipeline_router.py
  pipelines/
    news_preprocess_pipeline.py
    report_preprocess_pipeline.py
    fact_preprocess_pipeline.py
```

### 9.2 首批最小实现

第一期建议只先实现：

- `NewsAdapterOperator`
- `ReportAdapterOperator`
- `FactTableAdapterOperator`
- `DocumentNormalizeOperator`
- `MinHashDeduplicateOperator`
- `ChunkingOperator`
- `ChunkToEventSeedOperator`
- `StructuredRowToSeedOperator`
- `DocumentClassificationOperator`
- `CompanyCategoryPreBinder`

### 9.3 第一阶段验收标准

满足以下条件即可视为第一阶段完成：

1. 三类输入都能进入统一前置层
2. 每条前置链都能输出标准 DTO
3. 算子可以注册和发现
4. 算子运行结果带统计信息
5. 下游至少能喂给：
   - `KAG`
   - `IncCore fusion pipeline`

## 10. 结论

这套标准与草案的核心目标是：

**把原始输入治理能力从“脚本逻辑”提升为“标准算子系统”。**

这样做的直接收益是：

- 前置处理过程更清晰
- 数据链路更统一
- 可持续扩展
- 后续 agent 更容易接入

推荐的工程方向是：

1. 用统一 DTO 把输入与输出标准化
2. 用统一算子元数据把处理动作标准化
3. 用统一 routing 规则把 pipeline 编排标准化
4. 用统一 stats 机制把 agent 反馈闭环标准化
