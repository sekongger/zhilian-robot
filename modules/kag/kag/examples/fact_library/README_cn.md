# KAG 示例：事实图库（FactLibrary）

本示例用于承接 `backend/data/fact_library/processed/<dataset>` 目录下由事实库预处理 pipeline 生成的标准化文件：

- `entities/*.csv`：结构化实体
- `relations/*.csv`：结构化关系
- `texts/*.csv`：可选的文本增强输入

本示例的目标不是替代预处理 pipeline，而是把筛选后的事实数据继续导入到 OpenSPG / KAG 使用的图谱中。

## 推荐用法

现在推荐直接使用仓库根目录下的脚本，而不是手工改 `kag_config.yaml`：

1. 准备环境文件：

```bash
cp .env.example .env
```

目录：

- [modules/kag/kag/examples/fact_library/.env.example](/Users/caixudong/Downloads/zhilian-robot/modules/kag/kag/examples/fact_library/.env.example)

2. 一条命令完成启动 OpenSPG、安装 KAG、创建/恢复项目、提交 schema、导入结构化事实：

```bash
bash scripts/fact_library/import_fact_library.sh --env-file modules/kag/kag/examples/fact_library/.env --dataset 20260313_183538
```

3. 如果还要导入 `texts/*.csv` 做增强抽取，再加 `--with-text`：

```bash
bash scripts/fact_library/import_fact_library.sh --env-file modules/kag/kag/examples/fact_library/.env --dataset 20260313_183538 --with-text
```

说明：

- `scripts/fact_library/start_openspg_stack.sh`：启动 OpenSPG 本地 docker stack
- `scripts/fact_library/install_kag.sh`：创建本地 venv 并安装 KAG
- `scripts/fact_library/render_fact_library_kag_config.py`：根据 `.env` 生成 `kag_config.yaml`
- `scripts/fact_library/ensure_openspg_project.py`：确保 OpenSPG 里存在 `FactLibrary` 项目，并把 `project.id` 回填到 `kag_config.yaml`

预处理阶段还会额外产出：

- `stats/relation_summary.csv`：关系匹配统计
- `stats/unmatched_relation_candidates.csv`：未匹配名称清单

建议先看这两份文件，再决定是否直接导入全部关系。

## 1. 前置条件

1. 已完成事实库预处理：

```bash
python3 backend/scripts/run_fact_library_pipeline.py --dataset 20260313_183538
```

2. 已启动 OpenSPG server，或者直接使用上面的 `import_fact_library.sh` 自动启动。
3. 已按项目情况准备 `.env` 文件；`kag_config.yaml` 由脚本自动生成。

## 2. 提交 schema

如果你仍然要手工执行，可以在本目录执行：

```bash
knext schema commit
```

Schema 文件位于 [schema/FactLibrary.schema](./schema/FactLibrary.schema)。

## 3. 导入结构化事实

默认只导入结构化实体与结构化关系：

```bash
cd builder && python indexer.py --dataset 20260313_183538 && cd ..
```

## 4. 导入文本增强（可选）

如果需要对 `texts/*.csv` 跑 KAG 的 `schema_free_extractor` 做增强抽取：

```bash
cd builder && python indexer.py --dataset 20260313_183538 --with-text && cd ..
```

说明：

- `texts/*.csv` 已经是筛选后实体对应的高价值文本，不建议直接对原始海量库跑抽取。
- 第一版使用默认 prompt；如果后续你们要面向特定行业，建议再补自定义 prompt。
- `--with-text` 需要 `.env` 中补齐 LLM 和向量模型配置；纯结构化导入不需要。

## 5. 当前建模范围

当前 schema 覆盖以下核心类型：

- `Company`
- `Institution`
- `Investor`
- `Person`
- `Project`
- `Patent`
- `Article`
- `Achievement`
- `StandardLocal`
- `StandardIndustry`
- `StandardNation`
- `RankingList`
- `Product`
- `Technology`
- `Organization`
- `Chunk`
- `Others`

当前已落地的显式关系：

- `RankingList.includesCompany -> Company`
- `Institution.supportedBy -> Company`（仅当预处理阶段产出了该关系文件时）
- `Company.hasMainProduct -> Product`
- `Patent.appliedBy* / ownedBy* / inventedBy`
- `Project.ledBy / undertakenBy*`
- `Achievement.completedBy*`
- `Article.authoredBy / publishedBy*`

## 6. 数据来源

本示例默认读取：

- `backend/data/fact_library/processed/<dataset>/entities`
- `backend/data/fact_library/processed/<dataset>/relations`
- `backend/data/fact_library/processed/<dataset>/texts`

由 [builder/indexer.py](./builder/indexer.py) 自动解析路径。
