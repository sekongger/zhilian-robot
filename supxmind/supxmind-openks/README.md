# supxmind-openks

`supxmind-openks` 是 SupXmind MaaS 层的知识计算引擎仓。

## 定位

- 承接产业网链基础定义、要素 schema 组织与知识库工程落仓。
- 复用 KAG 的抽取/融合能力，编排 OpenSPG 的图谱主存与语义服务。
- 对上层智能体与应用输出 Builder / Reasoner / Solver 的知识计算结果。

## 当前落地内容

- `openks/common`：公共 schema、基类、基于 `module.toml` 的模块发现。
- `openks/common/interop`：OpenKS -> KAG schema 适配，可把模块 `describe()` 编译成 `.schema` 并导出到 KAG 项目目录。
- `openks/kg`：事实类、认知类、决策类 KG 目录骨架与模块元数据。
- `openks/cross`：跨 KG 调度层骨架。
- `openks/entry`：启动、CLI、API 入口骨架。
- `tests`：最小回归测试，验证 discovery 与骨架布局可用。

## 仓库原则

- 主结构固定为 `common + kg + cross + entry + tests + docs`。
- 每个 KG 独立维护 `module.toml / schema / builder / reasoner / solver / config / tests / README`。
- 具体业务实现后续由各模块负责人在对应目录继续补全。

## 协作约定

- `module.toml` 是模块元数据的单一真相源，用于展示 owner、status、dependencies 和 summary。
- `README.md` 负责人读，`module.toml` 给程序读，不要反过来。
- 模块级测试可以直接执行，例如：`pytest openks/kg/fact/news_kg/tests/test_news_kg.py -q`
- 若新增模块，先补 `module.toml` 和骨架，再接入具体业务逻辑。

## OpenKS -> KAG Schema 适配

当前仓库已经提供最小可用的 schema 适配能力：

- 从 OpenKS 模块加载 `BaseSchema.describe()`
- 编译为 KAG / OpenSPG 可接受的 `.schema` DSL
- 导出到 KAG 项目目录的 `schema/$namespace.schema`
- 可选调用 KAG `SPGSchemaMarkLang.sync_schema()` 直接提交

示例：

```python
from openks.common.interop import export_module_schema_to_kag_project

result = export_module_schema_to_kag_project(
    "news_kg",
    namespace="OpenKSNews",
    project_dir="/path/to/kag/examples/OpenKSNews",
    commit=False,
)
```

说明：

- 这次实现只打通了 schema 适配，不会替换现有 `news_kg -> Mongo/Neo4j` 主链路。
- 也就是说，当前已实现的是“定义层适配”，不是“运行时全面切换到 KAG”。
- 详细说明见 `docs/openks-kag-schema-adapter.md`。
