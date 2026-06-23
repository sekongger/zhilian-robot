# 资讯融合大图 MCP 工具测试报告

## 1. 测试结论

本次对资讯融合大图 MCP 工具做了一次收敛。原来对外暴露 8 个工具，其中部分工具是早期调试和探索阶段形成的通用查询能力，和后续新增的推荐、订阅、查证类工具存在重叠。为了让下游简报 agent 和小程序推荐链路更容易使用，当前对外 MCP 工具目录收敛为 5 个。


| 工具名                                     | 产品链路角色            | 测试结果                                |
| --------------------------------------- | ----------------- | ----------------------------------- |
| `query_subscription_news_feed`          | 小程序用户订阅资讯流入口      | 可按用户关注的产业、企业、产品和偏好标签返回资讯流           |
| `query_recommended_news_candidates`     | 简报 agent 推荐候选素材入口 | 可返回推荐分数、命中词、推荐理由和候选资讯               |
| `query_enterprise_supply_chain_context` | 企业专题和产业链展开入口      | 可返回企业、关联产品、资讯时间线和 LLM 可读上下文         |
| `query_entity_news_timeline`            | 实体动态追踪入口          | 可按实体名或 `canonical_graph_id` 返回资讯时间线 |
| `query_news_by_source_industry`         | 原文查证和来源过滤入口       | 可按时间、信息源、产业返回 summary 和原文 content   |


## 2. 测试环境


| 项目             | 内容                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------ |
| 代码目录           | `/Users/caixudong/Desktop/zhilian-robot`                                                         |
| Neo4j 地址       | `bolt://127.0.0.1:7688`                                                                          |
| Neo4j database | 默认库                                                                                              |
| 测试批次           | `graphiti_news_100_all_20260607`                                                                 |
| 本次复查工具原始返回文件   | `/Users/caixudong/Desktop/zhilian-robot/tmp/news_graph_mcp_traceable_tool_outputs_20260608.json` |
| 旧 smoke 返回文件状态 | 不再作为报告样例依据，其中包含早期手工测试链接                                                                          |


## 3. 已融合数据盘点

测试前查看了 `inccore` 数据库里已有的融合数据。当前主要有两批数据：


| batchId                            | 节点数 | 说明                     |
| ---------------------------------- | --- | ---------------------- |
| `graphiti_news_100_all_20260607`   | 742 | Graphiti 资讯抽取后融合入大图的数据 |
| `wikidata_v2_link_fusion_20260513` | 29  | 早期 Wikidata 链接融合测试数据   |


`graphiti_news_100_all_20260607` 批次中的主要节点类型如下：


| 节点标签                | 数量  |
| ------------------- | --- |
| `Episodic`          | 100 |
| `Product`           | 172 |
| `Technology`        | 119 |
| `Enterprise`        | 98  |
| `ProductModel`      | 65  |
| `Industry`          | 30  |
| `Organization`      | 29  |
| `Region`            | 19  |
| `EconomicSector`    | 18  |
| `NewsEntityProfile` | 17  |


关系侧的主要统计如下：


| 关系类型                  | 数量   |
| --------------------- | ---- |
| `mentions`            | 1460 |
| `produces`            | 42   |
| `develops`            | 30   |
| `developed`           | 30   |
| `has_feature`         | 26   |
| `uses`                | 26   |
| `released`            | 24   |
| `uses_technology`     | 22   |
| `supports_technology` | 22   |
| `collaborates_with`   | 22   |
| `refersTo`            | 17   |


当前融合方式不是把资讯字段直接覆盖到 Wikidata 常识节点上，而是保留资讯侧节点，并通过 `canonicalGraphId` 和 `refersTo` 链接指向常识节点。这个方式适合后续资讯增量更新，因为动态资讯可以独立新增、失效或重新抽取，不会破坏相对稳定的常识骨架。

本次复查同时检查了 `Episodic` 的原文链接质量。当前 100 条资讯节点中有 98 条带真实外部原文链接，2 条来自早期手工 smoke test，链接域名为 `example.com`。MCP 工具已经在返回层过滤这 2 条，后续抽取链路也会阻止这类占位链接继续入图。

## 4. 保留工具及理由

### 4.1 `query_subscription_news_feed`

这是最贴近小程序最终产品形态的工具。小程序要给用户推荐资讯，本质上需要根据用户关注的产业、企业、产品生成资讯流。这个工具直接接收这些关注项，并返回 `subscription_profile`、`feed_summary`、`items[].matched_subscription` 和 `items[].recommendation`。

与任务的适配性：

- 对应“小程序资讯推荐”的主入口。
- 能说明每条资讯命中了哪些订阅项，例如命中产业、企业、产品。
- 下游 agent 和小程序前端可以直接用 `recommendation.reasons` 生成推荐解释。
- 比 `query_latest_news` 更适合推荐任务，因为它不是简单按时间查新闻，而是按用户画像组织资讯流。

测试参数：

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

实际返回节选：

```json
{
  "query": "subscription_news_feed",
  "feed_summary": "针对 AI服务器、AI PC、三星、高通、企业级SSD、AI PC、增长、发布、需求 生成资讯流，共召回 5 条资讯。代表性资讯包括：苹果iPhone Ultra将采用三星的M14 OLED和均热板，而iPhone 18 Pro和Pro Max则配备更先进的M16面板；纳芯微推出ASIL D芯片，高端汽车半导体国产替代加速；绿联携AI NAS参展英特尔峰会，定义智能存储新生态。",
  "items": [
    {
      "title": "苹果iPhone Ultra将采用三星的M14 OLED和均热板，而iPhone 18 Pro和Pro Max则配备更先进的M16面板",
      "summary": "苹果首款折叠屏设备或定名iPhone Ultra，采用三星M14 OLED面板和专用均热板。",
      "source_name": "Octopus News Feed",
      "source_url": "https://www.icloudnews.net/a/118158.html",
      "recommendation": {
        "score": 65,
        "matched_terms": ["三星"],
        "reasons": [
          "命中关注企业：三星。",
          "包含事件或关系线索，适合作为简报材料。",
          "带有原文链接，可追溯来源。"
        ]
      },
      "matched_subscription": {
        "enterprises": ["三星"],
        "industries": [],
        "products": [],
        "preference_tags": []
      }
    }
  ]
}
```

### 4.2 `query_recommended_news_candidates`

这是给下游简报 agent 准备候选素材的主入口。它不绑定具体用户订阅画像，而是按产业、企业、产品召回一批候选资讯，并给每条资讯打推荐分、列出命中词和推荐理由。

与任务的适配性：

- 对应“资讯简报 agent 的素材召回”。
- 适合在 agent 写简报前先筛出高价值资讯。
- 返回 `score` 和 `reasons`，可以帮助 agent 判断哪些资讯应写入简报。
- 比 `query_industry_briefing_context` 更清晰，因为它不是直接替 agent 聚合简报，而是给 agent 一批可解释、可排序的候选事实材料。

测试参数：

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

实际返回节选：

```json
{
  "query": "recommended_news_candidates",
  "llm_context": "已召回 5 条推荐候选资讯。推荐时优先考虑分数高、带原文链接、包含事件或关系线索的资讯。候选标题包括：纳芯微推出ASIL D芯片，高端汽车半导体国产替代加速；苹果iPhone Ultra将采用三星的M14 OLED和均热板，而iPhone 18 Pro和Pro Max则配备更先进的M16面板；绿联携AI NAS参展英特尔峰会，定义智能存储新生态。",
  "items": [
    {
      "title": "纳芯微推出ASIL D芯片，高端汽车半导体国产替代加速",
      "summary": "纳芯微发布首款通过ASIL D认证的隔离栅极驱动芯片NSI6911F。2025年公司营收33.68亿元，同比增长71.80%。",
      "source_name": "Octopus News Feed",
      "source_url": "https://www.icloudnews.net/a/116925.html",
      "recommendation": {
        "score": 80,
        "matched_terms": ["半导体", "增长", "发布"],
        "reasons": [
          "命中关注产业：半导体。",
          "命中偏好标签：增长、发布。",
          "包含事件或关系线索，适合作为简报材料。",
          "带有原文链接，可追溯来源。"
        ]
      }
    }
  ]
}
```

### 4.3 `query_enterprise_supply_chain_context`

保留理由：

资讯推荐和简报不只需要新闻列表，还需要解释某个企业在产业链中的位置。这个工具围绕企业返回关联产品、上下游企业、近期资讯时间线和 `llm_context`，适合作为简报 agent 对重点企业做展开分析。

与任务的适配性：

- 对应“企业专题简报”和“产业链解释”。
- 能把常识图谱骨架和资讯动态结合起来，而不是只返回孤立资讯。
- 能服务推荐后的二次展开，例如用户点开“三星”相关资讯后，agent 可以解释三星关联的产品和近期动态。
- 比通用 `search_news_graph` 更稳定，因为返回结构是企业上下文，而不是任意节点搜索结果。

测试参数：

```json
{
  "entity_name": "三星",
  "canonical_graph_id": "Enterprise:wiki:Q20716",
  "since_hours": 8760,
  "limit": 5
}
```

实际返回节选：

```json
{
  "query": "enterprise_supply_chain_context",
  "enterprise": {
    "id": "NewsEntityProfile:graphiti:graphiti_entity_samsung_group_20260524",
    "name": "三星集团",
    "type": "NewsEntityProfile",
    "canonical_graph_id": "Enterprise:wiki:Q20716"
  },
  "products": [],
  "upstream_enterprises": [],
  "downstream_enterprises": [],
  "llm_context": "围绕三星集团，当前图数据库已整理出以下可用于产业链分析的上下文。\n当前图中还没有足够的上下游、产品或资讯线索，需要继续补充抽取和融合。"
}
```

当前样例中 `products`、`upstream_enterprises` 和 `downstream_enterprises` 为空，原因是过滤掉手工 smoke 资讯后，当前图里可追溯资讯与三星常识骨架之间的产品/上下游关系仍不充分。工具结构已经支持这类返回，后续重点应放在图谱抽取和融合质量上。

### 4.4 `query_entity_news_timeline`

保留理由：

这是实体动态追踪的基础工具。推荐流或简报候选中经常会出现54某个企业、产品或技术，下游 agent 需要进一步查看这个实体最近一段时间的资讯演化，这个工具正好提供实体时间线能力。

与任务的适配性：

- 对应“从一条推荐资讯展开到某个实体近期动态”的场景。
- 支持 `canonical_graph_id`，可以基于常识图谱骨架查询动态资讯。
- 可以作为企业专题简报的补充工具。
- 与 `query_enterprise_supply_chain_context` 不完全重复：后者侧重企业产业链上下文，前者侧重任意实体的资讯时间线。

测试参数：

```json
{
  "canonical_graph_id": "Enterprise:wiki:Q20716",
  "since_hours": 8760,
  "limit": 3
}
```

实际返回节选：

```json
{
  "query": "entity_news_timeline",
  "entity": {
    "canonical_graph_id": "Enterprise:wiki:Q20716"
  },
  "items": [
    {
      "news_id": "Episodic:fusion:graphiti:905190b0-de61-4bd2-b302-0ce0c5223aff",
      "title": "苹果iPhone Ultra将采用三星的M14 OLED和均热板，而iPhone 18 Pro和Pro Max则配备更先进的M16面板",
      "summary": "苹果首款折叠屏设备或定名iPhone Ultra，采用三星M14 OLED面板和专用均热板。",
      "publish_time": "2026-06-01T08:00:00.000000000+00:00",
      "source_name": "Octopus News Feed",
      "source_url": "https://www.icloudnews.net/a/118158.html",
      "entities": [
        {
          "name": "三星",
          "type": "NewsEntityProfile",
          "canonical_graph_id": "Enterprise:wiki:Q20716",
          "match_method": "alias",
          "match_score": 0.95
        }
      ]
    }
  ]
}
```

### 4.5 `query_news_by_source_industry`

保留理由：

推荐和简报最终需要可追溯证据。这个工具按时间、信息源和产业查询资讯明细，并返回 `summary` 和完整原文 `content`。它不是主推荐入口，而是事实查证入口。

与任务的适配性：

- 对应“简报 agent 需要查看原文依据”的场景。
- 能按来源过滤，适合排查某个采集源的数据质量。
- 能返回 `content`，弥补推荐工具只返回摘要和片段的不足。
- 比 `query_latest_news` 更适合查证，因为它支持明确的信息源和产业过滤，并返回原文。

测试参数：

```json
{
  "start_time": "2026-05-01T00:00:00+00:00",
  "end_time": "2026-06-30T00:00:00+00:00",
  "source_name": "Octopus",
  "industry": "AI",
  "limit": 2
}
```

实际返回节选：

```json
{
  "query": "news_by_source_industry",
  "filters": {
    "source_name": "Octopus",
    "industry": "AI"
  },
  "items": [
    {
      "news_id": "Episodic:fusion:graphiti:e4590d35-306a-4942-b883-d1d36d1443b0",
      "title": "谷歌首款AI眼镜即将呼之欲出，微美全息(WIMI.US)扎实推进AI+AR生态落地",
      "summary": "开云集团将在2027年与谷歌合作推出古驰品牌智能眼镜，首款AI眼镜将与依视路陆逊梯卡竞争。",
      "content": "开云集团将在2027年与谷歌合作推出古驰品牌智能眼镜，首款AI眼镜将与依视路陆逊梯卡竞争，后者正与Meta合作生产雷朋智能眼镜。",
      "publish_time": "2026-05-06T08:00:00.000000000+00:00",
      "source_name": "Octopus News Feed",
      "source_url": "https://www.icloudnews.net/a/116875.html"
    }
  ]
}
```

