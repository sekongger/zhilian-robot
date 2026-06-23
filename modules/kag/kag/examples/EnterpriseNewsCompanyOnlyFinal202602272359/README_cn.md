# EnterpriseNews 示例（企业实体 schema + `new1.md` 实体抽取）

本目录包含以下文件：

1. `schema/EnterpriseNews.schema`：企业场景 schema
2. `kag_config.yaml`：模型与构建链路配置
3. `builder/indexer.py`：执行构建任务脚本
4. `builder/data/new1.md`：抽取输入语料
5. `builder/data/new1_entity_extraction.json`：当前离线抽取结果

## 可执行步骤（完整命令版）

### 0) 安装并确认命令可用

```bash
cd /Users/youfang/Documents/openspg/KAG
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
which knext
which kag
```

### 1) 进入 EnterpriseNews 示例

```bash
cd /Users/youfang/Documents/openspg/KAG/kag/examples/EnterpriseNews
```

### 2) 配置模型参数（必做）

编辑配置文件中的 `api_key/base_url/model`：

```bash
vim kag_config.yaml
```

### 3) 初始化项目到 OpenSPG

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### 4) 提交 schema

```bash
knext schema commit
```

### 5) 执行实体抽取与入图

```bash
cd builder
python indexer.py
```

### 6) 查看抽取统计与 checkpoint

```bash
ls -lah ckpt
less ckpt/kag_checkpoint_0_1.ckpt
wc -l ckpt/kag_checkpoint_0_1.ckpt
```

### 7) 返回项目目录

```bash
cd ..
```

## 这里调用的大模型是什么

以当前 `kag_config.yaml` 默认值为准：

1. `openie_llm.model = qwen2.5-7b-instruct-1m`
   用途：`schema_free_extractor` 在 `indexer.py` 构建时做 NER / 三元组抽取。
2. `chat_llm.model = qwen2.5-72b-instruct`
   用途：主要给 solver/推理问答链路使用，本示例仅跑 `builder/indexer.py` 时通常不会用到。
3. `vectorize_model.model = BAAI/bge-m3`
   用途：向量化（节点/文本 embedding）。

## 说明

`builder/data/new1_entity_extraction.json` 是本仓库里已经生成好的离线结构化结果；你执行上述命令后，会得到基于在线模型调用的构建与抽取结果（写入图数据库并产生日志/checkpoint）。
