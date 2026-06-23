# 知识计算算子目录详细设计稿

**日期**: 2026-04-13

**关联文档**:
- [知识计算算子目录重定方案](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-04-13-knowledge-computing-operator-catalog.md)
- [知识计算算子清单（适配KAG规范+自定义业务框架版）](/Users/caixudong/Downloads/zhilian-robot/知识计算算子清单（适配KAG规范+自定义业务框架版）.docx)
- [知识计算算子清单（增加业务扩展）](/Users/caixudong/Downloads/zhilian-robot/知识计算算子清单（增加业务扩展）.docx)

## 1. 目的

在已经确定的 7 类“知识计算”顶层目录基础上，进一步给出：

- 具体算子
- 算子功能
- 第一版关键参数
- 实现方案
- 是否优先复用 `KAG`
- 是否需要自研

本稿的目标是为后续：

- 工作台目录重构
- 算子实现排期
- `KAG/OpenSPG` 结合方式落地

提供统一依据。

---

## 2. 设计原则

### 2.1 参数设计原则

本稿中的“参数”只写**第一版关键参数**，不等同于最终代码接口。参数说明遵循以下原则：

- 只列影响编排和实现边界的核心参数
- 优先列稳定业务参数，不展开底层模型/线程池等运行参数
- 优先列 DTO 级输入输出参数，不把所有内部字段都写成对外参数

### 2.2 实现方案分类

每个算子的实现方案统一标成以下几类：

- `复用 KAG`
  - 直接包装现有 `KAG` 组件即可
- `包装 KAG + 自研`
  - 底层复用 `KAG`，但要补业务 DTO、规则、路由或结果整理
- `复用 OpenSPG`
  - 主要依赖 `OpenSPG` 的 schema、图查询、图存储能力
- `自研`
  - `KAG/OpenSPG` 没有直接可复用能力，需要自己实现

### 2.3 实现优先级标记

- `P0`
  - 必须尽快落地，支撑工作台和基础链路
- `P1`
  - 第二批落地，支撑完整知识计算链
- `P2`
  - 后续扩展能力

---

## 3. 顶层目录与实现侧重点

| 顶层目录 | 当前是否已有基础实现 | 主要复用来源 | 主要新增来源 |
| --- | --- | --- | --- |
| 数据接入与加载 | 部分有 | 自研接入层、少量 `KAG reader` | 自研 |
| 数据预处理与结构化 | 部分有 | `KAG reader/splitter/extractor` | 包装层 |
| 知识抽取 | 部分有 | `KAG extractor` | 包装层、业务抽取规则 |
| 知识对齐与标准化 | 很少 | 少量现有 resolver 逻辑 | 自研 |
| 知识融合与图构建 | 已有较多 | `KAG mapping/writer`、`OpenSPG` | 自研融合逻辑 |
| 知识检索与召回 | 很少 | `OpenSPG` 查询、向量召回能力 | 自研检索编排 |
| 推理与决策生成 | 很少 | `OpenSPG` 图查询、规则引擎 | 自研 |

---

## 4. 数据接入与加载

### 4.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `pdf_source_ingest` | P0 | 接入本地文件、对象存储或上传得到的 PDF 源 | `source_uri`, `source_id`, `source_name`, `metadata`, `load_mode` | 自研。源接入本身不是 `KAG` 强项，建议统一封装到我们自己的 source adapter。 |
| `docx_source_ingest` | P1 | 接入 Word 文档并生成标准源对象 | `source_uri`, `source_id`, `source_name`, `metadata`, `load_mode` | 自研。后续正文解析可复用 `KAG`，但接入层应统一自建。 |
| `markdown_source_ingest` | P0 | 接入 Markdown 文档或文本片段 | `source_text/source_uri`, `source_id`, `title`, `metadata` | 自研。接入和抽取逻辑解耦，适合作为标准入口。 |
| `webpage_source_ingest` | P0 | 接入网页 URL 并记录抓取上下文 | `url`, `source_id`, `fetch_mode`, `headers`, `metadata` | 自研。网页抓取和重试逻辑应在我们自己的接入层。 |
| `rss_source_ingest` | P1 | 接入 RSS/Atom 订阅源并输出资讯记录 | `feed_url`, `source_id`, `poll_window`, `dedup_key` | 自研。`KAG` 不负责资讯源接入。 |
| `structured_table_source_ingest` | P0 | 接入 CSV/Excel/DB 行数据，转成标准结构化源 | `source_uri/table_name`, `pk_fields`, `field_mapping`, `load_mode` | 自研。后续可接 `KAG mapping`，但接入本身仍是我们自己的职责。 |
| `api_source_ingest` | P1 | 拉取第三方 API 数据源 | `endpoint`, `auth_config`, `pagination`, `retry_policy`, `field_mapping` | 自研。偏连接器能力，不建议塞进 `KAG`。 |

### 4.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `giks_batch_load` | P1 | 对接 GIKS 产业知识云，按主题批量加载数据 | `dataset_type`, `industry_code`, `region_code`, `version`, `sync_mode` | 自研。明确属于业务专属连接器。 |
| `industry_chain_topic_load` | P1 | 按产业链专题拉取企业、产品、技术、政策等专题数据 | `chain_code`, `region_scope`, `time_range`, `data_scopes` | 自研。 |
| `policy_corpus_load` | P1 | 按区域/时间/主题接入政策法规语料 | `region_code`, `policy_type`, `time_range`, `source_scope` | 自研。 |
| `innovation_asset_load` | P1 | 加载专利、论文、成果、软著等创新链数据 | `asset_type`, `ipc_code`, `owner_scope`, `time_range` | 自研。 |

---

## 5. 数据预处理与结构化

### 5.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `pdf_parse` | P0 | 把 PDF 源解析成标准 `DocumentDTO` | `parse_mode`, `page_range`, `ocr_enabled`, `layout_enabled` | 包装 `KAG PDFReader`。需要补 DTO 适配和异常处理。 |
| `docx_parse` | P1 | 解析 docx 文档正文与标题层级 | `parse_mode`, `include_comments`, `extract_tables` | 包装 `KAG DocxReader`。 |
| `html_extract` | P0 | 提取网页正文、标题、发布时间、链接结构 | `content_selector`, `clean_html`, `keep_links` | 包装 `KAG` 读入能力 + 自研正文提取。 |
| `markdown_normalize` | P0 | 统一 Markdown 标题层级、引用块、列表结构 | `normalize_heading`, `normalize_quote`, `strip_empty_blocks` | 包装 `KAG MarkDownReader` + 自研规范化。 |
| `document_clean` | P0 | 清理乱码、页眉页脚、冗余空白、无效噪声 | `clean_rules`, `dedup_paragraph`, `remove_boilerplate` | 自研。 `KAG` 无现成稳定清洗算子。 |
| `text_chunk_split` | P0 | 按长度、语义或标题切分 chunk | `split_mode`, `chunk_size`, `overlap`, `heading_aware` | 包装 `KAG LengthSplitter/SemanticSplitter/OutlineSplitter`。 |
| `outline_extract` | P1 | 提取章节和段落层级结构 | `max_depth`, `preserve_section_id` | 包装 `KAG OutlineExtractor`。 |
| `table_extract` | P1 | 从文档中抽取表格块及表格上下文 | `table_mode`, `keep_context`, `max_cells` | 包装 `KAG TableExtractor`。 |
| `format_normalize` | P1 | 统一日期、金额、编码、标点等文本格式 | `date_format`, `currency_format`, `normalize_punctuation` | 自研。 |

### 5.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `industry_document_parse` | P1 | 识别产业文档类型并恢复章节逻辑 | `doc_type_hint`, `section_schema`, `extract_appendix` | 包装通用解析算子 + 自研规则。 |
| `patent_fulltext_preprocess` | P1 | 专利全文拆成摘要、权利要求、说明书等模块 | `split_claims`, `split_description`, `drop_legal_notice` | 自研。专利文本结构有明显业务特性。 |
| `policy_text_normalize` | P1 | 标准化政策文本层级、文号、有效期等信息 | `extract_doc_no`, `extract_effective_date`, `clause_mode` | 自研。 |
| `announcement_normalize` | P1 | 清洗企业公告、招投标公告等文本 | `announcement_type`, `drop_risk_note`, `extract_subject` | 自研。 |
| `industry_code_normalize` | P1 | 标准化 IPC、ICD、行业代码、区域码等 | `code_system`, `version`, `strict_validate` | 自研。 |

---

## 6. 知识抽取

### 6.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `entity_extract` | P0 | 从 chunk 中抽实体候选 | `schema_ref`, `entity_types`, `llm_profile`, `confidence_threshold` | 包装 `KAG schema_constraint_extractor.named_entity_recognition`。 |
| `entity_standardize` | P0 | 对抽出的实体做标准化和别名归并 | `schema_ref`, `normalize_mode`, `official_name_enabled` | 包装 `KAG schema_constraint_extractor.named_entity_standardization`，并补业务别名策略。 |
| `relation_extract` | P0 | 从文本中抽关系候选 | `schema_ref`, `relation_types`, `llm_profile`, `confidence_threshold` | 包装 `KAG schema_constraint_extractor.relations_extraction`。 |
| `event_extract` | P0 | 从文本中抽事件候选 | `schema_ref`, `event_types`, `time_extraction`, `location_extraction` | 包装 `KAG schema_constraint_extractor.event_extraction`。 |
| `concept_seed_extract` | P1 | 从文本中抽概念候选或概念归属 | `concept_types`, `schema_ref`, `mode` | 包装 `KAG` 抽取结果 + 自研概念候选整理。 |
| `table_fact_extract` | P1 | 从表格 seed 中抽结构化事实 | `fact_schema`, `header_mode`, `merge_cells` | 包装 `KAG TableExtractor` 结果并二次整理。 |
| `summary_extract` | P2 | 提取 chunk 或文档摘要，用于后续检索与解释 | `summary_length`, `style`, `schema_hint` | 包装 `KAG SummaryExtractor`。 |

### 6.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `policy_factor_extract` | P1 | 抽取政策主体、对象、支持方向、申报条件、额度等要素 | `policy_schema`, `region_scope`, `support_type` | 包装通用抽取 + 自研政策要素模板。 |
| `patent_core_factor_extract` | P1 | 抽专利申请人、发明人、IPC、技术点、权利要求核心约束 | `patent_schema`, `extract_claim_core`, `extract_ipc` | 包装通用抽取 + 自研专利逻辑。 |
| `industry_chain_relation_extract` | P1 | 抽取上下游、供需、配套、替代等产业链关系 | `chain_schema`, `relation_set`, `industry_scope` | 自研为主，`KAG` 负责底层实体/关系抽取。 |
| `enterprise_capability_extract` | P1 | 抽企业科创能力、制造能力、平台能力等 | `capability_schema`, `dimension_set`, `score_hint` | 包装通用抽取 + 自研业务规则。 |
| `financing_event_extract` | P1 | 抽融资轮次、金额、投资方、用途等 | `event_schema`, `currency_norm`, `round_norm` | 包装 `event_extract` + 自研后处理。 |
| `talent_factor_extract` | P2 | 抽人物职称、教育背景、机构归属、成果能力 | `talent_schema`, `career_mode`, `title_norm` | 包装通用抽取 + 自研。 |
| `risk_event_extract` | P1 | 抽供应链风险、经营风险、合规风险事件 | `risk_schema`, `severity_mode`, `time_window` | 包装通用事件抽取 + 自研风险类型映射。 |

---

## 7. 知识对齐与标准化

### 7.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `entity_link` | P1 | 把实体候选链接到标准实体库 | `entity_type`, `match_keys`, `fuzzy_match`, `threshold` | 自研。`KAG` 无完整多源主实体归一框架。 |
| `entity_deduplicate` | P1 | 对同批抽取结果中的重复实体做归并 | `entity_type`, `match_fields`, `merge_strategy` | 自研。 |
| `attribute_normalize` | P1 | 统一日期、金额、代码、地址、别名等属性格式 | `attribute_set`, `normalize_rules`, `strict_mode` | 自研。 |
| `term_standardize` | P1 | 把术语、简称、别名归并到标准术语表 | `term_dict`, `normalize_mode`, `allow_new_term` | 自研。 |
| `time_normalize` | P1 | 统一事件时间、发布日期、有效期等时间字段 | `timezone`, `time_granularity`, `infer_partial_time` | 自研。 |
| `region_normalize` | P1 | 标准化省市区和行政编码 | `region_version`, `strict_region_match` | 自研。 |

### 7.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `enterprise_identity_resolve` | P0 | 企业名称、简称、信用代码、多源别名统一 | `match_priority`, `credit_code_first`, `alias_fields` | 自研，优先复用当前 `entity_resolver` 逻辑。 |
| `technology_term_align` | P1 | 技术术语对齐到标准技术体系 | `taxonomy_ref`, `alias_dict`, `embedding_match` | 自研。 |
| `industry_standard_align` | P1 | 把行业分类、产业链分类、IPC/ICD 等统一对齐 | `standard_system`, `version`, `fallback_map` | 自研。 |
| `policy_clause_align` | P1 | 将政策条款映射到统一条款层级结构 | `clause_schema`, `region_scope`, `policy_level` | 自研。 |

---

## 8. 知识融合与图构建

### 8.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `structured_entity_map` | P0 | 把结构化对象映射成图节点 | `schema_ref`, `type_name`, `field_mapping`, `upsert_key` | 包装 `KAG spg_type_mapping`。 |
| `structured_relation_map` | P0 | 把结构化关系映射成图边 | `schema_ref`, `relation_name`, `subject_key`, `object_key` | 包装 `KAG spo_mapping`。 |
| `concept_hierarchy_map` | P1 | 把概念层级映射为 `isA`/概念边 | `concept_type`, `path_separator`, `hypernym_predicate` | 包装 `KAG spg_type_mapping` 的概念能力。 |
| `subgraph_assemble` | P1 | 把实体、关系、事件、证据装成统一子图 | `graph_schema`, `merge_mode`, `keep_evidence` | 包装 `KAG` 子图拼装 + 自研 DTO 适配。 |
| `graph_import` | P0 | 把子图导入 OpenSPG | `project_id`, `namespace`, `write_mode`, `batch_size` | 包装 `KAG kg_writer` 或当前 `OpenSPGImporter`。 |

### 8.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `multi_source_enterprise_fusion` | P0 | 融合工商、专利、公告、舆情、投融资等多源企业数据 | `source_priority`, `merge_rules`, `entity_type` | 自研，优先复用现有融合链。 |
| `industry_chain_graph_fusion` | P1 | 融合产业链节点、上下游关系、产能和供需信息 | `chain_code`, `relation_priority`, `merge_rules` | 自研。 |
| `ipc_icd_dual_chain_fusion` | P1 | 将创新链与产业链做双链融合 | `ipc_taxonomy`, `icd_taxonomy`, `link_rules` | 自研。 |
| `knowledge_freshness_update` | P1 | 增量更新知识版本、归档旧值 | `version_key`, `update_window`, `archive_policy` | 自研。 |
| `knowledge_compliance_check` | P2 | 对敏感数据、涉密信息、合规风险做校验 | `compliance_policy`, `mask_mode`, `sensitivity_level` | 自研。 |

---

## 9. 知识检索与召回

### 9.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `vector_retrieve` | P1 | 向量语义检索 chunk、摘要或知识单元 | `query`, `top_k`, `similarity_threshold`, `index_name` | 包装现有向量检索能力，`KAG` 可部分复用，整体编排需自研。 |
| `graph_retrieve` | P1 | 按实体、关系、属性或路径做图谱精确检索 | `query_pattern`, `entity_type`, `relation_type`, `limit` | 复用 `OpenSPG` 图查询能力，包装成算子。 |
| `hybrid_retrieve` | P1 | 混合向量检索、图检索、关键词检索结果 | `query`, `top_k`, `weights`, `rerank_strategy` | 自研编排层，底层复用多种检索能力。 |
| `entity_profile_retrieve` | P1 | 检索某实体的全景信息 | `entity_id`, `profile_scope`, `limit` | 复用 `OpenSPG` 查询 + 自研结果组装。 |

### 9.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `industry_chain_topic_retrieve` | P1 | 定向召回产业链专题知识 | `chain_code`, `region_scope`, `topic_scope`, `top_k` | 自研，底层可复用图检索。 |
| `policy_match_retrieve` | P1 | 为企业或项目召回匹配政策 | `target_entity`, `region_code`, `industry_code`, `top_k` | 自研。 |
| `patent_similarity_retrieve` | P2 | 按技术语义和 IPC 召回相似专利 | `patent_id/query`, `ipc_scope`, `top_k`, `similarity_mode` | 自研，底层可复用向量检索。 |
| `investment_target_retrieve` | P2 | 按投融资主题召回候选企业/项目 | `industry_code`, `stage`, `region_scope`, `top_k` | 自研。 |
| `talent_match_retrieve` | P2 | 按产业和技术方向检索人才资源 | `industry_code`, `tech_term`, `region_scope`, `top_k` | 自研。 |

---

## 10. 推理与决策生成

### 10.1 通用基础算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `classification_reasoner` | P2 | 基于规则和知识图谱做分类判断 | `target_type`, `rule_set`, `confidence_threshold` | 自研。 |
| `multi_hop_reasoner` | P1 | 基于图谱做多跳事实推理 | `start_entity`, `hop_limit`, `constraint_set`, `top_k` | 复用 `OpenSPG` 图查询，推理编排自研。 |
| `rule_reasoner` | P1 | 执行业务规则和 if-then 逻辑 | `rule_set`, `input_bundle`, `strict_mode` | 自研。 |
| `numeric_reasoner` | P2 | 做统计、占比、增长率、对比等数值推理 | `metric_set`, `aggregation_mode`, `time_window` | 自研。 |
| `result_verifier` | P1 | 对推理结果做事实校验和来源验证 | `verification_scope`, `evidence_required`, `strict_mode` | 自研，底层复用检索与图查询。 |
| `answer_generator` | P2 | 基于检索/推理结果生成结构化或自然语言输出 | `output_format`, `style`, `with_evidence` | 自研。 |

### 10.2 业务扩展算子

| 算子名称 | 优先级 | 功能 | 第一版关键参数 | 实现方案 |
| --- | --- | --- | --- | --- |
| `enterprise_classification_reasoner` | P1 | 做企业行业、资质、科创等级、风险等级分类 | `classification_schema`, `rule_set`, `evidence_required` | 自研。 |
| `policy_enterprise_match_reasoner` | P1 | 推理企业和政策的匹配关系 | `enterprise_id`, `policy_scope`, `match_rules`, `top_k` | 自研。 |
| `industry_chain_path_reasoner` | P1 | 推理产业链上下游链路和薄弱环节 | `chain_code`, `start_node`, `path_constraint`, `hop_limit` | 自研。 |
| `supply_chain_risk_reasoner` | P2 | 推理供应链风险传播和影响 | `risk_event`, `propagation_rules`, `time_window` | 自研。 |
| `innovation_capability_reasoner` | P2 | 推理企业科创能力和技术成熟度 | `enterprise_id`, `capability_dimensions`, `score_rules` | 自研。 |
| `report_generator` | P2 | 自动生成产业研判/企业分析报告 | `report_type`, `template_id`, `evidence_scope` | 自研。 |

---

## 11. 哪些优先复用 KAG

优先直接包装 `KAG` 的算子如下：

### 11.1 直接可包装

- `pdf_parse`
- `docx_parse`
- `markdown_normalize`
- `text_chunk_split`
- `outline_extract`
- `table_extract`
- `entity_extract`
- `entity_standardize`
- `relation_extract`
- `event_extract`
- `structured_entity_map`
- `structured_relation_map`
- `concept_hierarchy_map`
- `graph_import`

### 11.2 需要“包装 KAG + 自研”的

- `html_extract`
- `concept_seed_extract`
- `table_fact_extract`
- `subgraph_assemble`

这些能力底层可借 `KAG`，但 DTO、业务 schema 和执行编排必须由我们自己补。

---

## 12. 哪些必须自研

以下类别不建议试图塞进 `KAG` 本体，而应由我们自己的知识计算算子层负责：

- 所有 source ingest 连接器
- 实体归一和多源对齐
- 产业链/政策/专利/人才等业务专属抽取
- 多源融合
- 专题检索
- 业务推理
- 报告生成
- 工作台、registry、pipeline 编排、试跑、保存

这些是业务平台能力，不是 `KAG` 通用组件能力。

---

## 13. 首期建议实现批次

### 第一批：P0 基础链

- `pdf_source_ingest`
- `markdown_source_ingest`
- `structured_table_source_ingest`
- `pdf_parse`
- `markdown_normalize`
- `document_clean`
- `text_chunk_split`
- `entity_extract`
- `entity_standardize`
- `relation_extract`
- `event_extract`
- `structured_entity_map`
- `structured_relation_map`
- `graph_import`
- `enterprise_identity_resolve`
- `multi_source_enterprise_fusion`

目标：

- 跑通“原始数据 -> 预处理 -> 抽取 -> 对齐 -> 融合 -> 落图”的最小闭环。

### 第二批：P1 业务增强

- `policy_factor_extract`
- `patent_core_factor_extract`
- `industry_chain_relation_extract`
- `financing_event_extract`
- `industry_document_parse`
- `policy_text_normalize`
- `industry_standard_align`
- `industry_chain_graph_fusion`
- `knowledge_freshness_update`
- `vector_retrieve`
- `graph_retrieve`
- `hybrid_retrieve`
- `multi_hop_reasoner`
- `policy_enterprise_match_reasoner`

目标：

- 支撑产业研究分析的关键主题场景。

---

## 14. 落地建议

### 14.1 当前仓库内的建议组织方式

建议继续沿用当前仓库组织，但逐步把：

- [knowledge_extraction_operators](/Users/caixudong/Downloads/zhilian-robot/backend/app/knowledge_extraction_operators)

演进成更明确的“知识计算算子层”。短期内不强制改目录路径，避免一次性迁移过大。

### 14.2 与 KAG/OpenSPG 的分工

- `KAG`
  - 通用 builder component
- `OpenSPG`
  - schema、图谱存储、图谱查询
- 我们自己的算子层
  - DTO、registry、runtime、业务扩展算子、工作台、pipeline 编排

### 14.3 核心实现原则

1. 能包装 `KAG` 的，不重复造轮子
2. 业务逻辑不回写进 `KAG` 本体
3. 工作台始终面向“知识计算目录”而不是“内部实现分层”
4. 实现优先级始终以 P0/P1 为主，不追求一次性铺满全目录

---

## 15. 最终建议

最终建议可以收敛成一句话：

**后续实现时，先按 7 类知识计算目录来组织算子，用“通用基础 / 业务扩展”作为第二维，并优先包装 `KAG` 的通用组件；凡是涉及实体归一、多源融合、产业专题检索和业务推理的部分，统一放在我们自己的知识计算算子层实现。**
