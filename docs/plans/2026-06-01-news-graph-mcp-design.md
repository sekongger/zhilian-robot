# 资讯融合大图 MCP 设计方案

更新时间：2026-06-01

## 1. 建设目标

我们要把现有“常识资讯融合大图”包装成一个只读 MCP 服务，供外部 agent 在生成产业简报时调用。

这个 MCP 不负责重新抽取资讯，也不负责修改图谱。它只消费已经落到 Neo4j / OpenSPG 图中的资讯融合结果，把 `Episodic`、`NewsEntityProfile`、`refersTo`、`mentions` 等节点和关系整理成稳定的 agent 工具接口。

核心目标是：

- 支持按用户关注的产业、企业、产品生成可解释资讯流。
- 支持给简报 agent 召回推荐候选资讯，并说明推荐理由。
- 支持围绕企业、产品、技术或行业获取动态上下文。
- 支持返回可直接用于产业简报的结构化材料，包括标题、摘要、发布时间、来源、URL、关联实体、事件、关系和证据。

## 2. 服务边界

服务命名为 `incore-news-graph-mcp`，采用 sidecar 方式部署。

它和现有 `kag-mcp` 的定位不同：

```text
kag-mcp
  负责知识库问答、KAG 检索和推理问答。

incore-news-graph-mcp
  负责订阅资讯流、推荐候选资讯、实体动态时间线、企业上下文和原文证据。
```

两个 MCP 可以同时挂给同一个 agent。

## 3. 依赖的大图结构

当前大图分为三层。

第一层是常识骨架层，主要来自 Wikidata / IncCore。典型节点包括 `Enterprise:wiki:*`、`Product:wiki:*`、`ProductModel:wiki:*`、`Industry:wiki:*`。这一层更新频率低，承担稳定身份锚点。

第二层是资讯动态层，核心节点是 `NewsEntityProfile`。它保存来源实体、动态画像、匹配结果、批次和来源系统等字段，并通过 `refersTo` 链接到常识骨架节点。

第三层是事实证据层，核心节点是 `Episodic`。它保存资讯标题、摘要、发布时间、来源、原文 URL 和抽取上下文，并通过 `mentions` 等关系连接到资讯画像或抽取实体。

MCP 查询优先以 `Episodic` 作为资讯入口，以 `NewsEntityProfile` 作为实体动态入口，以 `refersTo` 作为资讯动态和常识骨架之间的身份链接。

## 4. 当前对外工具

当前对外 MCP 工具目录收敛为 5 个，分别覆盖小程序资讯推荐、简报候选素材、企业产业链上下文、实体动态追踪和原文查证。早期的 `query_latest_news`、`query_industry_briefing_context`、`search_news_graph` 不再注册为公开 MCP 工具，避免下游 agent 在通用查询入口和产品化入口之间选择混乱。

### 4.1 `query_subscription_news_feed`

按用户关注的产业、企业、产品和偏好标签生成订阅资讯流，目标是支持小程序面向用户的资讯推荐。

参数：

- `industries`：用户关注的产业列表。
- `enterprises`：用户关注的企业列表。
- `products`：用户关注的产品或技术列表。
- `preference_tags`：用户偏好标签。
- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用。
- `limit`：返回条数。

返回结果包括 `subscription_profile`、`feed_summary`、`items[].matched_subscription` 和 `items[].recommendation`。

### 4.2 `query_recommended_news_candidates`

按产业、企业、产品和偏好标签召回推荐候选资讯，目标是支持小程序推荐和简报素材筛选。

参数：

- `industries`：产业列表。
- `entity_names`：企业或实体列表。
- `product_names`：产品、型号或技术列表。
- `preference_tags`：偏好标签。
- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用。
- `limit`：返回条数。

返回结果包括 `recommendation.score`、`recommendation.matched_terms`、`recommendation.reasons` 和 `llm_context`，下游 agent 可以直接解释推荐原因。

### 4.3 `query_enterprise_supply_chain_context`

围绕某个企业查询产业链上下文，目标是让 agent 不只拿到孤立资讯，而能看到该企业在当前融合图中的上下游企业、关联产品、近期资讯时间线和可直接引用的自然语言上下文。

参数：

- `entity_name`：企业名称，可选。
- `canonical_graph_id`：常识骨架节点 ID，可选。
- `since_hours`：资讯时间范围，默认 720。
- `limit`：关联实体和资讯数量上限。

返回结果包括 `upstream_enterprises`、`downstream_enterprises`、`products`、`news_timeline` 和 `llm_context`。

### 4.4 `query_entity_news_timeline`

查询某个实体的资讯动态时间线。

参数：

- `entity_name`：实体名称。
- `canonical_graph_id`：常识骨架节点 ID，例如 `Enterprise:wiki:Q20716`。
- `since_hours`：最近多少小时，默认 168。
- `limit`：返回条数，默认 20。

### 4.5 `query_news_by_source_industry`

按时间、信息源和产业查询资讯数据，目标是支持 agent 精确拉取某个来源在某个时间窗口内采集到的产业资讯，并同时获得摘要和原文。

参数：

- `start_time`：起始时间，ISO 字符串，可选。
- `end_time`：结束时间，ISO 字符串，可选。
- `since_hours`：未传 `start_time` 时使用。
- `source_name`：信息源名称关键词。
- `industry`：产业关键词。
- `limit`：返回条数。

返回结果中的资讯条目会包含 `summary` 和 `content`。其中 `summary` 用于快速判断价值，`content` 用于让 agent 在生成简报时保留更完整的原文依据。

## 5. 返回字段

MCP 工具统一返回 agent 友好的 JSON，而不是直接暴露原始 Neo4j 节点。

资讯结果包含：

- `news_id`
- `title`
- `summary`
- `content_excerpt`
- `publish_time`
- `ingested_at`
- `source_name`
- `source_url`
- `batch_id`
- `group_id`
- `entities`
- `events`
- `relations`
- `briefing_signals`

实体结果包含：

- `name`
- `type`
- `profile_id`
- `canonical_graph_id`
- `match_method`
- `match_score`
- `summary`

## 6. 时间规则

不同来源的资讯时间字段不完全一致。MCP 查询统一使用：

```text
coalesce(publish_time, valid_at, created_at, ingested_at)
```

这样可以兼容 Graphiti 原生节点和融合导入后的节点。

## 7. 使用建议

产业简报 agent 的推荐调用顺序是：

1. 先用 `query_recommended_news_candidates` 获取主题下的推荐候选材料。
2. 对重点企业调用 `query_enterprise_supply_chain_context` 获取企业产业链上下文。
3. 对重点实体调用 `query_entity_news_timeline` 补充时间线。
4. 如需查证来源或引用原文，再调用 `query_news_by_source_industry`。
5. 简报正文优先引用带 `source_url` 和 `publish_time` 的资讯。

没有 `source_url`、`publish_time` 或证据片段的内容，只能作为线索，不应直接作为简报结论。
