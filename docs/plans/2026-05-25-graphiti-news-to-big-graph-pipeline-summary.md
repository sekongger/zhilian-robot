# Graphiti 资讯收集到主图融合链路改造说明

## 1. 背景

我们当前的大图以 Wikidata 构建出的常识层为骨架，企业、产品、技术等节点主要来自稳定的百科型数据。这类数据更新频率较低，适合作为产业网链大图中的主干节点。

资讯数据的特点不同。资讯来自 RSS、八爪鱼、网页等动态来源，更新频率高、时效性强，内容里会持续出现新的企业动态、产品变化、市场事件和上下游关系。如果把这些动态字段直接合并进 Wikidata 常识节点，会带来两个问题：

1. 高频资讯字段会污染低频常识节点，后续更新和回滚都不方便。
2. 每次资讯增量更新时，很难判断哪些字段应该覆盖、哪些字段只是某条资讯中的事实证据。

因此，我们采用“链接式融合”的方式：Wikidata 节点继续作为主图骨架，Graphiti 从资讯中抽取出的动态实体和事实，先作为资讯侧节点进入图谱，再通过身份链接或事实关系挂到 Wikidata 骨架上。

## 2. 本次改造目标

本次工作的目标不是做前端页面，而是把后端链路打通，形成一条可重复执行、可按批次追踪、不会误融合历史数据的 Graphiti 资讯收集到主图融合 pipeline。

改造前，系统里已经有两部分能力：

- `graphiti_news_pipeline` 可以执行资讯采集、清洗、压缩，并通过 Graphiti 抽取实体和关系。
- `incore_fusion_pipeline` 已经具备把外部图谱节点映射到 IncCore 大图 DTO，并与 Wikidata canonical 节点做匹配融合的能力。

但两者之间还缺少稳定的批次边界和一键编排入口。也就是说，Graphiti 能抽取资讯，主图融合器也能融合数据，但还没有形成一条稳定的“本次资讯收集结果 -> 本次 Graphiti 抽取图 -> 本次主图融合结果”的闭环。

## 3. 改造后的整体链路

改造后的 pipeline 如下：

```text
资讯源 RSS / 八爪鱼 / 网页
-> graphiti_news_pipeline crawler
-> 清洗 / 相关性过滤 / 去重 / 压缩
-> /api/add-text
-> Graphiti.add_episode(group_id=run_id)
-> Graphiti Neo4j 生成 Episodic / Entity / Relation
-> GraphitiNewsNeo4jLoader 按 group_id 读取本批图
-> GraphitiNewsFusionRunner
-> Wikidata canonical 匹配
-> 生成 NewsEntityProfile / 动态事实节点 / refersTo 关系
-> 导入 OpenSPG Neo4j 主图
```

这里最关键的变化是：每次 crawler 运行都会生成一个 `run_id`，现在这个 `run_id` 会贯穿整个链路，作为 Graphiti 的 `group_id` 和融合批次标识使用。

## 4. 本次具体做了什么

### 4.1 打通 crawler run_id 到 Graphiti group_id 的透传

我们修改了 Graphiti 资讯收集链路，让 crawler 的 `run_id` 不只是运行日志编号，而是成为 Graphiti 抽取图中的批次边界。

具体做法是：

- crawler 每次运行生成 `run_id`。
- ingest 阶段把 `run_id` 写入 `/api/add-text` 请求体中的 `group_id` 和 `fusion_batch_id`。
- `/api/add-text` 接收这两个字段，并继续传给 `GraphitiService.add_text_episode`。
- `GraphitiService.add_text_episode` 调用 `Graphiti.add_episode(..., group_id=...)`。
- 同时把 `group_id / fusion_batch_id` 写入 Episodic 节点元数据。

这样做以后，Graphiti Neo4j 中的资讯 episode 就天然带有批次信息。后续融合时可以只读取本批数据，而不是扫描整个 Graphiti 历史图。

涉及的核心文件包括：

- `graphiti_news_pipeline/crawler/pipeline/orchestrator.py`
- `graphiti_news_pipeline/crawler/pipeline/steps/ingest_step.py`
- `graphiti_news_pipeline/api/graph_routes.py`
- `graphiti_news_pipeline/services/graphiti_service.py`

### 4.2 强化 Graphiti 到主图融合的批次读取逻辑

之前的 Graphiti loader 可以从 Graphiti Neo4j 中读取 `Entity / Episodic / Relationship`，但如果没有明确批次过滤，就容易把历史资讯节点也读进来。

本次我们增强了 `GraphitiNewsNeo4jLoader`：

- 支持按 `group_id` 或 `fusion_batch_id` 读取本批节点。
- 读取本批命中的 Episodic 或 Entity 后，会补齐它们的一跳相邻实体。
- 这样即使 Graphiti 只在 Episodic 上写了批次字段，也不会丢掉该资讯提到的企业、产品、技术等实体节点。

这一步解决的是“只融合本批资讯，但又不能丢掉本批资讯关联实体”的问题。

涉及文件：

- `backend/app/incore_fusion_pipeline/loaders/graphiti_news_neo4j_loader.py`

### 4.3 把融合脚本升级为一键编排入口

我们对 `run_graphiti_news_big_graph_fusion.py` 做了增强，使它不再只是简单地读取 Graphiti Neo4j 并融合，而是承担完整 pipeline 的编排职责。

现在这个脚本支持：

- Graphiti API 健康检查。
- Graphiti database 初始化。
- 可选执行 `graphiti_news_pipeline` 的 crawler。
- 捕获 crawler 输出的 JSON 运行摘要。
- 从 crawler 摘要中自动拿到 `run_id`，并作为本次融合的 `group_id`。
- 如果 Graphiti ingest 全部失败，直接中断，避免继续融合空数据或旧数据。
- 按 `group_id` 读取 Graphiti Neo4j。
- 运行 Wikidata canonical 匹配和大图融合。
- 输出 `fusion_batch.json / node_decisions.json / relation_decisions.json / fusion_report.json`。
- 可选导入 OpenSPG Neo4j 进行图形化查看。

涉及文件：

- `backend/scripts/run_graphiti_news_big_graph_fusion.py`

## 5. 融合后的图谱组织方式

本次仍然坚持“链接式融合”，不会把资讯字段直接覆盖到 Wikidata 常识节点上。

如果 Graphiti 抽取出的资讯实体能匹配到 Wikidata 节点，会生成一个资讯画像节点：

```text
NewsEntityProfile:graphiti:{graphiti_uuid}
```

然后通过 `refersTo` 指向 Wikidata canonical 节点：

```text
NewsEntityProfile:graphiti:{graphiti_uuid}
-> refersTo
Enterprise:wiki:{qid}
```

如果无法匹配到 Wikidata 节点，则保留为 Graphiti 资讯侧新增节点，例如：

```text
Enterprise:fusion:graphiti:{graphiti_uuid}
Product:fusion:graphiti:{graphiti_uuid}
Episodic:fusion:graphiti:{episode_uuid}
```

这样可以同时满足两个目标：

1. Wikidata 常识节点保持稳定，不被动态资讯频繁覆盖。
2. 资讯中的动态事实、来源、证据、热度和事件线索可以独立更新、独立删除、独立追溯。

## 6. 输出产物

每次 pipeline 运行后，会在 `tmp/incore_fusion_runs/{batch_id}` 下生成一组结果文件：

- `fusion_batch.json`：最终准备导入主图的节点和边。
- `node_decisions.json`：每个 Graphiti 节点的融合决策，例如匹配 Wikidata、创建新节点等。
- `relation_decisions.json`：每条 Graphiti 关系如何映射到主图关系。
- `fusion_report.json`：本批次总体报告，包括节点数、边数、warning、crawler 摘要、Graphiti group id 等。

这些文件是后续调试和审计的基础。尤其是 `node_decisions.json`，可以用来检查某个资讯实体为什么匹配到了某个 Wikidata 节点，或者为什么没有匹配成功。

## 7. 验证结果

本次改造后，我们做了两类验证。

第一类是自动化测试：

```text
Graphiti 子项目测试：11 passed
主项目融合测试：7 passed
```

覆盖内容包括：

- crawler ingest 是否把 `group_id / fusion_batch_id` 发给 Graphiti。
- `/api/add-text` 是否把批次字段传给 `GraphitiService`。
- 融合 CLI 是否能解析 crawler 输出。
- 当 Graphiti ingest 全失败时，pipeline 是否会中断。
- Graphiti 资讯节点是否能融合为 `NewsEntityProfile` 并通过 `refersTo` 链接 Wikidata。

第二类是小规模落图验证：

我们复用已有的 Graphiti 测试批次 `manual_smoke_20260524`，按 `group_id` 读取该批数据，并导入 OpenSPG Neo4j。

验证结果：

```text
batch_id: graphiti_news_group_scoped_20260524
graphiti_group_id: manual_smoke_20260524
node_count: 7
edge_count: 12
warnings: []
```

其中，资讯侧的“三星集团”画像节点已经成功通过 `refersTo` 指向 Wikidata 骨架节点：

```text
NewsEntityProfile:graphiti:{graphiti_uuid}
-> refersTo
Enterprise:wiki:Q20716
```

## 8. 当前限制

当前链路已经打通，但真实 RSS/八爪鱼资讯抽取还依赖 Graphiti 的 LLM 和 embedding 配置。

在上一次真实 `/api/add-text` 调用中，Graphiti 的 LLM 接口返回：

```text
401 Api key is invalid
```

因此，本次验证主要证明“Graphiti 已抽取图 -> 主图融合”这半段链路已经稳定。要跑真实资讯端到端抽取，需要先修正以下配置：

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_BASE`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIM`

## 9. 后续建议

下一步建议按以下顺序推进：

1. 修复 Graphiti 的 LLM 和 embedding 配置，确保 `/api/add-text` 能真实抽取。
2. 用 `--run-crawler --ingest` 跑一次真实小批量 RSS 资讯。
3. 检查 `fusion_report.json` 和 `node_decisions.json`，确认匹配质量。
4. 对企业、产品、技术三类节点分别补充更强的匹配规则。
5. 将这条 pipeline 纳入定时任务，形成“定期资讯收集 -> 增量融合主图”的生产链路。

## 10. 一句话总结

本次工作把 Graphiti 资讯收集和 IncCore 主图融合从“两个分散能力”收敛成了一条有批次边界、可审计、可中断保护、可增量融合的后端 pipeline。它为后续把真实资讯持续接入产业网链大图打下了基础。
