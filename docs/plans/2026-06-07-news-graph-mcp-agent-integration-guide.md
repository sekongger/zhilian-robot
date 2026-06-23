# 资讯融合大图 MCP 下游 Agent 接入说明

## 1. 文档目的

这份文档面向下游“资讯简报 agent”和小程序推荐链路的开发者。

我们提供的 `incore-news-graph-mcp` 是只读 MCP 服务，负责从资讯融合大图中查询资讯、实体动态、产业链上下文和推荐候选材料。下游 agent 不需要直接写 Cypher，也不需要理解 Neo4j 内部节点结构，只需要按本文约定调用 MCP 工具，并使用返回的结构化字段生成资讯流或产业简报。

当前 MCP 的定位是：

```text
资讯抽取/融合 pipeline
  -> OpenSPG / Neo4j 资讯融合大图
  -> incore-news-graph-mcp
  -> 资讯推荐 agent / 简报 agent
  -> 小程序资讯流和简报展示
```

## 2. 推荐调用顺序

### 2.1 小程序资讯推荐流

如果目标是给用户推荐资讯，优先调用：

```text
query_subscription_news_feed
```

适用场景：

- 用户关注了若干产业，例如 AI服务器、半导体、具身智能。
- 用户关注了若干企业，例如 三星、高通、腾讯。
- 用户关注了若干产品或技术，例如 企业级SSD、AI PC、HBM。
- 小程序需要生成一批可解释的资讯流。

推荐调用流程：

```text
1. 从用户画像读取关注项
2. 调用 query_subscription_news_feed
3. 按 recommendation.score 排序或截断
4. 使用 matched_subscription 生成推荐理由
5. 小程序展示 title、summary、source_name、publish_time、recommendation.reasons
```

### 2.2 简报候选材料生成

如果目标是给简报 agent 准备素材，优先调用：

```text
query_recommended_news_candidates
```

适用场景：

- agent 已经知道本期简报主题。
- 需要先召回一批高价值候选资讯。
- 需要知道每条资讯为什么值得写进简报。

推荐调用流程：

```text
1. 输入产业、企业、产品、偏好标签和时间窗口
2. 调用 query_recommended_news_candidates
3. 读取 items[].recommendation.score 和 items[].recommendation.reasons
4. 选择高分、带 source_url、带关系或事件线索的资讯
5. 再按需要调用 query_enterprise_supply_chain_context 展开重点企业
6. 生成简报正文，并引用 source_url 和 publish_time
```

### 2.3 企业专题简报

如果目标是围绕某个企业写专题，推荐调用：

```text
query_enterprise_supply_chain_context
  -> query_entity_news_timeline
  -> query_news_by_source_industry
```

调用逻辑：

- 先用 `query_enterprise_supply_chain_context` 获取企业、产品、上下游和 `llm_context`。
- 再用 `query_entity_news_timeline` 获取企业近期资讯时间线。
- 如果需要查某个来源或产业下的原文，再用 `query_news_by_source_industry` 获取 `content`。

### 2.4 主题型产业简报

如果目标是“AI服务器周报”“半导体产业动态”这类主题简报，推荐调用：

```text
query_recommended_news_candidates
  -> query_enterprise_supply_chain_context
  -> query_entity_news_timeline
  -> query_news_by_source_industry
```

调用逻辑：

- `query_recommended_news_candidates` 用于生成可解释候选，先解决“哪些资讯值得写”的问题。
- `query_enterprise_supply_chain_context` 用于对候选资讯中的重点企业做产业链展开。
- `query_entity_news_timeline` 用于补充重点企业、产品或技术的近期动态。
- `query_news_by_source_industry` 用于按来源、产业和时间窗口获取原文，支撑事实查证。

当前对外 MCP 工具目录只保留 5 个稳定工具。早期的 `query_industry_briefing_context`、`search_news_graph` 和 `query_latest_news` 已从公开注册目录下线，不建议下游 agent 再依赖。

## 3. 工具字段契约

### 3.1 `query_subscription_news_feed`

用途：按用户关注的产业、企业、产品和偏好标签生成订阅资讯流。

输入字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `industries` | `list[str]` | 否 | 用户关注的产业，例如 `["AI服务器", "半导体"]` |
| `enterprises` | `list[str]` | 否 | 用户关注的企业，例如 `["三星", "高通"]` |
| `products` | `list[str]` | 否 | 用户关注的产品或技术，例如 `["企业级SSD", "AI PC"]` |
| `preference_tags` | `list[str]` | 否 | 偏好标签，例如 `["增长", "发布", "需求"]` |
| `start_time` | `str` | 否 | 起始时间，ISO 格式 |
| `end_time` | `str` | 否 | 结束时间，ISO 格式 |
| `since_hours` | `int` | 否 | 未传 `start_time` 时使用，默认 168 |
| `limit` | `int` | 否 | 返回条数，默认 20，最大 100 |

核心返回字段：

| 字段 | 说明 |
|---|---|
| `subscription_profile` | 本次订阅画像，回显产业、企业、产品和偏好标签 |
| `feed_summary` | 可直接给 LLM 使用的资讯流摘要 |
| `items` | 资讯列表 |
| `items[].matched_subscription` | 每条资讯命中的订阅项 |
| `items[].recommendation` | 推荐分数、命中词、推荐理由 |

推荐使用：

```text
小程序资讯流优先使用这个工具。
展示时可以用 recommendation.reasons 解释推荐原因。
```

### 3.2 `query_recommended_news_candidates`

用途：按产业、企业、产品和偏好标签召回推荐候选资讯。

输入字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `industries` | `list[str]` | 否 | 候选资讯相关产业 |
| `entity_names` | `list[str]` | 否 | 候选资讯相关企业或实体 |
| `product_names` | `list[str]` | 否 | 候选资讯相关产品、型号或技术 |
| `preference_tags` | `list[str]` | 否 | 候选资讯偏好标签 |
| `start_time` | `str` | 否 | 起始时间，ISO 格式 |
| `end_time` | `str` | 否 | 结束时间，ISO 格式 |
| `since_hours` | `int` | 否 | 未传 `start_time` 时使用 |
| `limit` | `int` | 否 | 返回条数 |

核心返回字段：

| 字段 | 说明 |
|---|---|
| `items[].recommendation.score` | 推荐分数，0 到 100 |
| `items[].recommendation.matched_terms` | 命中的产业、企业、产品或标签 |
| `items[].recommendation.reasons` | 中文推荐理由 |
| `items[].recommendation.suggested_use` | 对 agent 的使用建议 |
| `llm_context` | 本次候选召回的整体说明 |

推荐使用：

```text
简报 agent 在写作前可以先调用这个工具，选出候选事实材料。
```

### 3.3 通用资讯字段

大多数返回资讯都会包含以下字段：

| 字段 | 说明 |
|---|---|
| `news_id` | 资讯节点 ID |
| `title` | 资讯标题 |
| `summary` | 资讯摘要 |
| `content_excerpt` | 资讯片段 |
| `content` | 资讯原文，只有部分工具返回，例如 `query_news_by_source_industry` |
| `publish_time` | 发布时间 |
| `ingested_at` | 入库时间 |
| `source_name` | 信息源名称 |
| `source_url` | 原文链接 |
| `batch_id` | 融合批次 |
| `entities` | 关联实体 |
| `events` | 关联事件 |
| `relations` | 关联关系 |
| `briefing_signals` | 给简报 agent 的写作提示 |

### 3.4 实体字段

`entities` 中每个实体一般包含：

| 字段 | 说明 |
|---|---|
| `name` | 实体名称 |
| `type` | 实体类型，例如 Enterprise、Product、ProductModel、Technology |
| `profile_id` | 资讯侧实体节点 ID |
| `canonical_graph_id` | 常识图谱骨架 ID，可为空 |
| `match_method` | 与常识节点的匹配方式 |
| `match_score` | 匹配分数 |
| `summary` | 实体描述 |

## 4. 样例调用

### 4.1 用户订阅资讯流

输入：

```json
{
  "industries": ["AI服务器", "AI PC"],
  "enterprises": ["三星", "高通"],
  "products": ["企业级SSD", "AI PC"],
  "preference_tags": ["增长", "发布", "需求"],
  "start_time": "2026-05-01T00:00:00+00:00",
  "end_time": "2026-06-30T00:00:00+00:00",
  "limit": 5
}
```

返回节选：

```json
{
  "query": "subscription_news_feed",
  "feed_summary": "针对 AI服务器、AI PC、三星、高通、企业级SSD、AI PC、增长、发布、需求 生成资讯流，共召回 5 条资讯。",
  "items": [
    {
      "title": "小范围测试资讯：三星存储芯片价格变化",
      "summary": "三星集团相关存储芯片和企业级SSD需求变化资讯。",
      "recommendation": {
        "score": 100,
        "matched_terms": ["AI服务器", "三星", "企业级SSD", "需求"],
        "reasons": [
          "命中关注产业：AI服务器。",
          "命中关注企业：三星。",
          "命中关注产品/技术：企业级SSD。",
          "命中偏好标签：需求。"
        ]
      },
      "matched_subscription": {
        "industries": ["AI服务器"],
        "enterprises": ["三星"],
        "products": ["企业级SSD"],
        "preference_tags": ["需求"]
      }
    }
  ]
}
```

### 4.2 推荐候选资讯

输入：

```json
{
  "industries": ["AI服务器", "半导体"],
  "entity_names": ["三星", "高通"],
  "product_names": ["企业级SSD", "AI PC"],
  "preference_tags": ["增长", "发布", "需求"],
  "start_time": "2026-05-01T00:00:00+00:00",
  "end_time": "2026-06-30T00:00:00+00:00",
  "limit": 5
}
```

返回节选：

```json
{
  "query": "recommended_news_candidates",
  "llm_context": "已召回 5 条推荐候选资讯。推荐时优先考虑分数高、带原文链接、包含事件或关系线索的资讯。",
  "items": [
    {
      "title": "小范围测试资讯：三星存储芯片价格变化",
      "summary": "三星集团相关存储芯片和企业级SSD需求变化资讯。",
      "recommendation": {
        "score": 100,
        "matched_terms": ["AI服务器", "三星", "企业级SSD", "需求"],
        "reasons": [
          "命中关注产业：AI服务器。",
          "命中关注企业：三星。",
          "命中关注产品/技术：企业级SSD。",
          "命中偏好标签：需求。",
          "包含事件或关系线索，适合作为简报材料。",
          "带有原文链接，可追溯来源。"
        ]
      }
    }
  ]
}
```

## 5. Agent 生成简报时的字段使用建议

简报标题：

- 优先参考 `title`。
- 如果是多条资讯合并，使用 `entities` 和 `matched_terms` 提炼主题。

简报摘要：

- 优先使用 `summary`。
- 如果需要更完整事实，调用 `query_news_by_source_industry` 获取 `content`。

推荐理由：

- 优先使用 `recommendation.reasons`。
- 小程序端可以直接展示其中 1 到 2 条。

事实证据：

- 优先使用 `source_url`、`source_name`、`publish_time`。
- 如果 `source_url` 为空，需要在简报中降低引用强度，避免写成强事实。

实体解释：

- 优先使用带 `canonical_graph_id` 的实体。
- `canonical_graph_id` 为空的实体可以作为动态线索，但不应当被当作已归一的常识实体。

## 6. 异常和空结果处理

### 6.1 空结果

如果 `items` 为空：

- 放宽时间窗口，例如从 24 小时扩大到 168 小时。
- 减少过滤条件，例如只保留产业，不传企业和产品。
- 对推荐任务，改用 `query_recommended_news_candidates` 并减少企业、产品、偏好标签数量。
- 对查证任务，改用 `query_news_by_source_industry`，先只传时间窗口和产业，不传来源。

建议 agent 输出：

```text
当前时间窗口内未检索到足够资讯，已扩大检索范围或建议稍后重试。
```

### 6.2 字段为空

常见可为空字段：

- `canonical_graph_id`
- `source_url`
- `events`
- `relations`
- `content`

处理原则：

- `canonical_graph_id` 为空：说明只是资讯侧动态实体，不能直接视为常识图谱已归一节点。
- `source_url` 为空：不要在最终简报中写“原文显示”，只能写“图谱中抽取到”。
- `events` 或 `relations` 为空：可以使用摘要，但不要强行生成事件链。
- `content` 为空：使用 `summary` 和 `content_excerpt`。

### 6.3 工具超时

如果 MCP 调用超时：

- 降低 `limit`，建议先用 10。
- 缩短时间窗口。
- 减少关键词数量。
- 对推荐流优先调用 `query_subscription_news_feed`，不要同时对大量产业、企业、产品做宽召回。

### 6.4 返回过长

如果返回内容过长：

- 小程序资讯流只展示 `title`、`summary`、`recommendation.reasons`、`source_name`、`publish_time`。
- 简报 agent 只保留前 5 到 10 条高分资讯。
- 只有在需要引用原文时，再调用 `query_news_by_source_industry` 获取 `content`。

## 7. 当前限制

1. 当前推荐分数是规则分，不是机器学习模型分。
2. 当前订阅匹配主要依赖文本和图中 mentions 实体，产品、技术、产业概念归一还需要继续增强。
3. 当前企业-企业上下游关系还不够充分，企业产业链上下文工具可能返回产品多、上下游企业少。
4. MCP 工具函数级测试已通过，但正式接入 agent 前还需要启动真实 MCP SSE/stdio 服务做协议级联调。

## 8. 最小接入检查清单

下游 agent 接入前建议检查：

| 检查项 | 要求 |
|---|---|
| MCP 服务可访问 | SSE 或 stdio 启动成功 |
| Neo4j database | 指向 `inccore` |
| 推荐工具 | `query_recommended_news_candidates` 有返回 |
| 订阅工具 | `query_subscription_news_feed` 有返回 |
| 原文工具 | `query_news_by_source_industry` 能返回 `content` |
| 空结果处理 | agent 能扩大时间窗口或降级搜索 |
| 引用策略 | agent 优先引用带 `source_url` 的资讯 |
