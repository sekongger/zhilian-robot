# Fact Library Pipeline

原始数据目录：

- `backend/data/fact_library/raw/<dataset_name>/`

当前已接入数据集：

- `backend/data/fact_library/raw/20260313_183538/`

这条 pipeline 的目标不是直接写图，而是先把大批量事实库数据变成三类标准文件：

- `entities/`：筛选后的实体主表
- `support/`：适合后续做关系抽取或事件建模的辅助表
- `texts/`：适合后续交给 KAG / OpenKS 做抽取增强的文本材料
- `relations/`：当前已能直接物化的显式关系

更详细的数据筛选与抽取规则说明见：

- [fact_library_extraction_rules.md](/Users/caixudong/Downloads/zhilian-robot/docs/runbooks/fact_library_extraction_rules.md)

## Run

在项目根目录执行：

```bash
python3 backend/scripts/run_fact_library_pipeline.py --dataset 20260313_183538
```

如果只是想快速跑通完整链路，推荐直接生成小规模连通子图版本：

```bash
python3 backend/scripts/run_fact_library_pipeline.py \
  --dataset 20260313_183538 \
  --output-dataset 20260313_183538_quick \
  --profile quick
```

`quick` 模式会做两件事：

- `entities/*.csv` 只保留真正的实体信息字段，不再夹带大量原始关系字段
- 基于已物化的关系自动裁剪出一个小规模、可连通的子图，适合快速验证 OpenSPG / KAG 全流程

## Output

输出目录：

- `backend/data/fact_library/processed/20260313_183538/entities/`
- `backend/data/fact_library/processed/20260313_183538/support/`
- `backend/data/fact_library/processed/20260313_183538/texts/`
- `backend/data/fact_library/processed/20260313_183538/relations/`
- `backend/data/fact_library/processed/20260313_183538/stats/summary.csv`
- `backend/data/fact_library/processed/20260313_183538/stats/relation_summary.csv`
- `backend/data/fact_library/processed/20260313_183538/stats/unmatched_relation_candidates.csv`
- `backend/data/fact_library/processed/20260313_183538/manifest.json`

快速版输出目录：

- `backend/data/fact_library/processed/20260313_183538_quick/entities/`
- `backend/data/fact_library/processed/20260313_183538_quick/relations/`
- `backend/data/fact_library/processed/20260313_183538_quick/texts/`
- `backend/data/fact_library/processed/20260313_183538_quick/stats/summary.csv`

## Current Filter Rules

当前版本按单字段做首轮筛选：

- `Company`: `status in {存续, 在业, 正常}`
- `Institution`: `domain is not empty`
- `Investor`: `total_invest_amount >= 5`
- `Person`: `org is not empty`
- `Project`: `approval_year >= 2018`
- `Patent`: `grant_date is not empty`
- `Article`: `year >= 2018`
- `Achievement`: `publish_time >= 2018-01-01`
- `StandardLocal`: `abolish_date is empty`
- `StandardIndustry`: `status == 现行`
- `StandardNation`: `status == 现行`
- `RankingList`: `is_official == 1`
- `CompanyMainProduct`: `main_product is not empty`
- `CompanyBidder`: `deal_money > 0`
- `ListDetail`: `sort_order <= 100`

## Next Step

这条 pipeline 的输出适合接在图谱构建链路前面：

1. `entities/*.csv` 走结构化实体导入。
2. `relations/*.csv` 走结构化关系导入。
3. `texts/*.csv` 只对核心实体跑 KAG / OpenKS 做增强抽取。

当前已物化的关系包括：

- `institution_supported_by_company`
- `ranking_list_includes_company`
- `company_has_main_product`
- `patent_applied_by_company`
- `patent_applied_by_institution`
- `patent_owned_by_company`
- `patent_owned_by_institution`
- `patent_invented_by_person`
- `project_led_by_person`
- `project_undertaken_by_company`
- `project_undertaken_by_institution`
- `achievement_completed_by_company`
- `achievement_completed_by_institution`
- `achievement_completed_by_person`
- `article_authored_by_person`
- `article_published_by_company`
- `article_published_by_institution`

## Relation Quality

当前版本在关系物化阶段额外做了三件事：

- 只连到已经通过筛选、并且实际会导入图库的实体 ID
- 对企业 / 机构同名场景做了简单去歧义，例如 `大学 / 学院 / 研究院 / 实验室` 优先按机构处理，`有限公司 / 股份有限公司 / 集团` 优先按企业处理
- 导出匹配统计和未匹配名单，方便后续补规则

建议优先查看：

- `stats/relation_summary.csv`：每类关系候选数、匹配数、未匹配数
- `stats/unmatched_relation_candidates.csv`：没有连上的原始名称及出现次数

已提供对应的 KAG example：

- [modules/kag/kag/examples/fact_library/README_cn.md](/Users/caixudong/Downloads/zhilian-robot/modules/kag/kag/examples/fact_library/README_cn.md)

推荐顺序：

1. 先执行事实库预处理。
2. 再提交 [FactLibrary.schema](/Users/caixudong/Downloads/zhilian-robot/modules/kag/kag/examples/fact_library/schema/FactLibrary.schema)。
3. 最后运行 [builder/indexer.py](/Users/caixudong/Downloads/zhilian-robot/modules/kag/kag/examples/fact_library/builder/indexer.py) 做结构化导入，必要时再追加 `--with-text` 做文本增强。

如果要快速验证整套知识构建流程，建议直接使用 quick 配置：

```bash
bash scripts/fact_library/import_fact_library.sh \
  --env-file modules/kag/kag/examples/fact_library/.env.quick \
  --dataset 20260313_183538_quick \
  --skip-install-kag
```

说明：

- `modules/kag/kag/examples/fact_library/.env.quick` 使用独立 namespace：`FactLibraryQuick`
- 这样不会污染原来的 `FactLibrary` 项目
