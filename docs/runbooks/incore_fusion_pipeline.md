# IncCore Fusion Pipeline 运行说明

## 1. 入口脚本

脚本位置：

- [run_incore_fusion_pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/scripts/run_incore_fusion_pipeline.py)

示例输入：

- [sample_records.jsonl](/Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/examples/sample_records.jsonl)

流程解释：

- [incore_fusion_pipeline_explained.md](/Users/caixudong/Downloads/zhilian-robot/docs/runbooks/incore_fusion_pipeline_explained.md)

## 2. 输入格式

脚本读取 `JSONL` 或 `JSON 数组`，每条记录都要满足 `SourceRecordDTO` 外层结构：

```json
{
  "source_system": "fact_library | mongo_news | graphiti",
  "source_table": "dw_company_info_tyc",
  "record_id": "91310000X",
  "record_type": "entity | relation | document | chunk | event | concept_seed",
  "payload": {}
}
```

推荐使用 `JSONL`，每行一条记录。

## 3. Dry Run

只跑融合，不写 OpenSPG：

```bash
PYTHONPATH=/Users/caixudong/Downloads/zhilian-robot/backend \
/Users/caixudong/Downloads/zhilian-robot/.venv-kag/bin/python \
/Users/caixudong/Downloads/zhilian-robot/backend/scripts/run_incore_fusion_pipeline.py \
  --input /Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/examples/sample_records.jsonl \
  --project IncCore \
  --namespace IncCore \
  --project-id 3 \
  --batch-id incore_cli_dryrun
```

## 4. Live Import

写入真实 OpenSPG：

```bash
PYTHONPATH=/Users/caixudong/Downloads/zhilian-robot/backend \
/Users/caixudong/Downloads/zhilian-robot/.venv-kag/bin/python \
/Users/caixudong/Downloads/zhilian-robot/backend/scripts/run_incore_fusion_pipeline.py \
  --input /Users/caixudong/Downloads/zhilian-robot/backend/app/incore_fusion_pipeline/examples/sample_records.jsonl \
  --project IncCore \
  --namespace IncCore \
  --project-id 3 \
  --batch-id incore_cli_live \
  --live
```

## 5. 当前默认能力

当前脚本已经支持：

- 企业主实体对齐
  - 优先使用 `credit_code / code`
  - 其次使用标准名和企业简称
- 区域实体生成
  - 从企业 `province/city`
  - 从事件 `location`
- 事件融合
  - `CompanyFinancingEvent`
  - `CompanyCooperationEvent`
  - `GovernmentPublishPolicyEvent`
  - 泛化 `Event`
- 概念挂载
  - `CompanyCategory`
  - `IndustrySector`
  - `RegionCategory`
  - `EventCategory`
  - `ImpactCategory`

## 6. 当前 OpenSPG 项目

当前验证项目：

- `project_id = 3`
- `namespace = IncCore`

## 7. 注意事项

- [IncCore.v2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCore.v2.schema) 已经通过 knext 成功提交到 `project_id=3`。
- 真实写图使用的是 OpenSPG 公共接口：
  - `/public/v1/graph/upsertVertex`
  - `/public/v1/graph/upsertEdge`
- 如果不显式传 `--project-id`，脚本会走运行时 importer 的环境变量兜底逻辑。
