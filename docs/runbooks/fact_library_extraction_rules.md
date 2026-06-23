# Fact Library 数据抽取规则说明

这份文档说明当前事实库预处理 pipeline 的数据抽取逻辑。这里的“抽取”主要指结构化抽取，不是大模型语义抽取。

当前实现位置：

- [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py)

## 总体流程

当前 pipeline 会把原始 `|` 分隔事实库表处理成四类输出：

- `entities/`：通过筛选后的主实体表
- `support/`：用于关系抽取或后续事件建模的辅助表
- `texts/`：由若干文本字段拼接出的增强抽取材料
- `relations/`：从结构化字段中直接物化出的显式关系

处理顺序如下：

1. 按 `source_key` 定位原始 CSV。
2. 按实体或辅助表的单字段规则做首轮筛选。
3. 按 `id` 去重，空 `id` 记录直接丢弃。
4. 保留 `keep_columns` 作为内部工作字段。
5. 输出 `export_columns` 作为最终实体 CSV 字段。
6. 如果配置了 `text_fields`，额外生成一份 `texts/*.csv`。
7. 基于主实体和辅助表继续派生实体及关系文件。

对应代码：

- 读源文件：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L161)
- 应用筛选：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L173)
- 去重：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L223)
- 文本拼接：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L267)

## 支持的筛选操作

当前支持的筛选操作如下：

- `eq`：字段值等于指定值
- `in`：字段值属于指定集合
- `non_empty`：字段非空
- `empty`：字段为空
- `ge_int`：字段数值大于等于指定整数
- `le_int`：字段数值小于等于指定整数
- `gt_decimal`：字段数值大于指定小数
- `date_ge`：字段日期大于等于指定日期

实现见 [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L176)。

## 主实体抽取规则

### Company

- 来源表：`dw_company_info_tyc`
- 实体类型：`Company`
- 筛选规则：`status in {存续, 在业, 正常}`
- 导出字段：
  - `id`
  - `name`
  - `credit_code`
  - `status`
  - `establish_date`
  - `province`
  - `city`
  - `website`
  - `update_time`
- 内部额外保留字段：
  - `used_name`
  - `regist_capi_value_cal`
  - `insured_number`
  - `business_scope`
  - `description`
- 文本抽取字段：
  - `business_scope`
  - `description`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L42)。

### Institution

- 来源表：`dw_institution_2026`
- 实体类型：`Institution`
- 筛选规则：`domain is not empty`
- 导出字段：
  - `id`
  - `name`
  - `domain`
  - `province`
  - `city`
  - `website`
  - `level`
  - `update_time`
- 内部额外保留字段：
  - `support_org_id`
  - `support_org_name`
  - `type_1`
  - `type_2`
  - `description`
  - `achievement`
- 文本抽取字段：
  - `domain`
  - `description`
  - `achievement`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L80)。

### Investor

- 来源表：`dw_investor`
- 实体类型：`Investor`
- 筛选规则：`total_invest_amount >= 5`
- 导出字段：
  - `id`
  - `name`
  - `capital_scale`
  - `total_invest_amount`
  - `current_year_invest_amount`
  - `type`
  - `update_time`
- 内部额外保留字段：
  - `next_round_ratio`
  - `intro`
- 文本抽取字段：
  - `intro`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L117)。

### Person

- 来源表：`dw_expert`
- 实体类型：`Person`
- 筛选规则：`org is not empty`
- 导出字段：
  - `id`
  - `name`
  - `org`
  - `prof_title`
  - `position`
  - `research_fields`
  - `province`
  - `city`
  - `update_time`
- 内部额外保留字段：
  - `orgs`
  - `honors`
  - `awards`
  - `resume`
  - `url`
- 文本抽取字段：
  - `research_fields`
  - `honors`
  - `awards`
  - `resume`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L148)。

### Project

- 来源表：`dw_project`
- 实体类型：`Project`
- 筛选规则：`approval_year >= 2018`
- 导出字段：
  - `id`
  - `name`
  - `approval_num`
  - `category`
  - `approval_year`
  - `funding_value`
  - `start_date`
  - `end_date`
  - `update_time`
- 内部额外保留字段：
  - `project_leader`
  - `org`
  - `keywords`
  - `abstract_zh`
- 文本抽取字段：
  - `keywords`
  - `abstract_zh`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L186)。

### Patent

- 来源表：`dw_patent_china`
- 实体类型：`Patent`
- 筛选规则：`grant_date is not empty`
- 导出字段：
  - `id`
  - `title_cn`
  - `title`
  - `apply_code`
  - `public_code`
  - `patent_type`
  - `grant_date`
  - `apply_date`
  - `public_date`
  - `main_ipc`
  - `cited_other_times`
  - `pdf_url`
  - `update_time`
- 内部额外保留字段：
  - `applicants_norm`
  - `patentees_norm`
  - `inventors`
  - `abstract_cn`
- 文本抽取字段：
  - `abstract_cn`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L223)。

### Article

- 来源表：`dw_article`
- 实体类型：`Article`
- 筛选规则：`year >= 2018`
- 导出字段：
  - `id`
  - `title`
  - `year`
  - `subject`
  - `journal`
  - `doi`
  - `url`
  - `update_time`
- 内部额外保留字段：
  - `abstract`
  - `keywords`
  - `authors`
  - `applicants`
- 文本抽取字段：
  - `abstract`
  - `keywords`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L269)。

### Achievement

- 来源表：`dw_achievement_info`
- 实体类型：`Achievement`
- 筛选规则：`publish_time >= 2018-01-01`
- 导出字段：
  - `id`
  - `name`
  - `type`
  - `publish_time`
  - `technical_field`
  - `application_field`
  - `technology_maturity`
  - `url`
  - `update_time`
- 内部额外保留字段：
  - `unit`
  - `person`
  - `content`
  - `ipr`
  - `honors`
- 文本抽取字段：
  - `technical_field`
  - `application_field`
  - `content`
  - `ipr`
  - `honors`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L305)。

### StandardLocal

- 来源表：`dw_standard_local`
- 实体类型：`StandardLocal`
- 筛选规则：`abolish_date is empty`
- 导出字段：
  - `id`
  - `standard_code`
  - `standard_name`
  - `standard_level`
  - `local_name`
  - `publish_date`
  - `effective_date`
  - `status`
  - `url_link`
  - `update_time`
- 内部额外保留字段：
  - `abolish_date`
  - `industry_class`
  - `standard_type`
  - `publish_department`
  - `drafting_unit`
  - `details`
- 文本抽取字段：
  - `details`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L343)。

### StandardIndustry

- 来源表：`dw_standard_industry`
- 实体类型：`StandardIndustry`
- 筛选规则：`status == 现行`
- 导出字段：
  - `id`
  - `standard_code`
  - `standard_name`
  - `standard_level`
  - `domain_code`
  - `domain_name`
  - `publish_date`
  - `effective_date`
  - `status`
  - `url_link`
  - `update_time`
- 内部额外保留字段：
  - `abolish_date`
  - `industry_class`
  - `standard_type`
  - `publish_department`
  - `drafting_unit`
  - `details`
- 文本抽取字段：
  - `details`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L385)。

### StandardNation

- 来源表：`dw_standard_nation`
- 实体类型：`StandardNation`
- 筛选规则：`status == 现行`
- 导出字段：
  - `id`
  - `standard_code`
  - `standard_name`
  - `standard_level`
  - `publish_date`
  - `effective_date`
  - `status`
  - `url_link`
  - `update_time`
- 内部额外保留字段：
  - `abolish_date`
  - `standard_type`
  - `technical_unit`
  - `effect_unit`
  - `competent_department`
  - `drafting_unit`
  - `details`
- 文本抽取字段：
  - `details`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L429)。

### RankingList

- 来源表：`dw_list`
- 实体类型：`RankingList`
- 筛选规则：`is_official == 1`
- 导出字段：
  - `id`
  - `name`
  - `publish_organization`
  - `publish_time`
  - `first_sort`
  - `second_sort`
  - `is_official`
  - `url`
  - `update_time`
- 内部额外保留字段：
  - `description`
  - `indicator`
  - `lz_industry_chain`
- 文本抽取字段：
  - `description`
  - `indicator`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L470)。

## 辅助表抽取规则

这些表不会直接作为主实体入图，但会参与关系抽取、派生实体生成或后续事件建模。

### CompanyMainProduct

- 来源表：`dw_company_main_product`
- 类型：`CompanyMainProduct`
- 保留字段：
  - `id`
  - `name`
  - `credit_code`
  - `main_product`
  - `update_time`
- 筛选规则：`main_product is not empty`
- 文本抽取字段：
  - `main_product`

### CompanyBidder

- 来源表：`dw_company_bidder`
- 类型：`CompanyBidder`
- 保留字段：
  - `id`
  - `title`
  - `deal_money`
  - `public_date`
  - `tender`
  - `bidder`
  - `project_name`
  - `industry`
  - `project_address`
  - `tender_type`
  - `bidder_type`
  - `update_time`
- 筛选规则：`deal_money > 0`
- 文本抽取字段：
  - `title`
  - `project_name`

### ListDetail

- 来源表：`dw_list_detail`
- 类型：`ListDetail`
- 保留字段：
  - `id`
  - `pid`
  - `name`
  - `sort_order`
  - `cid`
  - `company_name`
  - `credit_code`
  - `main_product`
  - `industry`
  - `indicator_value`
  - `indicator_unit`
  - `update_time`
- 筛选规则：`sort_order <= 100`
- 文本抽取字段：
  - `main_product`
  - `industry`
  - `indicator_value`

定义见 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L509)。

## 文本抽取逻辑

当前 `texts/*.csv` 的生成不是大模型抽取，而是字段拼接。

逻辑如下：

1. 遍历当前类型配置的 `text_fields`。
2. 对每个非空字段按 `field: value` 形式拼接。
3. 生成一条文本记录，包含：
   - `id`
   - `name`
   - `entity_type`
   - `text`
   - `source_table`
   - `update_time`

用途：

- 作为后续 KAG / OpenKS 增强抽取的输入
- 不直接作为最终事实图谱节点

实现见 [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L267)。

## 派生实体抽取逻辑

当前唯一自动派生的新实体是 `Product`。

来源：

- `dw_company_main_product.main_product`

处理方式：

1. 只处理已经保留下来的企业记录。
2. 将 `main_product` 按常见分隔符拆分。
3. 对产品名称做简单标准化。
4. 去重后生成稳定 ID。
5. 输出到 `entities/product.csv`。

输出字段：

- `id`
- `name`
- `desc`
- `semanticType`

实现见 [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L503)。

## 关系抽取逻辑

当前关系抽取同样是结构化规则抽取，不依赖大模型。

### 基本思路

1. 先给已有主实体构建精确名称索引。
2. 对列表型字段做切分，对 JSON 风格字段做解析。
3. 通过企业/机构名称启发式判断类型。
4. 将原始名称匹配到主实体 ID。
5. 生成标准关系文件：
   - `s_id`
   - `s_type`
   - `p`
   - `o_id`
   - `o_type`
   - `properties`

相关实现：

- 名称标准化：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L301)
- 多值切分：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L309)
- 数组解析：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L326)
- 企业/机构粗分类：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L346)
- 名称索引构建：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L441)
- 关系主流程：[pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L551)

### 当前已实现的关系类型

- `Institution -> supportedBy -> Company`
- `RankingList -> includesCompany -> Company`
- `Company -> hasMainProduct -> Product`
- `Patent -> appliedByCompany -> Company`
- `Patent -> appliedByInstitution -> Institution`
- `Patent -> ownedByCompany -> Company`
- `Patent -> ownedByInstitution -> Institution`
- `Patent -> inventedBy -> Person`
- `Project -> ledBy -> Person`
- `Project -> undertakenByCompany -> Company`
- `Project -> undertakenByInstitution -> Institution`
- `Achievement -> completedByCompany -> Company`
- `Achievement -> completedByInstitution -> Institution`
- `Achievement -> completedByPerson -> Person`
- `Article -> authoredBy -> Person`
- `Article -> publishedByCompany -> Company`
- `Article -> publishedByInstitution -> Institution`

具体实现分布在：

- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L594)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L647)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L677)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L707)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L801)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L859)
- [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L918)

## quick 模式的缩量逻辑

如果使用 `quick` profile，除了首轮筛选以外，还会在关系生成之后进一步缩量。

规则如下：

1. 先统计各实体在关系中的度数。
2. 对每类实体只保留关系度最高的前 N 个 ID。
3. 只保留这些 ID 之间仍然连通的关系。
4. 回写新的 `entities/*.csv`、`relations/*.csv`、`texts/*.csv`。

当前 quick 上限定义在 [specs.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/specs.py#L28)：

- `Company`: 200
- `Institution`: 300
- `Person`: 800
- `Project`: 300
- `Patent`: 800
- `Article`: 300
- `Achievement`: 500
- `Product`: 200
- `RankingList`: 20

缩量实现见 [pipeline.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/fact_library_pipeline/pipeline.py#L982)。

## 当前抽取逻辑的特点

优点：

- 规则清晰，容易解释
- 跑速快，适合大批量结构化数据
- 输出格式稳定，方便对接 OpenSPG / KAG
- 能直接生成实体、文本和关系三类数据

当前局限：

- 高度依赖源表字段质量
- 关系匹配目前以精确名称匹配为主
- 别名、歧义、跨表口径差异还需要后续补规则
- 还没有引入事件抽取和概念层抽取
- 还没有在这条链路里启用大模型语义抽取

## 一句话总结

当前事实库抽取逻辑可以概括为：

**按表规则筛实体，按字段拼文本，按名称匹配抽关系，少量派生新实体。**

这是一条面向结构化事实库的知识装配线，重点是先把基础事实层稳定产出，再接 KAG / OpenKS 做后续增强。
