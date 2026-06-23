# 新资讯图谱 Pipeline 运行手册

## 目标

本 pipeline 用于把产业资讯写入 Graphiti 动态资讯图谱，并把资讯实体链接到常识锚点。它不再把资讯字段 merge 回常识图谱，也不再生成旧的 big graph fusion batch 作为主结果。

主入口：

```bash
python backend/scripts/run_news_graph_pipeline.py
```

## 标准小批量运行

先确认 Graphiti API、Graphiti Neo4j、常识 Neo4j 均已启动，并且环境变量指向正确数据库。

建议显式区分两类 Neo4j 连接：

```bash
export COMMON_GRAPH_NEO4J_URI=bolt://localhost:7687
export COMMON_GRAPH_NEO4J_USER=neo4j
export COMMON_GRAPH_NEO4J_PASSWORD=password123

export GRAPHITI_NEWS_NEO4J_URI=bolt://localhost:7687
export GRAPHITI_NEWS_NEO4J_USER=neo4j
export GRAPHITI_NEWS_NEO4J_PASSWORD=password123
```

如果两张图暂时部署在同一个 Neo4j 实例中，可以让两组变量指向同一地址；如果后续分库部署，则分别指向常识图谱库和 Graphiti 资讯图谱库。

```bash
PYTHONPATH=backend python backend/scripts/run_news_graph_pipeline.py \
  --run-crawler \
  --ingest \
  --since-hours 24 \
  --max-items-per-source 5 \
  --process-limit 10 \
  --sync-anchors \
  --link-entities \
  --anchor-limit 5000 \
  --entity-limit 1000
```

运行后会在 `tmp/news_graph_pipeline_runs/<run_id>/run_report.json` 写出报告，包含 crawler summary、anchor 同步统计、实体链接统计和 warnings。

## 只对已有批次做锚点联通

如果资讯已经通过 crawler 写入 Graphiti，可以直接指定 `group_id`：

```bash
PYTHONPATH=backend python backend/scripts/run_news_graph_pipeline.py \
  --group-id crawl_202606210001 \
  --sync-anchors \
  --link-entities
```

## 清理指定资讯批次

只清理 Graphiti 中指定 `group_id` 的资讯 episode，不清理常识图谱：

```bash
PYTHONPATH=backend python backend/scripts/run_news_graph_pipeline.py \
  --group-id crawl_202606210001 \
  --clear-news-group
```

## Neo4j Browser 验证查询

查看锚点：

```cypher
MATCH (a:CommonSenseAnchor)
RETURN a.name, a.anchor_id, a.type_name
LIMIT 20;
```

查看资讯实体到锚点的链接：

```cypher
MATCH p=(ep:Episodic)-[:MENTIONS|mentions]-(e)-[:refersTo|candidateRefersTo]->(a:CommonSenseAnchor)
RETURN p
LIMIT 50;
```

查看某个批次链接统计：

```cypher
MATCH (ep:Episodic)-[:MENTIONS|mentions]-(e)
WHERE ep.group_id = 'crawl_202606210001' OR ep.fusion_batch_id = 'crawl_202606210001'
OPTIONAL MATCH (e)-[r:refersTo|candidateRefersTo]->(a:CommonSenseAnchor)
RETURN type(r) AS link_type, count(*) AS count
ORDER BY count DESC;
```

## MCP 验证

启动 MCP：

```bash
PYTHONPATH=backend python backend/scripts/run_news_graph_mcp.py --transport sse --port 3010
```

下游 Agent 可继续使用既有工具名：

- `query_entity_news_timeline`
- `query_enterprise_supply_chain_context`
- `query_news_by_source_industry`
- `query_recommended_news_candidates`
- `query_subscription_news_feed`

这些工具现在优先读取 Graphiti 资讯图谱中的 `CommonSenseAnchor` 链接信息，并在返回中保留原文链接、摘要、实体、事件、关系、匹配分和匹配方式。
