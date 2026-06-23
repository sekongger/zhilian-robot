# 浙大 AI 知识中心“产业头条 + 企业库”链路与 OpenKS 一体化技术方案

更新时间：2026-03-21

> 本方案基于以下前提整理：
>
> - 前台展示口径以 [docs/2026-03-20-zheda-ai-pilot-platform-and-supxmind-architecture.md](/Users/youfang/Documents/zhilian-robot/docs/2026-03-20-zheda-ai-pilot-platform-and-supxmind-architecture.md) 为准
> - 产业网大图基础 schema 第一版以 [docs/IncCore.schema](/Users/youfang/Documents/zhilian-robot/docs/IncCore.schema) 为准
> - OpenKS 目录组织参考 [docs/openks.md](/Users/youfang/Documents/zhilian-robot/docs/openks.md)，但要兼容当前 `supxmind/supxmind-openks` 仓库现状
> - `DataHub` 由外部团队建设，这边重点是定义对接接口与 OpenKS 技术方案
> - 第一阶段只先实现“产业头条”链路，头条数据用现有 RSSHub 数据代替，企业库接口先预留不接实数
> - OpenKS 最终对外单实例暴露，OpenSPG 服务能力只作为内部代理能力，不单独对外暴露
> - 更细的页面结构与接口对象设计见 [docs/2026-03-21-headlines-openks-detailed-design.md](/Users/youfang/Documents/zhilian-robot/docs/2026-03-21-headlines-openks-detailed-design.md)

---

## 1. 目标

本次方案的目标不是一次性做完全部“产业头条 + 企业库 + 大图 + 链图”能力，而是先明确一条能逐步落地的主线：

1. `DataHub` 能调用头条和企业库接口拿到数据
2. `DataHub` 把标准化数据交给 `OpenKS`
3. `OpenKS` 负责 schema 管理、知识计算、知识融合和 OpenSPG 落图
4. `OpenKS` 最终产出产业网大图相关结果
5. 前台页面能展示“DataHub 把数据交对，OpenKS 把知识算对，OpenSPG 把图存对”的全过程与结果

第一阶段只要求：

- 跑通“产业头条 -> DataHub -> OpenKS -> OpenSPG -> 前台展示”
- 企业库只先定义接口和展示占位
- 不要求第一阶段就把产业链图谱自动抽取做到完整生产级

---

## 1.1 已确认口径

本方案以下 5 条已经作为确定结论：

1. `[IncCore.schema](/Users/youfang/Documents/zhilian-robot/docs/IncCore.schema)` 作为产业网大图 schema v1，头条链路只启用其中与资讯/事件/企业/技术相关的 schema 子集。
2. `Graphiti` 最终接真实服务，但第一阶段先在 OpenKS 内做兼容真实契约的模拟 `adapter`，真实部署放到后续阶段。
3. `OpenKS` 对外只暴露单实例入口，`OpenSPG` 相关服务能力在 OpenKS 内部代理，不单独对外暴露。
4. 企业库字段尚未最终确定，第一阶段按 `Company` 的基础字段子集实现接口和模块骨架。
5. 除前台外，`OpenKS` 需要单独工作台页面，用于展示数据导入、加工处理、构建结果和查询能力；前台负责业务展示，OpenKS 工作台负责构建工作台展示。

## 1.2 当前实现状态

### 已实现

- 前台五栏目展示页已落地，并已补充 `OpenKS` 工作台跳转入口
- `OpenKS` 工作台页面已落地，并已开始接真实模块、构建任务和图谱结果接口
- `/openks` 与 `/openks/workbench` 路由已接入前端
- DataHub mock 头条接口已落地，头条数据可用现有资讯/RSS 数据模拟
- DataHub mock 企业接口已落地，占位返回“后续接入”
- `OpenKS build-jobs` 提交/查询骨架已落地
- `OpenKS graph/summary`、`graph/sample`、`graph/evidence` 接口已落地
- `event_kg` 与 `industry_network` 模块骨架已在 `supxmind-openks` 中创建

### 待实现

- `Graphiti` 真实服务部署与真实接入
- `DataHub -> OpenKS` 真实远程调用链完全替换 mock
- `event_kg` 的真实 builder / reasoner / solver
- `industry_network` 的真实融合逻辑
- `IncCore.schema` 到实际构建链的完整映射
- 企业库真实接口接入与 `enterprise_kg`
- 从产业网大图抽取产业链图谱的真实逻辑
- `OpenKS -> OpenSPG` 内部代理链的生产化收口

---

## 2. 总体判断

### 2.1 这条主线是成立的

你现在想要的主线可以整理为：

```text
头条接口 / 企业库接口
-> DataHub 接入与标准化
-> Graphiti 对动态头条做初步加工
-> OpenKS 知识计算
-> OpenSPG 存储产业网大图
-> 从产业网大图抽取产业链图谱
-> 前台展示 / 智能服务消费
```

这条链路是合理的。

### 2.2 但需要明确分工边界

这条链必须严格区分三层：

- `DataHub` 负责“把数据交对”
- `OpenKS` 负责“把知识算对”
- `OpenSPG` 负责“把图存对”

这三层不能混。

更准确地说：

- `DataHub` 不应该直接拼 OpenSPG 的 vertices/edges
- `OpenKS` 不应该只做一个转发器
- `OpenSPG` 不应该承担业务语义映射

---

## 3. 业务主线设计

### 3.1 第一阶段范围

第一阶段只实现：

- 产业头条数据接入
- DataHub 到 OpenKS 的模拟对接
- `news_kg + event_kg + industry_network` 最小链路
- 前台展示结果

第一阶段明确不做：

- 企业库真实接入
- 多源融合全量规则
- 完整产业链图谱自动抽取
- 创新链/资金链/人才链完整专题

### 3.2 第二阶段范围

第二阶段再补：

- 企业库真实接入
- `enterprise_kg`
- `knowledge_fusion` 的企业挂接逻辑
- 从产业网大图抽取产业链图谱

### 3.3 第三阶段范围

第三阶段再扩展：

- 创新链
- 资金链
- 人才链
- 智能体头条推送联动

---

## 4. 基于 IncCore.schema 的第一阶段 schema 选型

`IncCore.schema` 很大，不适合第一阶段全量上。  
第一阶段建议只取其中与头条资讯和产业网大图最相关的一小部分类型。

更准确地说：

- `IncCore.schema` 是整个产业网大图的 schema 基线
- 第一阶段头条链路只启用其中与 `Document / Chunk / DataSource / Company / Technology / Event` 相关的类型
- schema 由 `OpenKS` 自己持有和同步，`DataHub` 不直接传 schema 给 OpenSPG

### 4.1 第一阶段建议启用的核心类型

来自 [docs/IncCore.schema](/Users/youfang/Documents/zhilian-robot/docs/IncCore.schema) 的建议子集：

- `IndustryNode`
- `IndustrySector`
- `Company`
- `Organization`
- `Person`
- `Technology`
- `ProductObject`
- `Document`
- `DataSource`
- `Chunk`
- `Event`
- `CompanyCooperationEvent`
- `CompanyFinancingEvent`

### 4.2 第一阶段建议启用的关键关系

- `Company.supplier`
- `Company.customer`
- `Company.invest`
- `ProductObject.coreTechnology`
- `CompanyCooperationEvent.subject/object`
- `CompanyFinancingEvent.subject/object`
- `Document.source`
- `Event.source`

### 4.3 第一阶段的实际图谱表达

第一阶段不追求把 `IncCore.schema` 全量投用，而是先形成 3 层结果：

1. 头条事实层
   - 文档
   - 文本块
   - 数据来源
   - 公司
   - 技术
   - 合作/融资事件

2. 动态事实图谱
   - 头条事件
   - 事件主体
   - 事件证据

3. 产业网大图基础层
   - 公司
   - 技术
   - 产品
   - 行业节点
   - 事件挂接关系

---

## 5. DataHub -> OpenKS -> OpenSPG 链路设计

### 5.1 第一阶段实际链路

```mermaid
flowchart LR
    A["RSSHub / 产业头条数据"] --> B["DataHub 模拟接入层"]
    B --> C["标准化 Batch / Manifest"]
    C --> D["Graphiti 初步加工"]
    D --> E["OpenKS<br/>news_kg + event_kg"]
    E --> F["industry_network / knowledge_fusion"]
    F --> G["OpenSPG 产业网大图"]
    G --> H["前台展示 / 图查询 / 智能服务"]
```

### 5.2 企业库后续链路

```mermaid
flowchart LR
    A["企业库接口"] --> B["DataHub 接入"]
    B --> C["标准化企业批次"]
    C --> D["OpenKS enterprise_kg"]
    D --> E["knowledge_fusion"]
    E --> F["OpenSPG 产业网大图"]
```

### 5.3 一句话说明

- 头条类动态数据先过 `Graphiti`
- 企业类静态/半结构化数据直接进入 `enterprise_kg`
- 最终都汇入 `industry_network`
- `industry_network` 写入 OpenSPG 形成产业网大图

补充说明：

- 第一阶段 `Graphiti` 先以模拟适配器形式存在
- 第二阶段再替换成真实 Graphiti 服务

---

## 6. 接口设计原则

### 6.1 DataHub 接口和 OpenSPG 原生接口不一样

必须明确：

- `DataHub -> OpenKS` 是业务层接口
- `OpenKS -> OpenSPG` 是引擎层接口

两者参数不应相同。

如果让 `DataHub` 直接按 OpenSPG 的 `vertices/edges` 参数调用，会带来问题：

- DataHub 需要理解业务 schema 和 type 名
- DataHub 需要自己做实体标准化
- DataHub 需要自己决定哪些数据进 `news_kg/event_kg/enterprise_kg`
- DataHub 会和 OpenKS 职责重叠

因此建议：

- `DataHub` 只提交标准批次和构建意图
- `OpenKS` 内部再去完成 schema sync、图构建和 OpenSPG 落库

### 6.2 第一阶段最小接口集合

建议先定义 4 类接口：

1. 头条接入接口
2. DataHub -> OpenKS 构建接口
3. OpenKS 构建状态查询接口
4. OpenKS 产物查询接口

---

## 7. 接口定义草案

### 7.1 头条数据接口

第一阶段直接复用现有 RSSHub 数据，不重新造源。

建议由 `DataHub` 侧调用一个聚合接口：

`GET /api/v1/datahub/mock/headlines`

返回示例：

```json
{
  "source": "rsshub",
  "items": [
    {
      "doc_id": "DOC_NEWS_001",
      "title": "华为与某机器人公司签署战略合作协议",
      "summary": "......",
      "content": "......",
      "source_name": "RSSHub",
      "source_url": "https://example.com/a/1",
      "publish_time": "2026-03-21T10:00:00+08:00"
    }
  ]
}
```

### 7.2 企业库接口

第一阶段只预留，不接实数。

建议先约定：

`GET /api/v1/datahub/mock/enterprise`

返回示例：

```json
{
  "source": "enterprise_api",
  "enabled": false,
  "message": "后续接入"
}
```

### 7.3 DataHub -> OpenKS 构建接口

建议新增统一接口：

`POST /api/v1/openks/build-jobs`

请求示例：

```json
{
  "project_id": 1,
  "namespace": "IncCore",
  "resource_pool_id": "POOL_HEADLINES_001",
  "batch_id": "BATCH_20260321_001",
  "manifest_uri": "file:///tmp/batch_20260321_001.jsonl",
  "source_types": ["headlines"],
  "module_names": ["news_kg", "event_kg", "industry_network"],
  "runtime_profile": "kag_openspg",
  "graphiti_options": {
    "enabled": true,
    "mode": "event_preprocess"
  },
  "schema_policy": {
    "mode": "sync_if_changed"
  },
  "build_options": {
    "publish_release": false
  },
  "idempotency_key": "POOL_HEADLINES_001:BATCH_20260321_001"
}
```

返回示例：

```json
{
  "job_id": "OKBUILD_20260321_001",
  "accepted": true,
  "status": "queued",
  "module_names": ["news_kg", "event_kg", "industry_network"]
}
```

### 7.4 OpenKS 构建状态查询接口

`GET /api/v1/openks/build-jobs/{job_id}`

返回示例：

```json
{
  "job_id": "OKBUILD_20260321_001",
  "status": "completed",
  "run_id": "KRUN_KAG_001",
  "artifact_id": "KART_KAG_001",
  "release_id": "KREL_KAG_001_DRAFT",
  "graph_stats": {
    "vertices": 532,
    "edges": 1218
  }
}
```

### 7.5 OpenKS 产物查询接口

建议保留：

- `GET /api/v1/runs`
- `GET /api/v1/artifacts`
- `GET /api/v1/releases`

当前仓库已经有这套产物接口，见 [backend/app/api/knowledge_runtime_routes.py](/Users/youfang/Documents/zhilian-robot/backend/app/api/knowledge_runtime_routes.py)。

---

## 8. OpenKS 代码组织方案

### 8.1 原则

虽然 [docs/openks.md](/Users/youfang/Documents/zhilian-robot/docs/openks.md) 给了一版理想结构，但当前仓库已经存在真实的 `supxmind/supxmind-openks/openks` 包结构。

因此建议：

- 不新起一个 `src/openks` 平行体系
- 在现有 `supxmind/supxmind-openks/openks` 基础上演进
- 吸收 `docs/openks.md` 的设计思想，但保持当前导入、模块发现和 schema 适配链兼容

### 8.2 推荐目录演进

建议演进为：

```text
supxmind/supxmind-openks/openks/
├── common/
│   ├── adapters/
│   ├── base/
│   ├── interop/
│   ├── registry/
│   └── utils/
├── cross/
│   ├── datahub_adapter/
│   ├── graphiti_adapter/
│   └── fusion/
├── entry/
│   ├── api/
│   ├── bootstrap/
│   └── runtime/
├── kg/
│   ├── fact/
│   │   ├── base_kg/
│   │   ├── news_kg/
│   │   ├── event_kg/
│   │   ├── enterprise_kg/
│   │   └── industry_network/
│   ├── cognition/
│   │   ├── industry_chain/
│   │   ├── innovation_chain/
│   │   ├── capital_chain/
│   │   └── talent_chain/
│   └── decision/
└── tests/
```

### 8.3 第一阶段必须新增的模块

第一阶段只建议补这些：

- `openks/cross/datahub_adapter/`
- `openks/cross/graphiti_adapter/`
- `openks/kg/fact/event_kg/`
- `openks/kg/fact/industry_network/`

### 8.4 第一阶段可复用的现有模块

- `base_kg`
- `news_kg`
- `common/interop`
- `entry/api`

---

## 9. OpenKS 内部处理流程

### 9.1 头条链路内部流程

```text
DataHub 批次
-> GraphitiAdapter
-> event_kg
-> news_kg
-> knowledge_fusion
-> industry_network
-> OpenSPG
-> run/artifact/release
```

### 9.2 各模块职责

#### datahub_adapter

负责：

- 接收 DataHub 批次对象
- 解析 `manifest_uri`
- 转成 OpenKS 标准输入记录

#### graphiti_adapter

负责：

- 针对头条资讯生成事件事实包
- 输出给 `event_kg`

#### news_kg

负责：

- 文档、实体、关系、陈述抽取
- 资讯事实沉淀

#### event_kg

负责：

- 事件对象标准化
- 动态事实结构化
- 证据和时态保留

#### industry_network

负责：

- `news_kg + event_kg + enterprise_kg` 融合
- 对齐 `IncCore.schema`
- 组织成产业网大图

---

## 10. 部署方案评估

### 10.1 是否可以不单独启动 OpenSPG 和 KAG 实例

结论：

- 从“对外暴露”角度，可以只有一个 `openks` 服务入口
- 从“内部运行”角度，OpenSPG 能力仍作为 OpenKS 的内部代理能力存在
- 第一阶段不建议强行把所有 OpenSPG 服务端能力都塞进单一 Python 进程

更准确地说：

- 用户、前台、DataHub 都只对接 `openks`
- `openks` 内部再去调用 OpenSPG 相关能力
- OpenSPG 不单独暴露给外部使用方

### 10.2 推荐部署口径

推荐的生产口径是：

- 对外只暴露一个 `openks` 服务实例
- `openks` 镜像内集成：
  - OpenKS 业务模块
  - KAG schema/runtime 适配模块
  - OpenSPG 调用适配代码
- 底层仍依赖：
  - 图数据库（Neo4j）
  - OpenSPG 服务端接口能力
  - 必要的 MySQL / MongoDB

也就是说：

- “不单独给用户暴露 OpenSPG/KAG 实例”是可行的
- “完全不需要 OpenSPG/KAG 服务能力”不可行

### 10.3 第一阶段建议

第一阶段建议采用：

- `openks` 一个业务容器
- 复用现有 OpenSPG/Neo4j 基础设施
- 对外由 `openks` 统一暴露业务 API

不要在第一阶段就强行做成一个“完全消灭 OpenSPG 运行依赖”的单容器方案。

---

## 11. 前台页面展示设计

### 11.1 前台总体原则

前台继续沿现有 `/platform` 五个一级菜单展示：

- 整体概况
- 数据汇聚
- 知识计算
- 网链分析
- 智能服务

第一阶段重点要让用户看清楚：

- 头条数据从哪里来
- DataHub 做了什么
- OpenKS 做了什么
- OpenSPG 里形成了什么
- 当前是否已经能形成产业网大图结果

### 11.2 数据汇聚页展示

当前页以展示为主，不做真实 DataHub 接口强依赖。

建议新增或替换成 4 块：

1. 数据源接入卡片
   - 产业头条：已接入（RSSHub）
   - 企业库：后续接入

2. 标准化批次卡片
   - 最近批次号
   - 拉取条数
   - 清洗后条数
   - 批次生成时间

3. 接口调用状态
   - DataHub -> OpenKS
   - 最近调用时间
   - 最近 job_id
   - 最近状态

4. 数据加工流程
   - 接口拉取
   - 标准化
   - Graphiti 初步加工
   - 提交 OpenKS

### 11.3 知识计算页展示

知识计算页建议拆成 5 块：

1. Schema 展示
   - 读取 `IncCore.schema`
   - 展示本次启用的 schema 子集

2. KG 模块状态
   - `news_kg`
   - `event_kg`
   - `industry_network`
   - `enterprise_kg`（后续接入）

3. 构建任务状态
   - run
   - artifact
   - release

4. 结果统计
   - 文档数
   - 公司数
   - 事件数
   - 边数

5. 融合结果摘要
   - 动态事实图谱
   - 产业网大图
   - 产业链图谱抽取准备状态

### 11.4 OpenKS 页面建议

如果前台之外还需要单独的 OpenKS 页面，建议它不是“管理员控制台”，而是“知识构建工作台”。

职责边界建议固定为：

- 前台：展示业务结果、状态、入口、摘要
- OpenKS 工作台：展示 schema、导入、加工、构建任务、run/artifact/release、图谱结果查询

跳转建议固定为：

- 前台 `/platform?tab=overview` 和 `/platform?tab=knowledge-computing`
- 跳转到 `/openks/workbench`
- 参数带 `batch_id / job_id / run_id / artifact_id / release_id`

建议至少包含 4 个 Tab：

```text
Schema
KG 模块
构建任务
图谱结果
```

其中：

- `Schema`：展示 `IncCore.schema` 及模块增量 schema
- `KG 模块`：展示 `news_kg / event_kg / enterprise_kg / industry_network`
- `构建任务`：展示 build job、run、artifact、release
- `图谱结果`：展示产业网大图的统计和样例查询

---

## 12. OpenKS 最终数据如何展示

### 12.1 最终数据存哪里

综合评估，建议：

- 正式图谱数据存 `OpenSPG` 对接的图存层
- 当前阶段实际图查询可以继续借助 Neo4j
- 运行对象继续存 MongoDB：
  - `knowledge_runs`
  - `knowledge_artifacts`
  - `service_releases`

也就是说：

- 图数据：图数据库
- 运行对象：Mongo
- 配置/本体辅助：MySQL 或 schema 文件

企业库方面，第一阶段建议先按 `Company` 的基础字段子集实现：

- `name`
- `officialName`
- `alias`
- `code`
- `industry`
- `region`
- `website`
- `status`
- `foundedDate`
- `description`
- `source`
- `source_url`
- `confidence`

### 12.2 是否直接集成 Neo4j 网页端

不建议把 Neo4j Browser 当成前台主展示。

原因：

- 它适合开发调试，不适合业务展示
- 术语和交互太底层
- 无法自然承接 `run/artifact/release`
- 不适合领导和业务视角

### 12.3 推荐展示方式

推荐方案是：

- 前台自己实现业务化图谱展示页
- Neo4j Browser 只保留给研发调试

前台展示页建议做：

1. 统计摘要卡片
2. 事件列表
3. 主体关系图
4. 产业网大图样例视图
5. 产业链图谱抽取结果视图

### 12.4 第一阶段图展示建议

第一阶段不做复杂图编辑器，先做：

- 头条事件列表
- 公司/技术/事件的关系子图
- 产业网大图样例子图
- 证据侧边栏

这样成本最低，也最容易把“头条 -> 动态事实 -> 产业网大图”的价值说清楚。

---

## 13. OpenSPG 加工后数据与大图/链图关系

### 13.1 OpenSPG 加工后的第一层结果

OpenSPG 加工后，首先得到的是：

- 按 `IncCore.schema` 对齐后的正式图谱顶点和边
- 可追踪到 `run / artifact / release` 的知识产物

这一层结果首先对应的是：

- `动态事实图谱`
- `产业网大图`

### 13.2 还不是最终产业链图谱

这里必须明确：

- OpenSPG 落图后，不等于产业链图谱已经完成
- 产业链图谱还需要从产业网大图中按产业视角进一步抽取和组织

关系应理解为：

```text
OpenSPG 正式图
-> 产业网大图
-> 产业链图谱抽取
-> 网链分析 / 智能服务
```

### 13.3 还需要处理什么

OpenSPG 落图后，至少还要补 2 层：

1. 主图融合处理
   - 头条事件
   - 公司主体
   - 技术要素
   - 文档证据
   - 统一归并

2. 产业链图谱抽取
   - 从产业网大图中抽取产业视角子图
   - 生成面向展示的链图节点边
   - 补充上下游、合作、融资等链路标签

---

## 14. 推荐实施顺序

### Phase 1：头条链路打通

- 前台展示 `DataHub` 接入 RSSHub 头条
- `DataHub` 模拟接口提交 `OpenKS build job`
- `OpenKS` 先补 `event_kg`
- `news_kg + event_kg -> industry_network`
- OpenSPG 落产业网大图
- 前台展示构建结果

### Phase 2：企业库接入

- 对接企业库接口
- 补 `enterprise_kg`
- 加入 `knowledge_fusion`
- 企业主体挂到产业网大图

### Phase 3：产业链图谱抽取

- 从产业网大图按产业视角抽取产业链图谱
- 前台图谱页面联动
- 支撑头条推送和问答

---

## 15. 当前不确定项

下面这些点建议后续再单独确认：

1. `IncCore.schema` 第一阶段到底启用哪些类型
   - 我当前建议只启用头条和企业相关子集

2. `Graphiti` 是做真实服务接入，还是先做 OpenKS 内部模拟适配器
   - 第一阶段建议先做适配器，不强依赖外部 Graphiti 服务

3. OpenSPG 服务端能力是否允许被 OpenKS 镜像内统一代理
   - 如果可以，对外只暴露 `openks`
   - 如果不行，就保留内部依赖服务

4. 企业库后续接口的数据字段是否稳定
   - 这决定 `enterprise_kg` 的 builder 输入契约

---

## 16. 最终建议

一句话总结：

- 第一阶段只先做“产业头条 -> DataHub 模拟接入 -> OpenKS -> OpenSPG -> 前台展示”
- DataHub 接口用业务层对象，不直接传 OpenSPG 顶点边
- OpenKS 继续沿当前 `supxmind-openks` 结构演进，补 `event_kg` 和 `industry_network`
- 对外可以只有一个 `openks` 实例入口，但底层仍应复用 OpenSPG/图数据库能力
- 最终图谱展示建议前台自实现，Neo4j Browser 只作为研发调试工具

这样既符合你现在改好的前后台展示口径，也能沿着当前仓库真实能力逐步落地。
