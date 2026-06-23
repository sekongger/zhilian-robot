# 产业头条与 OpenKS 一体化详细设计

更新时间：2026-03-21

> 本文档是 [docs/2026-03-21-zju-ai-center-headlines-enterprise-openks-solution.md](/Users/youfang/Documents/zhilian-robot/docs/2026-03-21-zju-ai-center-headlines-enterprise-openks-solution.md) 的详细设计版。
>
> 目标是把第一阶段可落地内容拆成三部分：
>
> 1. 前台页面结构
> 2. OpenKS 工作台页面结构
> 3. DataHub/OpenKS 接口定义

---

## 1. 第一阶段范围

第一阶段只实现：

- 头条资讯数据接入
- DataHub 模拟接入与批次生成
- OpenKS `news_kg + event_kg + industry_network` 最小链路
- OpenSPG/图数据库落图
- 前台与 OpenKS 工作台展示

第一阶段不实现：

- 企业库真实接入
- 产业链图谱完整自动抽取
- 四链完整专题
- Graphiti 真实服务调用

### 1.1 当前实现状态

已实现：

- `/platform` 前台展示页
- `/openks` 与 `/openks/workbench` 工作台入口
- OpenKS 工作台真实接入模块、构建任务和图谱结果接口
- DataHub mock 头条接口
- DataHub mock 企业占位接口
- OpenKS `build-jobs` 最小骨架
- OpenKS 图谱结果接口：
  - `graph/summary`
  - `graph/sample`
  - `graph/evidence`
- `event_kg / industry_network` 模块骨架

待实现：

- build-jobs 串真实 manifest 和真实构建链
- Graphiti 真实服务接入
- 企业库真实接入
- 产业网大图完整真实构建
- 产业链图谱真实抽取

---

## 2. 页面总体职责划分

### 2.1 前台页面职责

前台页面负责：

- 展示业务结果
- 展示链路状态
- 展示关键指标
- 提供跳转入口

前台页面不负责：

- 手工提交构建任务
- 手工编辑 schema
- 调试 OpenSPG 原生参数

### 2.2 OpenKS 工作台职责

OpenKS 工作台负责：

- 查看 schema
- 查看批次和 build job
- 查看 run / artifact / release
- 查看图谱结果和样例子图
- 查看错误与重试建议

OpenKS 工作台不负责：

- 承担 DataHub 的资源接入页面
- 替代前台成果展示页面

---

## 3. 前台页面详细设计

### 3.1 路由建议

继续保留现有：

- `/platform?tab=overview`
- `/platform?tab=data-hub`
- `/platform?tab=knowledge-computing`
- `/platform?tab=chain-analysis`
- `/platform?tab=intelligent-service`

新增跳转目标：

- `/openks`
- `/openks/workbench`

当前实现已经调整为：

- `OpenKS` 使用独立布局和独立导航
- 不再复用中试平台主导航栏
- 前台通过“OpenKS 门户地址”跳转
- 后续只需要把 `OpenKS` 门户地址切到独立端口或独立域名即可

### 3.2 整体概况页

#### 模块

1. 链路总览卡
2. 第一阶段建设范围卡
3. 最新批次 / 最新构建 / 最新产物卡
4. 快捷跳转入口

#### 展示字段

- 最新头条批次 `batch_id`
- 最新 build job `job_id`
- 最新 run `run_id`
- 最新 artifact `artifact_id`
- 最新 release `release_id`
- 最新图谱实体数 / 边数

#### 交互

- “进入 DataHub 摘要”
- “进入 OpenKS 工作台”
- “查看图谱结果”

### 3.3 数据汇聚页

#### 模块

1. 数据源接入状态
2. 头条批次列表
3. 标准化处理摘要
4. DataHub -> OpenKS 调用状态

#### 第一阶段展示对象

- 产业头条：已接入（RSSHub）
- 企业库：后续接入

#### 头条批次字段

- `batch_id`
- `source`
- `raw_count`
- `normalized_count`
- `status`
- `created_at`
- `last_push_job_id`

#### 调用状态字段

- `job_id`
- `target_modules`
- `runtime_profile`
- `submit_status`
- `submitted_at`

#### 交互

- 查看批次详情
- 跳转 OpenKS 工作台并带 `job_id`

### 3.4 知识计算页

#### 模块

1. Schema 摘要
2. KG 模块状态
3. 构建任务摘要
4. 产业网大图结果摘要
5. 跳转 OpenKS 工作台

#### Schema 摘要

展示：

- `IncCore.schema`
- 第一阶段启用子集
- 本次启用实体类型数
- 本次启用关系类型数

#### KG 模块状态

第一阶段展示：

- `base_kg`
- `news_kg`
- `event_kg`
- `industry_network`
- `enterprise_kg`（后续接入）

字段：

- `module_name`
- `status`
- `schema_synced`
- `last_run_id`
- `entity_count`
- `statement_count`

#### 构建任务摘要

展示：

- 最新 build job
- 最新 run
- 最新 artifact
- 最新 release
- 最近错误信息

### 3.5 网链分析页

第一阶段建议不做完整产业链图谱，只做“产业网大图样例视图 + 预留产业链图谱入口”。

#### 模块

1. 产业网大图样例子图
2. 头条事件关系子图
3. 产业链图谱入口占位

#### 字段

- `artifact_id`
- `sample_companies`
- `sample_events`
- `sample_relations`

### 3.6 智能服务页

第一阶段主要展示：

1. 头条推送能力占位
2. 问答上下文来源摘要
3. OpenKS release 消费状态

#### 字段

- `release_id`
- `release_status`
- `headline_ready`
- `qa_context_ready`

---

## 4. OpenKS 工作台详细设计

### 4.1 路由建议

新增：

- `/openks/workbench`

可选子路由：

- `/openks/workbench?tab=schema`
- `/openks/workbench?tab=modules`
- `/openks/workbench?tab=jobs`
- `/openks/workbench?tab=results`

第一阶段先用一个页面 + tabs 即可。

### 4.2 页面结构

```text
OpenKS 工作台
  概览头部
  Tabs
    Schema
    KG 模块
    Build Jobs
    图谱结果
```

### 4.3 Schema Tab

#### 内容

- `IncCore.schema` 基础摘要
- 第一阶段启用 schema 子集
- `news_kg` schema
- `event_kg` schema
- `industry_network` schema

#### 展示字段

- `entity_types`
- `relation_types`
- `version`
- `last_synced_at`
- `project_id`
- `namespace`

### 4.4 KG 模块 Tab

#### 模块卡片

- `base_kg`
- `news_kg`
- `event_kg`
- `industry_network`
- `enterprise_kg`（后续接入）

#### 每张卡片字段

- `title`
- `status`
- `owner`
- `dependencies`
- `has_schema`
- `has_builder`
- `has_reasoner`
- `has_solver`
- `last_run_id`

### 4.5 Build Jobs Tab

#### 列表字段

- `job_id`
- `batch_id`
- `resource_pool_id`
- `module_names`
- `runtime_profile`
- `status`
- `run_id`
- `artifact_id`
- `release_id`
- `created_at`
- `updated_at`

#### 详情字段

- 请求参数
- schema sync 结果
- build 结果
- materialize 结果
- 错误堆栈

### 4.6 图谱结果 Tab

#### 模块

1. 结果统计
2. 样例节点/边
3. 子图预览
4. 证据列表

#### 结果统计字段

- `artifact_id`
- `release_id`
- `vertex_count`
- `edge_count`
- `company_count`
- `event_count`
- `document_count`

#### 样例节点字段

- `type`
- `id`
- `name`
- `source_kg`
- `artifact_id`

#### 样例边字段

- `src`
- `label`
- `dst`
- `confidence`

---

## 5. DataHub 接口定义

### 5.1 头条接入接口

`GET /api/v1/datahub/mock/headlines`

#### 返回字段

- `source`
- `items[]`

#### `items[]` 字段

- `doc_id`
- `title`
- `summary`
- `content`
- `source_name`
- `source_url`
- `publish_time`

### 5.2 企业库接口

`GET /api/v1/datahub/mock/enterprise`

#### 第一阶段返回字段

- `source`
- `enabled`
- `message`
- `sample_fields`

#### `sample_fields`

- `name`
- `official_name`
- `code`
- `industry`
- `region`
- `website`

### 5.3 DataHub 批次接口

`POST /api/v1/datahub/mock/batches/headlines`

#### 请求

```json
{
  "source": "rsshub",
  "limit": 50
}
```

#### 返回

```json
{
  "batch_id": "BATCH_20260321_001",
  "source": "rsshub",
  "raw_count": 50,
  "normalized_count": 48,
  "manifest_uri": "file:///tmp/batch_20260321_001.jsonl",
  "status": "ready"
}
```

---

## 6. OpenKS 接口定义

### 6.1 提交构建任务

`POST /api/v1/openks/build-jobs`

#### 请求字段

- `project_id`
- `namespace`
- `resource_pool_id`
- `batch_id`
- `manifest_uri`
- `source_types`
- `module_names`
- `runtime_profile`
- `graphiti_options`
- `schema_policy`
- `build_options`
- `idempotency_key`

### 6.2 查询构建任务

`GET /api/v1/openks/build-jobs/{job_id}`

#### 返回字段

- `job_id`
- `status`
- `run_id`
- `artifact_id`
- `release_id`
- `graph_stats`
- `steps`

### 6.3 查询模块概览

复用现有：

- `GET /api/v1/openks/modules`
- `GET /api/v1/openks/modules/{name}`
- `GET /api/v1/openks/overview`

### 6.4 查询运行产物

复用现有：

- `GET /api/v1/runs`
- `GET /api/v1/artifacts`
- `GET /api/v1/releases`

### 6.5 图谱结果查询接口

第一阶段建议新增一层业务接口，而不是直接把 Neo4j 查询暴露给前端。

建议新增：

- `GET /api/v1/openks/graph/summary?artifact_id=...`
- `GET /api/v1/openks/graph/sample?artifact_id=...`
- `GET /api/v1/openks/graph/evidence?artifact_id=...`

---

## 7. 存储与对象关系

### 7.1 存储建议

- 图数据：OpenSPG 对接图存层 / Neo4j
- 运行对象：MongoDB
- schema 与配置：文件 + 必要元数据存储

### 7.2 运行对象

继续沿用当前：

- `knowledge_runs`
- `knowledge_artifacts`
- `service_releases`

### 7.3 图数据和页面对象关系

```text
图数据库中的正式图
-> 产业网大图结果
-> artifact
-> 前台摘要展示 / OpenKS 工作台查询
```

产业链图谱在第一阶段仍然是：

- 占位
- 样例抽取
- 非完整生产结果

---

## 8. 第一阶段代码落点建议

### 8.1 前端

建议新增：

- `frontend/src/pages/OpenKSWorkbenchPage.jsx`
- `frontend/src/pages/openksWorkbenchModel.mjs`

建议修改：

- `frontend/src/App.jsx`
- `frontend/src/components/Layout.jsx`
- `frontend/src/pages/PlatformOverviewPage.jsx`
- `frontend/src/pages/platformShowcaseModel.mjs`

### 8.2 后端

建议新增：

- `backend/app/api/datahub_mock_routes.py`
- `backend/app/api/openks_build_job_routes.py`
- `backend/app/services/datahub_mock_service.py`

建议修改：

- `backend/app/api/__init__.py`
- `backend/app/api/openks_routes.py`
- `backend/app/services/knowledge_runtime_service.py`

### 8.3 supxmind-openks

建议新增：

- `supxmind/supxmind-openks/openks/cross/datahub_adapter/`
- `supxmind/supxmind-openks/openks/cross/graphiti_adapter/`
- `supxmind/supxmind-openks/openks/kg/fact/event_kg/`
- `supxmind/supxmind-openks/openks/kg/fact/industry_network/`

---

## 9. 第一阶段验收标准

1. 前台可展示 RSSHub 头条接入状态
2. 可模拟生成头条批次
3. 可提交 `OpenKS build job`
4. OpenKS 工作台可看到 job/run/artifact/release
5. 可查看产业网大图样例结果
6. 企业库在页面上明确展示为“后续接入”
