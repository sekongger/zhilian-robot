# Wikipedia / Wikidata 产业网链基础图谱 MVP 实现计划

## 1. 目标

基于 [2026-04-20-wikipedia-industry-chain-base-kg-design.md](/Users/caixudong/Downloads/zhilian-robot/docs/plans/2026-04-20-wikipedia-industry-chain-base-kg-design.md) 的方案，第一期实现一个可运行的 Wikidata 机器人产业链基础图谱构建 MVP。

第一期只做：

1. Wikidata JSON 小样本 / limit 流式读取。
2. 机器人产业链候选实体筛选。
3. `Company`、`ProductObject`、`Technology`、`IndustrySector`、`Region` 五类实体。
4. 核心 Wikidata 属性路由。
5. 输出 `GraphImportBatchDTO` dry-run 和 coverage report。
6. 暂不做全量 dump、DBpedia、Wikipedia 正文增强和 live import。

## 2. 新增目录

建议新增：

```text
backend/app/wiki_industry_pipeline/
  __init__.py
  cli.py
  dto.py
  schema_loader.py
  wikidata_reader.py
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
  wiki_industry_schema_loader_test.py
  wiki_industry_candidate_filter_test.py
  wiki_industry_claim_extractor_test.py
  wiki_industry_claim_router_test.py
  wiki_industry_graph_mapper_test.py
  wiki_industry_cli_test.py
```

## 3. 任务拆解

### Task 1：补配置文件

文件：

- 新增 `configs/industry_wiki/IncIndustryWiki.routing.schema.yaml`
- 新增 `configs/industry_wiki/robotics_seed_terms.yaml`
- 新增 `configs/industry_wiki/wikidata_property_mapping.yaml`

内容：

- `IncIndustryWiki.routing.schema.yaml` 保存 category、module、routing 规则。
- `robotics_seed_terms.yaml` 保存机器人产业关键词、种子类型和可选种子 QID。
- `wikidata_property_mapping.yaml` 保存 Wikidata 属性到内部语义名、IncCore 字段和关系的映射。

验收：

- 配置文件能被 YAML loader 读取。
- 所有属性映射至少覆盖：`P31`、`P279`、`P452`、`P1056`、`P176`、`P178`、`P127`、`P749`、`P355`、`P159`、`P17`、`P131`、`P276`、`P571`、`P1128`、`P2139`、`P414`、`P856`。

### Task 2：定义 DTO

文件：

- 新增 `backend/app/wiki_industry_pipeline/dto.py`
- 新增测试 `backend/tests/wiki_industry_pipeline_dto_test.py`

DTO：

- `WikiDumpRecordDTO`
- `WikiEntityCandidateDTO`
- `WikiClaimDTO`
- `RoutedClaimDTO`
- `WikiGraphBuildBatchDTO`
- `WikiCoverageReportDTO`

测试重点：

- DTO 默认值正确。
- `RoutedClaimDTO.route` 支持 `core`、`intrinsic`、`relational`、`unclaimed`。
- `WikiGraphBuildBatchDTO` 能承载 entities、claims、routed_claims、unclaimed。

### Task 3：实现 routing schema loader

文件：

- 新增 `backend/app/wiki_industry_pipeline/schema_loader.py`
- 新增测试 `backend/tests/wiki_industry_schema_loader_test.py`

功能：

- 加载 YAML routing schema。
- 根据 category 名称返回目标 IncCore 类型。
- 根据 property id 查找 module、route、edge、target_type。
- 对未知属性返回 `unclaimed`。

测试样例：

- `P571` 在 `Company.basic_profile` 下路由为 `intrinsic`。
- `P1056` 在 `Company.product_portfolio` 下路由为 `relational`，edge 为 `hasProduct`。
- 未知属性路由为 `unclaimed`。

### Task 4：实现 Wikidata reader

文件：

- 新增 `backend/app/wiki_industry_pipeline/wikidata_reader.py`
- 新增测试 `backend/tests/wiki_industry_candidate_filter_test.py`

功能：

- 支持读取普通 `.jsonl` 小样本。
- 支持读取 `.bz2` dump。
- 支持 `limit` 参数。
- 输出 `WikiDumpRecordDTO`。

第一期不要求解析完整 dump 的所有边界情况，但要能处理 Wikidata JSON dump 的外层 `[`、`,`、`]` 包装。

测试重点：

- 能读取 2 到 3 条样本 entity。
- 能跳过空行和 JSON 外层符号。
- `limit=1` 时只返回一条。

### Task 5：实现候选实体筛选

文件：

- 新增 `backend/app/wiki_industry_pipeline/candidate_filter.py`
- 新增测试 `backend/tests/wiki_industry_candidate_filter_test.py`

功能：

- 从 raw entity 中抽取 label、aliases、description、claims、sitelinks。
- 根据三类规则判断是否入选：
  - 类型命中：`P31` / `P279`
  - 属性命中：`P452`、`P1056`、`P176` 等
  - 关键词命中：robotics、industrial robot、机器人等
- 输出 `WikiEntityCandidateDTO`。

测试样例：

- 一个含 `P1056` 的 company 能入选。
- 一个 description 包含 `robotics` 的 entity 能入选。
- 一个完全无关 entity 被过滤。
- `matched_reasons` 记录命中原因。

### Task 6：实现 claim extractor

文件：

- 新增 `backend/app/wiki_industry_pipeline/claim_extractor.py`
- 新增测试 `backend/tests/wiki_industry_claim_extractor_test.py`

功能：

- 从 `WikiEntityCandidateDTO.claims` 中抽取 claim。
- 支持 wikibase entity value。
- 支持 time、quantity、string、url 等 literal value。
- 保存 qualifiers 和 references 的轻量结构。

测试样例：

- `P452` 产生一个 value_id 型 claim。
- `P571` 产生一个 literal/time 型 claim。
- 缺 value 的 claim 被跳过或标记为无效。

### Task 7：实现 claim router

文件：

- 新增 `backend/app/wiki_industry_pipeline/claim_router.py`
- 新增测试 `backend/tests/wiki_industry_claim_router_test.py`

功能：

- 输入 `WikiClaimDTO` 和 subject category。
- 根据 routing schema 生成 `RoutedClaimDTO`。
- 支持 intrinsic / relational / unclaimed。
- relational claim 补充 edge_type 和 target_type。

测试样例：

- Company + `P571` -> intrinsic, module=`basic_profile`。
- Company + `P1056` -> relational, edge=`hasProduct`, target=`IncCore.ProductObject`。
- Company + 未知属性 -> unclaimed。

### Task 8：实现 concept builder

文件：

- 新增 `backend/app/wiki_industry_pipeline/concept_builder.py`
- 新增测试可并入 `wiki_industry_graph_mapper_test.py`

功能：

- 将 `P31`、`P279` 生成概念节点和 `isA` 边。
- 将人工 taxonomy 中的机器人产业概念注入图谱。
- 生成 `NormalizedConceptSeedDTO` 或直接生成 `GraphNodeUpsertDTO`。

第一期原则：

- 先保留简单概念层，不做复杂概念归并。
- 只确保 `ProductCategory`、`TechnologyCategory`、`IndustrySector` 能落图。

### Task 9：实现 entity resolver

文件：

- 新增 `backend/app/wiki_industry_pipeline/entity_resolver.py`

功能：

- 以 Wikidata QID 作为第一主键。
- DBpedia URI、Wikipedia URL 作为 alias/source id。
- 对无完整候选实体但被边引用的对象生成 stub node。

第一期原则：

- 不做复杂名称消歧。
- 不合并不同 QID。
- 保证 graph_id 稳定。

graph_id 规则：

```text
Company:wiki:{qid}
ProductObject:wiki:{qid}
Technology:wiki:{qid}
IndustrySector:wiki:{qid}
Region:wiki:{qid}
```

### Task 10：实现 graph mapper

文件：

- 新增 `backend/app/wiki_industry_pipeline/graph_mapper.py`
- 新增测试 `backend/tests/wiki_industry_graph_mapper_test.py`

功能：

- 将 `WikiGraphBuildBatchDTO` 转为 `GraphImportBatchDTO`。
- intrinsic claim 写节点 properties。
- relational claim 写 edge。
- unclaimed 不入图，但保留在 coverage report。
- stub node 写入对应节点列表，并标记 `semanticType=stub`。

测试样例：

- Company + `P571` 写入 `foundedDate`。
- Company + `P1056` 写入 `hasProduct` 边。
- ProductObject stub 被创建。
- 节点和边数量符合预期。

### Task 11：实现 coverage reporter

文件：

- 新增 `backend/app/wiki_industry_pipeline/coverage_reporter.py`

功能：

- 统计：
  - 原始记录数
  - 候选实体数
  - claim 数
  - routed claim 数
  - intrinsic / relational / unclaimed 比例
  - 各 property 出现次数
  - 未路由 property 排行
  - stub node 数

输出：

```json
{
  "raw_record_count": 1000,
  "candidate_count": 120,
  "claim_count": 800,
  "claim_routing_rate": 0.72,
  "relational_claim_rate": 0.45,
  "intrinsic_claim_rate": 0.27,
  "unclaimed_rate": 0.28,
  "top_unclaimed_properties": []
}
```

### Task 12：实现 CLI

文件：

- 新增 `backend/app/wiki_industry_pipeline/cli.py`
- 新增测试 `backend/tests/wiki_industry_cli_test.py`

命令：

```bash
PYTHONPATH=backend python -m app.wiki_industry_pipeline.cli build \
  --dump tmp/wiki/sample_wikidata_robotics.jsonl \
  --routing-schema configs/industry_wiki/IncIndustryWiki.routing.schema.yaml \
  --domain robotics \
  --limit 1000 \
  --output tmp/wiki/wiki_industry_graph_batch.json \
  --report tmp/wiki/wiki_industry_coverage_report.json \
  --dry-run
```

验收：

- CLI 能跑完样本文件。
- 输出 graph batch JSON。
- 输出 coverage report JSON。
- dry-run 不访问 OpenSPG。

## 4. 测试策略

必须先写测试，再实现功能。

推荐测试顺序：

1. DTO 测试。
2. schema loader 测试。
3. candidate filter 测试。
4. claim extractor 测试。
5. claim router 测试。
6. graph mapper 测试。
7. CLI 集成测试。

推荐测试命令：

```bash
PYTHONPATH=backend ./.venv-kag/bin/python -m pytest \
  backend/tests/wiki_industry_pipeline_dto_test.py \
  backend/tests/wiki_industry_schema_loader_test.py \
  backend/tests/wiki_industry_candidate_filter_test.py \
  backend/tests/wiki_industry_claim_extractor_test.py \
  backend/tests/wiki_industry_claim_router_test.py \
  backend/tests/wiki_industry_graph_mapper_test.py \
  backend/tests/wiki_industry_cli_test.py \
  -q
```

## 5. 第一版样本数据

建议新增小样本：

```text
backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl
```

至少包含：

1. 一个机器人企业样本。
2. 一个机器人产品样本。
3. 一个机器人技术样本。
4. 一个区域样本。
5. 一个无关实体样本。

样本字段只需要覆盖：

- `id`
- `labels`
- `aliases`
- `descriptions`
- `claims`
- `sitelinks`

## 6. 与现有代码的集成点

第一期尽量不改现有 pipeline，只复用现有 DTO：

- `GraphNodeUpsertDTO`
- `GraphEdgeUpsertDTO`
- `GraphImportBatchDTO`
- `GraphImportResultDTO`

后续接入工作台时再修改：

- `backend/app/knowledge_extraction_operators/dto.py`
- `backend/app/knowledge_extraction_operators/catalog_specs.py`
- `backend/app/knowledge_extraction_operators/operators/__init__.py`

第一期不动工作台前端，避免范围扩散。

## 7. 验收标准

第一期完成后必须满足：

1. CLI 能用样本 Wikidata JSONL 跑通。
2. 至少输出 5 类节点中的 3 类。
3. 至少输出 `hasProduct`、`industry`、`region`、`manufacturer` 中 2 类关系。
4. coverage report 中能看到 unclaimed property 排行。
5. 输出的 `GraphImportBatchDTO` 能被现有 `GraphImportOperator` dry-run。
6. 新增测试全部通过。

## 8. 不在第一期做的事情

明确不做：

1. 不处理完整 Wikidata dump 的性能优化。
2. 不接 DBpedia。
3. 不抽 Wikipedia 正文。
4. 不做 live OpenSPG import。
5. 不做复杂实体消歧。
6. 不改 IncCore.schema。
7. 不改前端工作台。

这些放到第二期和第三期。

