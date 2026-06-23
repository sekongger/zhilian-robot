# OpenKS 开发协作指南

## 目标

让资讯、研报、百科、产业链等模块能够在同一仓内并行开发，同时保持统一的模块结构和可观测状态。

## 协作定位

`supxmind-openks` 负责知识计算模块本体，不负责平台页面、上传入口、主仓路由或运维脚本。对多人协作来说，可以把职责简单分成两类：

1. OpenKS 模块开发
   - 负责 `schema / builder / reasoner / solver / tests`
   - 负责模块级 `module.toml`、`README.md`
   - 负责模块对上游输入和下游产物的约定
2. 主仓平台接线
   - 负责资源接入、任务调度、页面摘要、Open API、异步任务
   - 负责把 `supxmind-openks` 模块接入 `zhilian-robot` 的平台链路

一句话：

- `supxmind-openks` 负责“知识计算模块本体”
- `zhilian-robot` 负责“平台入口、队列接入、页面展示、服务消费”

## 模块级协作规则

- 每个模块根目录必须包含 `module.toml`。
- `module.toml` 负责描述：
  - `name`
  - `title`
  - `stage`
  - `owner`
  - `status`
  - `summary`
  - `dependencies`
- `README.md` 负责描述负责人、开发范围、实现说明和待办事项。

补充约定：

- `status` 要真实反映模块状态，不要把“只有骨架文件”的模块标成已实现。
- `dependencies` 表示 KG 级依赖关系，不是 Python 包依赖。
- 若模块已经可被主仓真实消费，推荐使用 `status = "active"`；纯骨架用 `status = "skeleton"`。

## 标准目录

每个模块至少包含：

- `schema/`
- `builder/`
- `reasoner/`
- `solver/`
- `config/`
- `tests/`
- `README.md`
- `module.toml`

多人协作时，默认一个模块一个负责人，尽量只在自己模块目录内改动。若一个功能需要多人协作，也建议先把工作拆到：

- `schema`
- `builder`
- `reasoner`
- `solver`
- `tests`

避免多人同时修改同一个文件。

## 本地安装

在 `supxmind/supxmind-openks` 目录下执行：

```bash
python -m pip install -e .
```

如果只需要被主仓 backend 使用，也可以由 backend 镜像在构建期安装该子项目。

## 常用命令

生成或补齐模块骨架：

```bash
python scripts/scaffold_modules.py
```

运行仓库级测试：

```bash
pytest tests/test_module_discovery.py tests/test_scaffold_layout.py tests/test_registry.py -q
```

运行 OpenKS -> KAG schema 适配测试：

```bash
pytest tests/test_kag_schema_adapter.py -q
```

运行单模块测试：

```bash
pytest openks/kg/fact/news_kg/tests/test_news_kg.py -q
```

研报模块测试：

```bash
pytest openks/kg/fact/report_kg/tests/test_report_kg.py -q
```

## OpenKS -> KAG schema 适配

当前 `openks/common/interop/kag_schema_adapter.py` 已实现最小可用适配层，用于把 OpenKS 模块 schema 导出到 KAG 项目。

推荐调用方式：

```python
from openks.common.interop import export_module_schema_to_kag_project

result = export_module_schema_to_kag_project(
    "news_kg",
    namespace="OpenKSNews",
    project_dir="/path/to/kag/examples/OpenKSNews",
    commit=True,
    host_addr="http://127.0.0.1:8887",
    project_id=123,
)
```

当前适配规则：

- `entities` 会编译为 `EntityType`
- `relations` 会挂到对应 source 实体下面
- `fields` 会作为公共 properties 挂到每个实体下
- `text / float / int / integer / datetime / bool` 会映射到 KAG 基础类型

当前限制：

- 只支持 `describe()` 的最小实体/关系/字段结构
- 不自动生成完整 `kag_config.yaml`
- 不自动创建 KAG project
- 不会改变现有 `news_kg` builder 仍直接写 Mongo / Neo4j 的事实

因此，这个适配层当前最适合承担“定义层下发”的角色，而不是直接替换现有运行主链路。

## 推荐分工方式

以 `fact/report_kg` 为例，推荐按下面拆分：

1. 模块负责人
   - 维护 `module.toml`
   - 决定 schema 边界、依赖和状态
   - 审核 builder/reasoner/solver 最终接口
2. Schema 开发
   - 定义实体、关系、字段
   - 明确与 `base_kg` 的扩展关系
3. Builder 开发
   - 定义输入记录格式
   - 把结果写入 `entity_instances / inc_statement / inc_context / Neo4j`
4. Reasoner / Solver 开发
   - 面向消费层输出推理结果和检索结果
5. 测试与对账
   - 覆盖 schema describe、builder 主流程、solver 检索

## report_kg 开发建议

当前 `report_kg` 还是骨架。若要按资讯模式补齐，建议开发顺序：

1. 先补 `schema`
   - `ReportDocument`
   - `Company`
   - `Technology`
   - `Indicator`
   - `Conclusion`
   - `AnalystView`
2. 再补 `builder`
   - 明确消费哪个研报输入集合或队列
   - 写入 `entity_instances`
   - 写入 `inc_statement`
   - 写入 `inc_context`
   - 同步 Neo4j
3. 再补 `reasoner`
   - 观点归并
   - 指标趋势归并
   - 评级变化推理
4. 最后补 `solver`
   - 按公司、指标、观点、技术检索结构化结果

### report_kg 只在本仓开发的部分

- `openks/kg/fact/report_kg/schema/*`
- `openks/kg/fact/report_kg/builder/*`
- `openks/kg/fact/report_kg/reasoner/*`
- `openks/kg/fact/report_kg/solver/*`
- `openks/kg/fact/report_kg/tests/*`
- `openks/kg/fact/report_kg/README.md`
- `openks/kg/fact/report_kg/module.toml`

### 需要主仓 `zhilian-robot` 配合的部分

这些不应放在 `supxmind-openks` 内实现：

- 研报上传、导入、处理入口
- 把研报结果送入知识计算队列
- `report_kg` 的 API 路由
- Celery 任务和调度
- 平台总览页、数据汇聚页、知识计算页展示
- Open API / 智能服务消费 `report_kg`

## 什么时候改 common

只有在以下情况才允许改 `openks/common`：

- 两个及以上模块需要复用同一套基础能力
- 需要统一 schema、命名或注册规则
- 需要统一 Builder / Reasoner / Solver 基类

如果只是单模块业务规则，应该只改自己模块目录。

补充判断：

- 如果功能只服务 `report_kg`，就留在 `report_kg/`
- 如果 `news_kg` 和 `report_kg` 都会复用，例如 Mongo/Neo4j adapter、统一 ID 规则、章节切分工具、指标标准化工具，再进入 `openks/common`

## 合并前检查

提交模块改动前，至少确认：

1. `module.toml` 的 `owner/status/dependencies` 已更新
2. `README.md` 已同步实现范围
3. 单模块测试可运行
4. 若改了 `openks/common`，说明复用场景已经明确
5. 若模块状态仍是骨架，不要在文档或页面里宣称“已实现”
