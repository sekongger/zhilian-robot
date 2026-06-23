# 智链平台架构梳理：定位、链路、输入输出与待改进项

更新时间：2026-03-18

## 1. 当前真实架构全景

### 1.1 四层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  产品层（五板块 UI）                                              │
│  整体概况 │ 数据汇聚 │ 知识计算 │ 网链分析 │ 智能服务              │
├─────────────────────────────────────────────────────────────────┤
│  业务控制层（OpenKS）                                             │
│  模块注册 │ schema-as-code │ 依赖编排 │ Run/Artifact/Release 聚合 │
├─────────────────────────────────────────────────────────────────┤
│  执行编排层（KAG）                                                │
│  SPGSchemaMarkLang │ builder submit │ solver/retrieval 框架       │
├─────────────────────────────────────────────────────────────────┤
│  语义服务层（OpenSPG）                                            │
│  schema/project 主存 │ graph upsert │ search │ reason 服务        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 当前数据存储实况

| 存储 | 当前用途 | 写入方 |
|---|---|---|
| OpenSPG (Neo4j/MySQL) | schema 主存 + 正式图谱 | KAG schema commit + graph_materializer upsert |
| MongoDB `crawled_articles` | 原始采集资讯 | rss_ingest |
| MongoDB `kg_input_queue` | NLP 处理后待构建队列 | news pipeline (Celery) |
| MongoDB `entity_instances` | openks_direct 链路写入的实体 | NewsKgBuilder (openks_direct) |
| MongoDB `inc_statement` | openks_direct 链路写入的陈述 | NewsKgBuilder (openks_direct) |
| MongoDB `inc_context` | openks_direct 链路写入的上下文 | NewsKgBuilder (openks_direct) |
| MongoDB `knowledge_runs` | 运行记录 | 两条链路都写 |
| MongoDB `knowledge_artifacts` | 产物版本 | 两条链路都写 |
| MongoDB `service_releases` | 发布版本 | knowledge_runtime_routes |
| JSONL 批次文件 | bridge 导出的标准化资讯 | BridgeRunner |

## 2. 问题诊断：当前存在的杂糅与不清晰

### 2.1 数据汇聚层混入了知识层数据

当前 `platform_overview_routes.py:103-129` 的 `_build_data_elements_summary()` 在数据汇聚卡片里展示了 `entities` 和 `statements` 计数：

```python
# platform_overview_routes.py:114-115 — 问题所在
"entities": ((news.get("knowledge_layer") or {}).get("entities") or 0),
"statements": ((news.get("knowledge_layer") or {}).get("statements") or 0),
```

这些数据来自 `document_pipeline_routes.py:240-243`，读的是 MongoDB 的 `entity_instances` 和 `inc_statement` 集合。

问题：
- `entity_instances` / `inc_statement` 是 openks_direct 链路的产物，属于知识计算层的输出
- 在 kag_openspg 主链下，本体数据（实体、关系）应该由 OpenSPG 管理，存在 OpenSPG 的 Neo4j 里
- 数据汇聚层不应该展示知识层的实体和陈述计数，它的职责是展示"资源接入了多少、治理了多少、质量如何"

### 2.2 两条链路的数据产物混在一起

当前系统同时存在两条链路的数据产物：

| 链路 | 实体/关系存储 | 当前状态 |
|---|---|---|
| `openks_direct` | MongoDB `entity_instances` / `inc_statement` / `inc_context` + 自有 Neo4j | 旧链路，仍被 graph_routes 和 open_api_routes 消费 |
| `kag_openspg` | OpenSPG 的 Neo4j（通过 graph_materializer upsert） | 新主链，但下游消费还没完全切过来 |

`graph_routes.py:25-74` 的 `_build_artifact_scoped_graph()` 仍然从 MongoDB 的 `entity_instances` / `inc_statement` 读数据来构图。这在 kag_openspg 链路下是不对的——kag_openspg 的图数据写到了 OpenSPG 的 Neo4j 里，不在这些 MongoDB 集合中。

### 2.3 知识分层逻辑不清晰

当前五板块的数据边界没有严格分层：

```
数据汇聚 → 知识计算 → 网链分析 → 智能服务
   ↑            ↑           ↑          ↑
  混入了      输入不明确    消费源不统一  消费源不统一
  知识层数据
```

应该是：

```
数据汇聚                    知识计算                    网链分析 / 智能服务
├─ 输入: RSS/API/人工导入    ├─ 输入: 标准化资讯批次       ├─ 输入: artifact_id
├─ 处理: 采集、清洗、标准化   │  (JSONL 或 kg_input_queue)  │  或 release_id
├─ 输出: 标准化资讯文档       ├─ 处理: schema → 抽取 →      ├─ 消费: OpenSPG graph
│  (crawled_articles)       │  构建 → 物化                │  API 查询
│                           ├─ 输出: OpenSPG 图谱 +        │
│                           │  KnowledgeArtifact           │
│                           │  + ServiceRelease            │
```

### 2.4 OpenKS 模块的输入输出没有明确定义

当前 OpenKS 的 19 个 KG 模块中，只有 `news_kg` 有真实实现。但即使是 `news_kg`，它的输入输出也没有在代码层面显式定义：

- `NewsKgBuilder.build()` 的输入是 `records: Iterable[Dict]`，但这个 Dict 的 schema 没有定义
- 输出写到了 MongoDB 的 `entity_instances` / `inc_statement`（openks_direct 链路），但在 kag_openspg 链路下应该写到 OpenSPG
- `BaseBuilder.build()` 的接口太薄，没有 `RuntimeProfile` / `GraphRuntime` / `ArtifactStore` 抽象

## 3. kag_openspg 主链的完整代码衔接

### 3.1 六步流水线代码路径

以下是 kag_openspg 主链从前端触发到最终结果的完整代码调用链：

```
前端 WorkflowWorkbenchPage.jsx
  → POST /api/v1/workflow/news/run
    → backend/app/api/workflow_routes.py:70  (转发)
      → backend/app/openspg_demo/routes.py:2694  run_news_workflow()
        → routes.py:2333  _execute_workflow_job()  (后台线程执行)
```

#### Step 1: 建模 — OpenKS schema → KAG → OpenSPG

```
_execute_workflow_job():2353-2366
  → backend/app/services/openks_schema_runtime_service.py:121
    apply_openks_news_kg_schema()
      → supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py:45
        compile_module_schema("news_kg", namespace=...)
          → 加载 openks/kg/fact/news_kg 模块
          → 调用 NewsKgSchema().describe() 获取 {entities, relations, fields}
          → 编译为 KAG .schema DSL 文本
      → kag_schema_adapter.py:84
        export_module_schema_to_kag_project()
          → 写 .schema 文件到 modules/kag/kag/examples/OpenKSNews/schema/
          → 实例化 modules/kag/knext/schema/marklang/schema_ml.py:66 SPGSchemaMarkLang
          → 调用 sync_schema() → diff_and_sync()
            → HTTP 请求 OpenSPG server (http://OPENSPG_BASE_URL:8887)
            → OpenSPG 执行 schema alter
```

输入：OpenKS news_kg 模块的 Python describe() 定义
输出：OpenSPG server 中的正式 schema（持久化在 OpenSPG 的 MySQL 中）
关键文件：
- `backend/app/services/openks_schema_runtime_service.py`
- `supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py`
- `modules/kag/knext/schema/marklang/schema_ml.py`

#### Step 2: 采集 — RSS 拉取资讯

```
_execute_workflow_job():2400-2415
  → backend/app/openspg_demo/rss_ingest.py
    pull_rss_articles_to_mongo()
      → 拉取 RSS feeds
      → 写入 MongoDB crawled_articles
```

输入：RSS feed 配置
输出：MongoDB `crawled_articles` 集合中的原始资讯文档
关键文件：`backend/app/openspg_demo/rss_ingest.py`

#### Step 3: 处理 — 读取并标准化

```
_execute_workflow_job():2417-2434
  → routes.py _read_news_rows()
    → 从 MongoDB crawled_articles 读取资讯
    → 标准化字段（title, content, summary, source_url, publish_time 等）
```

输入：MongoDB `crawled_articles`
输出：内存中的标准化资讯行列表
关键文件：`backend/app/openspg_demo/routes.py`

#### Step 4: 抽取 — Bridge 导出 JSONL 批次

```
_execute_workflow_job():2436-2468
  → backend/app/openspg_demo/bridge_runner.py:50 BridgeRunner
    bridge_runner.run_export(rows, limit=..., force_full=...)
      → 增量过滤（基于 cursor.last_seen_time）
      → 标准化每条记录
      → 写入 JSONL 批次文件到 backend/data/openspg_demo/batches/{run_id}.jsonl
      → 更新 bridge_state.json 游标
```

输入：标准化资讯行列表
输出：JSONL 批次文件（每行一条标准化资讯 JSON）
关键文件：`backend/app/openspg_demo/bridge_runner.py`

#### Step 5: 执行 — Builder 提交 + 图物化

这一步有两个并行动作：

**5a. Builder 提交到 OpenSPG**

```
_execute_workflow_job():2544-2561
  → backend/app/openspg_demo/builder_import_command.py
    build_builder_envs_for_run() — 构建环境变量
    build_real_import_command() — 构建导入命令
  → backend/app/openspg_demo/openspg_client.py:206
    submit_openspg_builder_job()
      → POST {OPENSPG_BASE_URL}/public/v1/builder/kag/submit
        body: {projectId, command, workerNum, envs}
```

**5b. 图物化到 OpenSPG**

```
_execute_workflow_job():2579-2583
  → backend/app/openspg_demo/graph_materializer.py:494
    async_materialize_bridge_batch()
      → 读取 JSONL 批次文件
      → 获取 project namespace（GET /public/v1/project）
      → _build_vertices_and_edges() — 从资讯中抽取 Company/Product/Technology/Document/Chunk/KnowledgePoint
      → _upsert_vertices() — POST {OPENSPG_BASE_URL}/public/v1/graph/upsertVertex
      → _upsert_edges() — POST {OPENSPG_BASE_URL}/public/v1/graph/upsertEdge
```

**5c. 注册运行时绑定**

```
_execute_workflow_job():2591-2598
  → backend/app/services/knowledge_runtime_service.py:92
    register_workflow_runtime_binding()
      → 写入 MongoDB knowledge_runs（run_id, status, artifact_ref, ...）
      → 写入 MongoDB knowledge_artifacts（artifact_id, version, entity_count, ...）
```

输入：JSONL 批次文件 + bridge_run 元数据
输出：
- OpenSPG 图谱中的 vertices 和 edges
- MongoDB `knowledge_runs` 中的运行记录
- MongoDB `knowledge_artifacts` 中的产物版本
关键文件：
- `backend/app/openspg_demo/graph_materializer.py`（核心：调用 OpenSPG Graph API）
- `backend/app/openspg_demo/openspg_client.py`（核心：调用 OpenSPG Builder API）
- `backend/app/services/knowledge_runtime_service.py`

#### Step 6: 应用 — 头条快照

```
_execute_workflow_job():2624-2647
  → backend/app/openspg_demo/headlines_service.py
    build_headlines_from_news()
      → 从标准化资讯中提取头条
      → 返回 headlines + stats
```

输入：标准化资讯行列表
输出：头条快照（用于智能服务的样本展示）
关键文件：`backend/app/openspg_demo/headlines_service.py`

### 3.2 kag_openspg 链路中真正调用 KAG/OpenSPG 的代码

| 调用点 | 文件 | 调用的 KAG/OpenSPG 能力 |
|---|---|---|
| schema 编译 | `kag_schema_adapter.py:45` | `compile_module_schema()` — OpenKS describe → KAG .schema DSL |
| schema 提交 | `kag_schema_adapter.py:102-108` | `SPGSchemaMarkLang.sync_schema()` — KAG 的 schema diff + commit 到 OpenSPG |
| builder 提交 | `openspg_client.py:232` | `POST /public/v1/builder/kag/submit` — OpenSPG Builder API |
| 图物化 vertex | `graph_materializer.py:251-256` | `POST /public/v1/graph/upsertVertex` — OpenSPG Graph API |
| 图物化 edge | `graph_materializer.py:259-264` | `POST /public/v1/graph/upsertEdge` — OpenSPG Graph API |
| 获取 namespace | `graph_materializer.py:212-238` | `GET /public/v1/project` — OpenSPG Project API |
| schema 查询 | `openspg_client.py:269-285` | `GET /v1/schemas/getSchemaScript` — OpenSPG Schema API |
| 健康检查 | `openspg_client.py:155-203` | schema/graph/search/builder 四项检查 |

### 3.3 最终结果在哪里

| 结果类型 | 存储位置 | 消费方 |
|---|---|---|
| 正式图谱（vertices/edges） | OpenSPG 的 Neo4j | 网链分析（应通过 OpenSPG search/graph API 查询） |
| schema 定义 | OpenSPG 的 MySQL | KAG/OpenSPG 内部 |
| KnowledgeRun | MongoDB `knowledge_runs` | 知识计算页展示 |
| KnowledgeArtifact | MongoDB `knowledge_artifacts` | 知识计算页展示 + 跨板块跳转 |
| ServiceRelease | MongoDB `service_releases` | 智能服务消费 |
| JSONL 批次文件 | `backend/data/openspg_demo/batches/` | graph_materializer 读取 + graph_routes fallback |

## 4. 五板块应有的清晰定位与输入输出

### 4.1 数据汇聚

定位：资源接入、清洗、标准化、质量管理。不涉及知识抽取和本体管理。

```
输入：RSS feeds / API / 人工导入
处理：采集 → 去重 → 清洗 → 标准化 → 质量检查
输出：标准化资讯文档（MongoDB crawled_articles）
      + 资源元数据（接入源、数量、质量指标）
```

页面应展示：
- 资源类型卡片（资讯、研报、企业、政策）
- 每类资源的：接入源数量、原始文档数、标准化文档数、质量指标
- 不应展示：实体数、陈述数（这些属于知识计算层的输出）

待改进：
- `platform_overview_routes.py:114-115` 中的 `entities` 和 `statements` 字段需要去掉
- `document_pipeline_routes.py` 的 `knowledge_layer` 统计不应出现在数据汇聚视图中
- 数据汇聚的输出对象应该是 `Resource`（resource_key + doc_version），作为知识计算的正式输入

### 4.2 知识计算（OpenKS 知识建模与计算）

定位：知识定义、抽取、融合、构建、版本管理。

```
输入：数据汇聚的标准化资讯批次
      （当前是 JSONL 批次文件 或 kg_input_queue）
处理：
  1. 建模：OpenKS schema → KAG .schema → OpenSPG schema commit
  2. 抽取：从标准化资讯中抽取实体和关系
  3. 融合：实体对齐、去重、规范化
  4. 构建：写入 OpenSPG 图谱（graph upsert）
  5. 版本化：生成 KnowledgeRun → KnowledgeArtifact
输出：
  - OpenSPG 中的正式图谱
  - KnowledgeArtifact（artifact_id + version）→ 交给网链分析
  - ServiceRelease（release_id + version）→ 交给智能服务
```

页面应展示：
- OpenKS 定义层（当前只展示 base_kg + news_kg）
- 最新 workflow 运行状态
- 最新 Run / Artifact / Release
- 跳转入口：进入 Workflow 工作台、进入网链分析、进入智能服务

知识分层逻辑：
```
知识抽取（从文档中提取实体、关系、事件）
  → 知识融合（实体对齐、去重、规范化）
    → 知识推理（链式认知、趋势判断、风险预警 — 当前未实现）
      → 知识服务（问答、API、推荐）
```

当前只实现了"知识抽取 → 知识服务"，中间的融合和推理还是空的。

### 4.3 网链分析

定位：基于知识产物的关系探索、热度分析、时序洞察。

```
输入：artifact_id（从知识计算页跳转带入）
处理：查询 OpenSPG 图谱中该 artifact 范围内的实体和关系
输出：图谱可视化、热度趋势、时序分析
```

待改进：
- 当前 `graph_routes.py:25-74` 的 `_build_artifact_scoped_graph()` 从 MongoDB `entity_instances` / `inc_statement` 读数据，这是 openks_direct 链路的产物
- 在 kag_openspg 主链下，应该改为通过 OpenSPG 的 search/graph API 查询
- 当前的 fallback 路径 `_build_artifact_scoped_graph_from_batch()` 从 JSONL 批次文件读取，这是临时方案

### 4.4 智能服务

定位：基于发布版本的问答、API 输出。

```
输入：release_id + release_version（从知识计算页跳转带入）
处理：
  - 解析 release → artifact → 确定知识范围
  - 问答时从该范围内检索结构化陈述
  - 生成带证据链的回答
输出：问答结果 + 证据追踪 + Open API
```

待改进：
- 当前 `open_api_routes.py` 的结构化陈述检索仍然从 MongoDB `inc_statement` 读取
- 在 kag_openspg 主链下，应该改为通过 OpenSPG 的 search API 或 KAG 的 retrieval/reasoning 框架

## 5. OpenKS 架构代码梳理与多人协作

### 5.1 OpenKS 代码结构

```
supxmind/supxmind-openks/openks/
├── common/                          # 公共层（平台共建）
│   ├── base/core.py                 # BaseSchema, BaseBuilder, BaseReasoner, BaseSolver
│   ├── adapters/
│   │   ├── mongodb_adapter.py       # MongoKnowledgeAdapter（读写 MongoDB 集合）
│   │   └── neo4j_adapter.py         # Neo4jGraphAdapter（读写自有 Neo4j）
│   ├── interop/
│   │   └── kag_schema_adapter.py    # OpenKS → KAG .schema 编译 + sync_schema()
│   └── registry/
│       └── discovery.py             # 模块发现：扫描 kg/*/*/module.toml
├── kg/                              # KG 模块目录
│   ├── fact/                        # 事实类
│   │   ├── base_kg/                 # 基础概念词典（公共定义）
│   │   ├── news_kg/                 # 资讯知识库（唯一真实实现）
│   │   │   ├── module.toml          # 模块元数据
│   │   │   ├── schema/              # NewsKgSchema.describe()
│   │   │   ├── builder/             # NewsKgBuilder.build()
│   │   │   ├── reasoner/            # NewsKgReasoner（空壳）
│   │   │   └── solver/              # NewsKgSolver.solve()
│   │   ├── report_kg/               # 研报（脚手架）
│   │   ├── enterprise_kg/           # 企业（脚手架）
│   │   └── ...                      # 其余 7 个事实类模块（脚手架）
│   ├── cognition/                   # 认知类（全部脚手架）
│   │   ├── industry_chain/
│   │   ├── supply_chain/
│   │   ├── innovation_chain/
│   │   └── capital_chain/
│   └── decision/                    # 决策类（全部脚手架）
│       ├── hotspot/
│       ├── trend/
│       ├── risk_alert/
│       ├── recommendation/
│       └── technology_foresight/
├── cross/                           # 跨 KG 调度层（空壳）
└── entry/
    └── api/service.py               # 统一入口：build_news_kg(), get_news_kg_status(), query_news_kg()
```

### 5.2 模块注册机制

每个 KG 模块通过 `module.toml` 注册：

```toml
name = "news_kg"
title = "资讯知识库"
stage = "fact"
owner = "楼彦炜"
path = "openks/kg/fact/news_kg"
summary = "面向资讯抽取事件、实体、关系和热点事实。"
status = "active"
dependencies = ["base_kg"]
```

`discovery.py` 在启动时扫描 `openks/kg/*/*/module.toml`，构建模块目录。

### 5.3 每个模块的标准四件套

每个 KG 模块应包含：

| 组件 | 基类 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| Schema | `BaseSchema` | 定义本体结构 | 无 | `{entities, relations, fields}` |
| Builder | `BaseBuilder` | 从数据构建知识 | `records: Iterable[Dict]` | 写入图谱 + 返回统计 |
| Reasoner | `BaseReasoner` | 知识推理 | `facts: Iterable[Dict]` | 推理结果 |
| Solver | `BaseSolver` | 知识查询 | `query: Dict` | 查询结果 |

当前问题：
- `BaseBuilder.build()` 的输入 `records` 没有 schema 定义
- 没有 `RuntimeProfile` 参数，builder 不知道该写到哪里
- 没有 `ArtifactStore` 抽象，产物版本管理散落在 builder 内部

### 5.4 多人协作模式

当前设计已经支持多人协作的基本框架：

```
每个 KG 模块 = 一个独立目录 + module.toml + 四件套
```

协作规则：
1. 每个模块有明确的 `owner`（在 module.toml 中定义）
2. 模块之间通过 `dependencies` 声明依赖关系
3. 公共层（common）由平台共建
4. 跨 KG 调度层（cross）负责模块间的数据流转

要让多人协作真正可行，还需要：
- 明确每个模块的输入数据 schema（不是 KG schema，是"你的 builder 期望接收什么格式的数据"）
- 明确每个模块的输出产物格式（写到 OpenSPG 的哪些 type 下）
- 提供模块开发脚手架命令（类似 `openks new-module report_kg --stage fact --owner 李奕君`）
- 提供本地测试能力（不依赖 OpenSPG server 也能验证 schema 和 builder 逻辑）

## 6. 具体待改进项清单

### 6.1 数据汇聚层：去掉实体和陈述

需要改的文件：

| 文件 | 改动 |
|---|---|
| `backend/app/api/platform_overview_routes.py:114-115,123-124` | 去掉 `entities` 和 `statements` 字段 |
| `frontend/src/pages/platformOverviewConfig.mjs` | 数据汇聚 hub 的 spotlights 不再提及实体/陈述 |
| `backend/app/api/resource_hub_routes.py:123-124` | 同上 |

数据汇聚卡片应该只展示：
- 原始文档数（raw_documents）
- 标准化文档数（resource_documents）
- 数据源数量
- 质量指标

### 6.2 知识计算层：明确输入来源

当前知识计算的输入有两个来源，需要统一：

| 来源 | 当前用途 | 目标 |
|---|---|---|
| `kg_input_queue`（MongoDB） | openks_direct 链路的 NLP 处理结果 | 逐步废弃，或作为 openks_direct 兼容 |
| JSONL 批次文件 | kag_openspg 链路的 bridge 导出 | 主链输入 |

在 kag_openspg 主链下，知识计算的输入应该是数据汇聚层产出的标准化资讯（`crawled_articles`），经过 bridge 导出为 JSONL 批次后，由 graph_materializer 抽取实体/关系并写入 OpenSPG。

### 6.3 网链分析：切换到 OpenSPG 查询

当前 `graph_routes.py` 的 artifact 范围图查询从 MongoDB 读数据，需要改为：

```python
# 当前（从 MongoDB 读 openks_direct 产物）
entity_rows = mongo.find_many("entity_instances", query={"artifact_id": artifact_id})
statement_rows = mongo.find_many("inc_statement", query={"artifact_id": artifact_id})

# 目标（从 OpenSPG 查询）
# 通过 OpenSPG search API 或 graph API 查询该 artifact 范围内的实体和关系
```

### 6.4 智能服务：切换到 OpenSPG 检索

当前 `open_api_routes.py` 的结构化陈述检索从 MongoDB `inc_statement` 读取，需要改为通过 KAG 的 retrieval 框架或 OpenSPG 的 search API。

### 6.5 OpenKS 模块输入输出定义

每个模块需要在 `module.toml` 或代码中显式定义：

```toml
[input]
source = "crawled_articles"          # 输入数据来源
format = "jsonl"                     # 输入格式
required_fields = ["title", "content", "source_url", "publish_time"]

[output]
target = "openspg"                   # 输出目标
entity_types = ["Company", "Product", "Technology", "Document", "Chunk", "KnowledgePoint"]
relation_types = ["mentionsCompany", "mentionsProduct", "mentionsTech"]
```

### 6.6 页面展示清理

| 页面 | 当前问题 | 改进方向 |
|---|---|---|
| 数据汇聚 | 混入了实体/陈述计数 | 只展示资源指标 |
| 知识计算 | 同时展示两条链路的状态 | 只展示 kag_openspg 主链 |
| 网链分析 | 从 MongoDB 读旧数据 | 改为从 OpenSPG 查询 |
| 智能服务 | 从 MongoDB 读旧数据 | 改为从 KAG/OpenSPG 检索 |
| Workflow | 步骤描述已基本正确 | 确保文案与 kag_openspg 一致 |

## 7. 知识分层与工具链定义

### 7.1 知识生产链路的四个阶段

```
知识抽取 → 知识融合 → 知识推理 → 知识服务
```

| 阶段 | 当前实现 | OpenKS 对应工具 | 配置项 | 监控项 |
|---|---|---|---|---|
| 知识抽取 | graph_materializer 的正则抽取 | Builder（每个 KG 模块的 builder） | 抽取规则、实体类型映射、关系映射 | 抽取实体数、关系数、失败率 |
| 知识融合 | canonicalization_service（简单哈希） | 待建：FusionOperator | 对齐规则、去重策略、置信度阈值 | 融合前后实体数、合并率 |
| 知识推理 | 未实现 | Reasoner（每个 KG 模块的 reasoner） | 推理规则、链路模板 | 推理产出数、覆盖率 |
| 知识服务 | open_api_routes + industry_qa_routes | Solver（每个 KG 模块的 solver） | 检索策略、top_k、证据链深度 | 查询延迟、命中率、证据覆盖率 |

### 7.2 需要在平台里配置和监控的内容

配置：
- schema 定义（通过 OpenKS describe() + Workflow 建模步骤）
- 抽取规则（当前硬编码在 graph_materializer 中，应抽象为可配置）
- runtime profile（kag_openspg / openks_direct）
- 采集源配置（RSS feeds）

监控：
- 每次 Run 的状态（queued → running → success/failed）
- 每次 Run 的产出统计（vertices, edges, entity_count, statement_count）
- Artifact 版本历史
- Release 状态流（draft → review_pending → released → active → superseded）
- OpenSPG server 健康状态

## 8. 总结

当前架构的核心链路（kag_openspg）已经跑通，但存在以下需要收敛的问题：

1. 数据汇聚层混入了知识层数据（实体/陈述计数），需要去掉
2. 下游消费（网链分析、智能服务）还在从 MongoDB 旧集合读数据，需要切到 OpenSPG
3. OpenKS 模块的输入输出没有显式定义，多人协作缺少契约
4. 知识融合和知识推理阶段还是空的，当前是"抽取 → 直接服务"
5. 两条链路（openks_direct / kag_openspg）的数据产物混在一起，需要明确边界

优先级建议：
1. 先清理数据汇聚页面（去掉实体/陈述）— 改动小，效果明显
2. 定义 OpenKS 模块的输入输出契约 — 多人协作的前提
3. 网链分析切到 OpenSPG 查询 — 让主链真正闭环
4. 智能服务切到 KAG/OpenSPG 检索 — 让主链真正闭环
5. 补知识融合能力 — 提升知识质量
