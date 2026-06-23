# OpenKS -> KAG Schema 适配说明

## 目标

把 OpenKS 模块里的 Python `describe()` 结构编译成 KAG / OpenSPG 可接受的 `.schema` DSL，并写入 KAG 项目目录；必要时可直接触发 `SPGSchemaMarkLang.sync_schema()`。

当前实现文件：

- `openks/common/interop/kag_schema_adapter.py`

## 当前支持的能力

1. 按模块名加载 OpenKS schema
   - 通过 registry 定位模块目录
   - 动态导入模块 package
   - 查找 `BaseSchema` 子类并实例化
2. 编译 `.schema`
   - `entities` -> `EntityType`
   - `relations` -> source 实体下的 relation 定义
   - `fields` -> 挂到每个实体的公共 properties
3. 导出到 KAG 项目目录
   - 输出到 `schema/$namespace.schema`
4. 可选提交
   - `commit=True` 时会动态导入 KAG 的 `SPGSchemaMarkLang`
   - 调用 `sync_schema()` 提交到 OpenSPG

## 用法

### 1. 只生成 `.schema`

```python
from openks.common.interop import compile_module_schema

schema_text = compile_module_schema("news_kg", namespace="OpenKSNews")
print(schema_text)
```

### 2. 导出到 KAG 项目目录

```python
from openks.common.interop import export_module_schema_to_kag_project

result = export_module_schema_to_kag_project(
    "news_kg",
    namespace="OpenKSNews",
    project_dir="/path/to/kag/examples/OpenKSNews",
)

print(result["schema_path"])
```

### 3. 导出并提交到 OpenSPG

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

print(result["committed"])
```

## 当前边界

这次实现只解决 schema 适配，不改现有 `news_kg` 运行主链路。也就是说：

- 已实现：`OpenKS describe() -> KAG .schema`
- 已实现：`OpenKS module -> schema/$namespace.schema`
- 已实现：可选 `sync_schema()` 提交
- 未实现：自动生成完整 `kag_config.yaml`
- 未实现：自动创建 KAG project
- 未实现：把 OpenKS builder 自动切换到 KAG builder
- 未实现：把 OpenKS solver 自动切换到 KAG solver

## 当前最适合的用法

把 OpenKS 作为“业务定义层”，把 KAG 作为“schema / project / retrieval 框架”：

1. 在 OpenKS 内维护业务 KG 的 `describe()`
2. 通过适配器生成 `.schema`
3. 提交到目标 KAG / OpenSPG 项目
4. 后续再逐步把 builder / solver 迁移到真正按 project schema 运行
