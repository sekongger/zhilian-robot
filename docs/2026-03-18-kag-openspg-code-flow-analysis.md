# kag_openspg 主链代码流程深度分析

## 一、整体架构概览

当前系统已经切换到 `kag_openspg` 主链，整体架构分为四层：

```
产品层（前端页面）
    ↓
业务控制层（OpenKS）
    ↓
执行编排层（KAG）
    ↓
语义服务层（OpenSPG）
```

## 二、核心代码调用链路

### 2.1 主链路入口

**前端触发点：**
- 文件：`frontend/src/pages/WorkflowWorkbenchPage.jsx`
- 用户点击"运行工作流"按钮

**后端入口：**
- 文件：`backend/app/api/workflow_routes.py`
- 路由：`POST /workflow/news/run`
- 转发到：`backend/app/openspg_demo/routes.py::run_news_workflow()`

### 2.2 六步执行流程

#### Step 1: 建模（Model）- OpenKS Schema 适配与提交

**关键代码文件：**
```
backend/app/services/openks_schema_runtime_service.py
  ↓ 调用
supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py
  ↓ 调用
modules/kag/knext/schema/marklang/schema_ml.py
```

**详细流程：**

1. **入口函数**：`apply_openks_news_kg_schema()`
   - 位置：`backend/app/services/openks_schema_runtime_service.py:127`
   - 参数：`project_id`, `activate_label`, `module_name="news_kg"`

2. **加载 OpenKS 模块**：
   ```python
   # 动态导入 OpenKS interop 模块
   compile_module_schema, export_module_schema_to_kag_project = _load_openks_interop()
   ```

3. **编译 Schema**：
   - 函数：`compile_module_schema(module_name, namespace=resolved_namespace)`
   - 位置：`supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py:48`
   - 作用：
     - 加载 `news_kg` 模块的 `NewsKgSchema.describe()`
     - 将 Python 字典结构转换为 `.schema` DSL 文本
   
   **Schema 定义源头：**
   ```python
   # supxmind/supxmind-openks/openks/kg/fact/news_kg/schema/news_kg_schema.py
   class NewsKgSchema(BaseSchema):
       def describe(self):
           return {
               "entities": [
                   {"name": "NewsDocument", "desc": "资讯文档"},
                   {"name": "Enterprise", "desc": "企业主体"},
                   {"name": "Technology", "desc": "技术要素"},
                   # ...
               ],
               "relations": [
                   {"name": "involves", "source": "NewsDocument", "target": "Enterprise"},
                   # ...
               ],
               "fields": [
                   {"name": "publish_time", "type": "datetime"},
                   # ...
               ]
           }
   ```

4. **导出到 KAG 项目**：
   - 函数：`export_module_schema_to_kag_project()`
   - 位置：`supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py:88`
   - 作用：
     - 将编译后的 `.schema` DSL 写入文件
     - 路径：`modules/kag/kag/examples/OpenKSNews/schema/OpenKSNews.schema`

5. **提交到 OpenSPG**：
   - 类：`SPGSchemaMarkLang`
   - 位置：`modules/kag/knext/schema/marklang/schema_ml.py:66`
   - 关键方法：`sync_schema()`（行 1124）
   
   **提交流程：**
   ```python
   marklang = SPGSchemaMarkLang(
       schema_path,
       host_addr=resolved_host_addr,
       project_id=project_id
   )
   committed = marklang.sync_schema()
   ```
   
   - `sync_schema()` 调用 `diff_and_sync(False)`
   - 通过 `SchemaClient` 与 OpenSPG 交互
   - 位置：`modules/kag/knext/schema/client.py:145`
   - 方法：`SchemaSession.commit()` 发送 HTTP 请求到 OpenSPG

**输出结果：**
- OpenSPG 中的 project 已更新 schema
- 返回 `schema_commit_result` 和 `activate_result`

---

#### Step 2: 采集（Collect）- RSS/API 资讯采集

**关键代码文件：**
```
backend/app/api/workflow_routes.py::run_news_collect_step()
  ↓ 调用
backend/app/openspg_demo/routes.py::ingest_real_rss()
```

**详细流程：**
1. 调用 RSS 采集服务
2. 将原始资讯存入 MongoDB `news_raw` 集合
3. 返回采集数量和状态

**输出结果：**
- 原始资讯数据存储在 MongoDB

---

#### Step 3: 处理（Process）- Bridge 数据转换

**关键代码文件：**
```
backend/app/openspg_demo/bridge_runner.py
backend/app/openspg_demo/bridge.py
```

**详细流程：**

1. **读取原始数据**：
   - 函数：`_read_news_rows()`
   - 位置：`backend/app/openspg_demo/routes.py:200`
   - 从 MongoDB 读取 `news_raw` 数据

2. **数据标准化**：
   - 函数：`normalize_news_record()`
   - 位置：`backend/app/openspg_demo/bridge.py`
   - 将原始字段映射为标准字段

3. **增量导出**：
   - 类：`BridgeRunner`
   - 位置：`backend/app/openspg_demo/bridge_runner.py:58`
   - 方法：`run_export()`
   - 作用：
     - 根据 `last_seen_time` 游标筛选增量数据
     - 导出为 JSONL 格式
     - 保存到：`backend/data/openspg_demo/batches/{run_id}.jsonl`

**输出结果：**
- JSONL 批次文件
- `bridge_run` 对象（包含 `run_id`, `export_count`, `batch_file_path`）

---

#### Step 4: 抽取（Extract）- KAG Builder 数据准备

**关键代码文件：**
```
backend/app/api/workflow_routes.py::run_news_extract_step()
  ↓ 调用
backend/app/openspg_demo/routes.py::run_bridge_batch()
```

**详细流程：**

1. **读取 JSONL 批次**
2. **准备 Builder 环境变量**：
   - 函数：`build_builder_envs_for_run()`
   - 位置：`backend/app/openspg_demo/builder_import_command.py`
   - 生成环境变量：
     ```python
     {
         "BATCH_FILE_PATH": "/path/to/batch.jsonl",
         "BATCH_RUN_ID": "20260318T120000Z-abc123",
         "EXPORT_COUNT": "150"
     }
     ```

**输出结果：**
- 准备好的批次数据和环境变量
- 等待 Builder 提交

---

#### Step 5: 执行（Execute）- Builder 提交与图谱物化

**关键代码文件：**
```
backend/app/api/workflow_routes.py::run_news_execute_step()
  ↓ 调用
backend/app/openspg_demo/routes.py::submit_engine_builder_job()
backend/app/openspg_demo/routes.py::_materialize_graph_for_bridge_run()
```

**详细流程：**

1. **构建 Builder 命令**：
   - 函数：`build_real_import_command()`
   - 位置：`backend/app/openspg_demo/builder_import_command.py`
   - 生成命令：
     ```bash
     python -m kag.builder.runner \
       --host_addr http://openspg:8887 \
       --project_id 1 \
       --batch_file $BATCH_FILE_PATH
     ```

2. **提交 Builder Job**：
   - 函数：`submit_engine_builder_job()`
   - 位置：`backend/app/openspg_demo/routes.py:2313`
   - 调用 OpenSPG Builder API：
     ```
     POST {host_addr}/public/v1/builder/job/submit
     ```
   - 参数：
     - `project_id`
     - `command`（Builder 执行命令）
     - `worker_num`（并行度）
     - `envs`（环境变量）

3. **KAG Builder 执行**（在 OpenSPG 侧）：
   - 入口：`modules/kag/kag/builder/runner.py`
   - 流程：
     - 读取 JSONL 批次文件
     - 调用 LLM 进行实体抽取、关系抽取
     - 生成 SubGraph 对象
     - 通过 KAG 的 `SPGAligner` 对齐到 schema
     - 提交到 OpenSPG 图存储

4. **图谱物化**：
   - 函数：`_materialize_graph_for_bridge_run()`
   - 位置：`backend/app/openspg_demo/routes.py:592`
   - 调用 OpenSPG Graph API 统计：
     ```
     GET {host_addr}/public/v1/graph/statistics
     ```
   - 返回：`vertices`（实体数）、`edges`（关系数）

5. **注册运行时对象**：
   - 函数：`register_workflow_runtime_binding()`
   - 位置：`backend/app/services/knowledge_runtime_service.py:103`
   - 作用：
     - 创建 `KnowledgeRun` 记录（MongoDB `knowledge_runs` 集合）
     - 创建 `KnowledgeArtifact` 记录（MongoDB `knowledge_artifacts` 集合）
     - 创建 `ServiceRelease` 记录（MongoDB `service_releases` 集合，状态为 `draft`）

**输出结果：**
- OpenSPG 图谱中新增实体和关系
- `KnowledgeRun`：`KRUN_KAG_{run_id}`
- `KnowledgeArtifact`：`KART_KAG_{run_id}`
- `ServiceRelease`：`KREL_KART_KAG_{run_id}_draft`

---

## 三、关键数据流转

### 3.1 Schema 流转

```
OpenKS Python describe()
  ↓ (compile_module_schema)
.schema DSL 文本
  ↓ (export_module_schema_to_kag_project)
KAG 项目 schema 文件
  ↓ (SPGSchemaMarkLang.sync_schema)
OpenSPG SchemaClient
  ↓ (HTTP POST)
OpenSPG 服务端 schema 存储
```

### 3.2 数据流转

```
RSS/API 原始资讯
  ↓ (ingest_real_rss)
MongoDB news_raw 集合
  ↓ (BridgeRunner.run_export)
JSONL 批次文件
  ↓ (Builder Job)
KAG Builder 处理
  ↓ (LLM 抽取 + SPGAligner)
OpenSPG 图谱存储
  ↓ (Graph API)
实体、关系、陈述
```

### 3.3 运行时对象流转

```
bridge_run (批次运行记录)
  ↓ (register_workflow_runtime_binding)
KnowledgeRun (知识构建运行)
  ↓
KnowledgeArtifact (知识产物版本)
  ↓
ServiceRelease (服务发布版本)
```

---

## 四、关键代码文件清单

### 4.1 OpenKS 层

| 文件路径 | 作用 |
|---------|------|
| `supxmind/supxmind-openks/openks/kg/fact/news_kg/schema/news_kg_schema.py` | 业务 schema 定义（Python describe） |
| `supxmind/supxmind-openks/openks/common/interop/kag_schema_adapter.py` | Schema 编译器（Python → DSL） |
| `supxmind/supxmind-openks/openks/common/interop/__init__.py` | Interop 导出接口 |

### 4.2 后端服务层

| 文件路径 | 作用 |
|---------|------|
| `backend/app/api/workflow_routes.py` | Workflow 路由入口 |
| `backend/app/services/openks_schema_runtime_service.py` | OpenKS schema 运行时服务 |
| `backend/app/services/knowledge_runtime_service.py` | Run/Artifact/Release 管理 |
| `backend/app/openspg_demo/routes.py` | 主链异步执行逻辑 |
| `backend/app/openspg_demo/bridge_runner.py` | 增量数据导出器 |
| `backend/app/openspg_demo/bridge.py` | 数据标准化 |
| `backend/app/openspg_demo/builder_import_command.py` | Builder 命令构建 |

### 4.3 KAG 层

| 文件路径 | 作用 |
|---------|------|
| `modules/kag/knext/schema/marklang/schema_ml.py` | Schema DSL 解析器和提交器 |
| `modules/kag/knext/schema/client.py` | OpenSPG Schema 客户端 |
| `modules/kag/kag/builder/runner.py` | Builder 主执行器 |
| `modules/kag/kag/builder/component/extractor/` | 实体和关系抽取器 |
| `modules/kag/kag/builder/component/aligner/spg_aligner.py` | Schema 对齐器 |

### 4.4 前端层

| 文件路径 | 作用 |
|---------|------|
| `frontend/src/pages/WorkflowWorkbenchPage.jsx` | Workflow 工作台页面 |
| `frontend/src/pages/PlatformOverviewPage.jsx` | 知识计算概览页 |
| `frontend/src/pages/GraphPage.jsx` | 网链分析页 |

---

## 五、关键接口调用

### 5.1 OpenSPG HTTP API

| API | 方法 | 作用 |
|-----|------|------|
| `/public/v1/project?projectId={id}` | GET | 查询项目信息（获取 namespace） |
| `/public/v1/schema/alter` | POST | 提交 schema 变更 |
| `/public/v1/builder/job/submit` | POST | 提交 Builder 任务 |
| `/public/v1/graph/statistics` | GET | 查询图谱统计信息 |
| `/public/v1/reasoner/query` | POST | 执行推理查询 |

### 5.2 内部服务接口

| 接口 | 作用 |
|------|------|
| `POST /workflow/news/run` | 启动完整工作流 |
| `POST /workflow/news/steps/model` | 执行建模步骤 |
| `POST /workflow/news/steps/collect` | 执行采集步骤 |
| `POST /workflow/news/steps/process` | 执行处理步骤 |
| `POST /workflow/news/steps/extract` | 执行抽取步骤 |
| `POST /workflow/news/steps/execute` | 执行执行步骤 |
| `POST /workflow/news/steps/apply` | 执行应用步骤 |

---

## 六、数据存储位置

### 6.1 MongoDB 集合

| 集合名 | 存储内容 |
|--------|---------|
| `news_raw` | RSS 原始资讯 |
| `knowledge_runs` | 知识构建运行记录 |
| `knowledge_artifacts` | 知识产物版本 |
| `service_releases` | 服务发布版本 |

### 6.2 文件系统

| 路径 | 存储内容 |
|------|---------|
| `backend/data/openspg_demo/batches/{run_id}.jsonl` | Bridge 导出的 JSONL 批次 |
| `backend/data/openspg_demo/bridge_state.json` | Bridge 游标状态 |
| `modules/kag/kag/examples/OpenKSNews/schema/OpenKSNews.schema` | 编译后的 schema DSL |

### 6.3 OpenSPG 存储

| 存储类型 | 内容 |
|---------|------|
| Schema Store | 本体定义（EntityType, Relation, Property） |
| Graph Store | 实体、关系、陈述 |
| Index Store | 向量索引、全文索引 |

## 八、总结

### 8.1 核心调用链

```
前端 WorkflowWorkbenchPage
  ↓
后端 workflow_routes.py
  ↓
OpenKS schema_runtime_service.py
  ↓
OpenKS interop/kag_schema_adapter.py
  ↓
KAG schema_ml.py (SPGSchemaMarkLang)
  ↓
KAG client.py (SchemaClient)
  ↓
OpenSPG HTTP API
```

### 8.2 数据处理链

```
RSS 采集
  ↓
MongoDB 存储
  ↓
Bridge 标准化
  ↓
JSONL 导出
  ↓
KAG Builder 抽取
  ↓
OpenSPG 图谱存储
  ↓
知识服务消费
```

### 8.3 关键衔接点

1. **OpenKS → KAG**：通过 `kag_schema_adapter.py` 编译 schema
2. **KAG → OpenSPG**：通过 `SPGSchemaMarkLang.sync_schema()` 提交 schema
3. **Backend → KAG**：通过 Builder Job 提交数据处理任务
4. **KAG → OpenSPG**：通过 Graph API 写入实体和关系
5. **Backend → MongoDB**：通过 `knowledge_runtime_service.py` 记录运行时对象

---

# 关于 KAG 和 OpenSPG 的实际调用方式

## 核心结论

**是的，系统确实通过 HTTP 调用外部独立运行的 OpenSPG 服务，而不是自己实现的模拟。**

## 详细说明

### 1. OpenSPG 是独立部署的外部服务

从配置可以看出：

```yaml
# docker-compose.yml 中的配置
backend:
  environment:
    - OPENSPG_BASE_URL=${OPENSPG_BASE_URL:-http://172.17.0.1:8887}
```

**关键点：**
- `172.17.0.1` 是 Docker 的默认网关地址，指向宿主机
- 端口 `8887` 是 OpenSPG 服务的默认端口
- 这意味着 **OpenSPG 是在宿主机上独立运行的服务**，不在 docker-compose 中

### 2. 真实的 HTTP 调用

系统使用 `httpx` 库（Python 的异步 HTTP 客户端）进行真实的网络调用：

```python
# backend/app/openspg_demo/openspg_client.py
async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
    result = await _request_json(
        client,
        "POST",
        "/public/v1/builder/kag/submit",
        json_body=body
    )
```

**调用的 OpenSPG API 包括：**

| API 端点 | 作用 |
|---------|------|
| `POST /public/v1/schema/alterSchema` | 提交 schema 变更 |
| `POST /public/v1/builder/kag/submit` | 提交 KAG Builder 任务 |
| `POST /public/v1/graph/upsertVertex` | 插入/更新图谱节点 |
| `POST /public/v1/graph/upsertEdge` | 插入/更新图谱边 |
| `GET /public/v1/project` | 查询项目信息 |
| `POST /public/v1/search/custom` | 执行自定义查询 |
| `GET /public/v1/reason/schema` | 获取推理 schema |

### 3. KAG 的角色

**KAG 不是独立服务，而是作为 Python 库被集成到后端中：**

```python
# 后端直接导入 KAG 的 Python 模块
from knext.schema.marklang.schema_ml import SPGSchemaMarkLang
from knext.schema.client import SchemaClient
```

**KAG 的作用：**
1. **Schema 编译器**：将 `.schema` DSL 解析为 OpenSPG 可接受的格式
2. **HTTP 客户端封装**：提供 `SchemaClient`、`ReasonerClient` 等封装类
3. **Builder 框架**：提供数据处理、实体抽取、关系抽取的框架代码

**KAG 最终也是通过 HTTP 调用 OpenSPG：**

```python
# modules/kag/knext/schema/client.py
class SchemaClient(Client):
    def __init__(self, host_addr: str = None, project_id: str = None):
        self._rest_client: rest.SchemaApi = rest.SchemaApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )
```

### 4. 完整的调用架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker 容器环境                            │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Backend 容器 (Python FastAPI)                        │   │
│  │                                                        │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  OpenKS (业务层)                              │    │   │
│  │  │  - news_kg.describe()                        │    │   │
│  │  │  - 定义业务 schema                            │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                    ↓                                   │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  KAG (Python 库，集成在后端中)                │    │   │
│  │  │  - SPGSchemaMarkLang (schema 编译)           │    │   │
│  │  │  - SchemaClient (HTTP 客户端封装)            │    │   │
│  │  │  - Builder 框架                               │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                    ↓                                   │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  httpx.AsyncClient                            │    │   │
│  │  │  - HTTP POST/GET 请求                         │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                    ↓ HTTP 请求                             │
└────────────────────┼──────────────────────────────────────┘
                     ↓
              Docker 网关 (172.17.0.1)
                     ↓
┌────────────────────┼──────────────────────────────────────┐
│                宿主机 (Host Machine)                        │
│                    ↓                                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  OpenSPG 服务 (独立运行在 :8887)                      │ │
│  │                                                        │ │
│  │  - Schema 管理服务                                     │ │
│  │  - Graph 存储服务                                      │ │
│  │  - Builder 执行引擎                                    │ │
│  │  - Reasoner 推理服务                                   │ │
│  │  - Search 查询服务                                     │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 总结

1. **OpenSPG 是真实的外部服务**，运行在宿主机的 8887 端口
2. **KAG 是 Python 库**，集成在后端容器中，作为 OpenSPG 的客户端
3. **所有调用都是真实的 HTTP 请求**，使用 `httpx` 库
4. **不是模拟实现**，而是真正的分布式架构
5. **系统有降级机制**，OpenSPG 不可用时会返回 mock 数据，但主链路依赖真实服务

这是一个典型的**微服务架构**，后端作为业务编排层，OpenSPG 作为知识图谱引擎层。

文韬构建大图,初始化大图 企业挂接到产业实体节点
浩渊构建链图,编织出 AI 产业链图
自动化智能化挂接

现在的想法是想要构建大图,初始化一个大图的 schema, 然后输入数据,调用 openspg/kag 的接口能力,使得企业/专利等要素挂接到产业实体节点,然后生成了这个挂接关系之后,可以构建链图,编织出具体的产业链图,比如人工智能链挂接了什么企业/专利,这个也是可以不断随着数据的更新而更新的,这个应该如何设计结合进当前的流程里