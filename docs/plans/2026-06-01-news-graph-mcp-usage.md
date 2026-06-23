# 资讯融合大图 MCP 使用说明


## 1. 这个 MCP 做什么

`incore-news-graph-mcp` 是一个只读 MCP sidecar 服务，用来把我们已经构建好的“常识资讯融合大图”开放给 agent 调用。

它不负责重新抽取资讯，也不负责修改图谱。它只读取已经落到 Neo4j / OpenSPG 图中的 `Episodic`、`NewsEntityProfile`、`refersTo`、`mentions` 等节点和关系，把它们整理成适合 agent 使用的结构化 JSON。

这个服务的主要使用场景是小程序资讯推荐和产业简报生成。agent 可以通过 MCP 工具获取订阅资讯流、推荐候选资讯、实体动态、企业产业链上下文和原文证据，再基于这些材料生成资讯流或简报。

## 2. 为什么单独做一个 MCP

现有 `kag-mcp` 更偏向知识库问答和证据检索。资讯融合大图的需求更明确：按时间查最新动态，围绕企业或产业主题拉取证据，支撑简报写作。

所以这里新增独立 sidecar：

```text
kag-mcp
  负责：知识库问答、KAG 检索、推理问答

incore-news-graph-mcp
  负责：订阅资讯流、推荐候选资讯、实体动态、企业上下文、原文证据
```

两个 MCP 可以同时挂给同一个 agent。


## 3. 当前对外工具

当前对外 MCP 工具目录已经从早期 8 个收敛为 5 个。`query_latest_news`、`query_industry_briefing_context`、`search_news_graph` 属于早期通用查询或调试接口，不再作为下游 agent 的公开调用入口。后续新增工具也应优先围绕推荐、订阅、企业上下文和证据查证这几个产品场景设计。

### 3.1 `query_subscription_news_feed`

按用户关注的产业、企业、产品和偏好标签生成订阅资讯流。

参数：

- `industries`：用户关注的产业列表。
- `enterprises`：用户关注的企业列表。
- `products`：用户关注的产品或技术列表。
- `preference_tags`：用户偏好标签。
- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用，默认 168。
- `limit`：返回条数。

返回内容会额外整理：

- `subscription_profile`：本次订阅画像。
- `feed_summary`：资讯流摘要。
- `items[].matched_subscription`：每条资讯命中的订阅项。
- `items[].recommendation`：推荐分数和推荐理由。

适合问题：

```text
根据用户关注的产业、企业和产品生成小程序资讯流。
```

### 3.2 `query_recommended_news_candidates`

按产业、企业、产品和偏好标签召回推荐候选资讯。

参数：

- `industries`：产业列表，例如 `["AI服务器", "半导体"]`。
- `entity_names`：企业或实体列表，例如 `["三星", "高通"]`。
- `product_names`：产品、型号或技术列表，例如 `["企业级SSD", "AI PC"]`。
- `preference_tags`：偏好标签，例如 `["增长", "发布", "需求"]`。
- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用，默认 168。
- `limit`：返回条数，默认 20，最大 100。

返回内容会额外整理：

- `recommendation.score`：推荐分数。
- `recommendation.matched_terms`：命中的产业、企业、产品或偏好标签。
- `recommendation.reasons`：中文推荐理由。
- `llm_context`：可直接给 agent 使用的候选召回摘要。

适合的问题：

```text
给关注 AI服务器、三星、企业级SSD 的用户召回推荐候选资讯。
```

### 3.3 `query_enterprise_supply_chain_context`

查询某个企业在融合大图中的产业链上下文，并返回 LLM 更容易理解的中文摘要。

参数：

- `entity_name`：企业名称，例如“三星”。
- `canonical_graph_id`：常识骨架节点 ID，例如 `Enterprise:wiki:Q20716`。
- `since_hours`：资讯时间范围，默认 720。
- `limit`：返回关联实体和资讯数量上限。

返回内容会额外整理：

- `upstream_enterprises`：可能的上游或供给侧企业。
- `downstream_enterprises`：可能的下游、客户或应用侧企业。
- `products`：关联产品、技术、型号。
- `news_timeline`：相关资讯时间线。
- `llm_context`：可直接提供给 LLM 的自然语言上下文。

适合的问题：

```text
三星在当前图谱里有哪些上下游企业和关联产品？
Enterprise:wiki:Q20716 对应企业最近有哪些产业链相关变化？
```

### 3.4 `query_entity_news_timeline`

查询某个实体的资讯时间线。

参数：

- `entity_name`：实体名称。
- `canonical_graph_id`：常识骨架节点 ID，例如 `Enterprise:wiki:Q20716`。
- `since_hours`：最近多少小时，默认 168。
- `limit`：返回条数，默认 20。

适合的问题：

```text
腾讯最近一周有哪些产业相关动态？
Enterprise:wiki:Q20716 对应实体最近有什么新闻？
```

### 3.5 `query_news_by_source_industry`

按时间、信息源和产业查询资讯明细，并同时返回摘要和原文。

参数：

- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用，默认 168。
- `source_name`：信息源名称关键词，例如“Octopus News Feed”“manual”“八爪鱼”。
- `industry`：产业关键词，例如“AI服务器”“半导体”“具身智能”。
- `limit`：返回条数，默认 20，最大 100。

返回的每条资讯除通用字段外，还会包含 `content` 字段，用于保存资讯原文或完整抽取文本。

适合的问题：

```text
查询 2026-05-01 到 2026-06-30 从八爪鱼采集到的 AI 服务器资讯，并给出摘要和原文。
```

## 4. 返回字段

资讯结果统一返回以下字段：

- `news_id`：资讯节点 ID。
- `title`：标题。
- `summary`：摘要。
- `content_excerpt`：证据片段。
- `publish_time`：发布时间。
- `ingested_at`：入库时间。
- `source_name`：来源名称。
- `source_url`：原文链接。
- `batch_id`：融合批次。
- `group_id`：Graphiti / crawler 批次。
- `entities`：关联实体。
- `events`：关联事件。
- `relations`：关联关系。
- `briefing_signals`：给简报 agent 的写作提示。

实体结果包含：

- `name`
- `type`
- `profile_id`
- `canonical_graph_id`
- `match_method`
- `match_score`
- `summary`

## 5. 查询时间规则

图中不同来源的资讯时间字段不完全一致。MCP 查询统一使用：

```text
coalesce(publish_time, valid_at, created_at, ingested_at)
```

这样可以兼容 Graphiti 原生节点和融合导入后的节点。

## 6. 启动方式

推荐用 Docker Compose 启动 sidecar，它会复用 backend 的 Python 3.11 镜像：

```bash
docker compose up -d news-graph-mcp
```

默认 SSE 地址：

```text
http://localhost:3010/sse
```

如果需要本地直接运行，必须使用 Python 3.10+ 环境，因为官方 `mcp` 包不支持 Python 3.9。示例：

```bash
python3.11 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r backend/requirements.txt
PYTHONPATH=backend .venv-mcp/bin/python backend/scripts/run_news_graph_mcp.py --transport sse --port 3010
```

不要使用当前 `.venv-kag` 直接启动该 MCP；它是 Python 3.9 环境，只能跑服务逻辑测试，无法安装 `mcp==1.6.0`。

stdio 方式：

```bash
PYTHONPATH=backend .venv-mcp/bin/python backend/scripts/run_news_graph_mcp.py --transport stdio
```

服务读取以下环境变量连接融合大图所在 Neo4j：

- `NEWS_GRAPH_NEO4J_URI`：Neo4j Bolt 地址，未设置时回退到 `NEO4J_URI`。
- `NEWS_GRAPH_NEO4J_USER`：Neo4j 用户名，未设置时回退到 `NEO4J_USER`。
- `NEWS_GRAPH_NEO4J_PASSWORD`：Neo4j 密码，未设置时回退到 `NEO4J_PASSWORD`。
- `NEWS_GRAPH_NEO4J_DATABASE`：Neo4j database，可选，未设置时回退到 `NEO4J_DATABASE`。
- `NEWS_GRAPH_MCP_TRANSPORT`：默认传输方式，默认 `sse`。
- `NEWS_GRAPH_MCP_PORT`：SSE 端口，默认 `3010`。

## 7. Agent 推荐调用方式

如果 agent 要生成小程序资讯流，推荐优先调用 `query_subscription_news_feed`。如果 agent 要生成产业简报，推荐先调用 `query_recommended_news_candidates` 召回候选材料，再调用 `query_enterprise_supply_chain_context` 或 `query_entity_news_timeline` 展开重点企业和实体动态。需要引用原文或按来源查证时，调用 `query_news_by_source_industry`。

推荐调用顺序：

```text
query_subscription_news_feed(industries, enterprises, products, preference_tags)
  -> 小程序资讯流展示

query_recommended_news_candidates(industries, entity_names, product_names, preference_tags)
  -> query_enterprise_supply_chain_context(entity_name 或 canonical_graph_id)
  -> query_entity_news_timeline(entity_name 或 canonical_graph_id)
  -> query_news_by_source_industry(start_time, end_time, source_name, industry)
```

简报生成时应优先使用以下字段作为证据：

- `title`：简报条目的标题来源。
- `summary`：简报正文摘要材料。
- `content_excerpt`：可作为证据片段，但不应该直接整段照搬。
- `publish_time`：判断资讯新旧。
- `source_name`、`source_url`：用于引用来源。
- `entities[].canonical_graph_id`：判断资讯实体是否已挂接到常识骨架。
- `briefing_signals.suggested_section`：辅助决定写入“企业动态”“产品技术”“事件变化”等栏目。

## 8. 设计边界

这个 MCP 是只读服务，不负责抽取、融合、去重、落图。它默认图中已经存在以下数据：

- `Episodic`：资讯或片段节点。
- `NewsEntityProfile`：资讯侧动态画像节点。
- `Enterprise`、`Product`、`ProductModel`、`Technology` 等常识骨架节点。
- `mentions`：资讯和实体画像之间的提及关系。
- `refersTo`：资讯画像指向常识骨架节点的链接关系。

后续如果资讯抽取侧新增字段，优先在 `backend/app/news_graph_mcp/dto.py` 做字段归一化，不建议让 agent 直接依赖 Neo4j 原始字段。
