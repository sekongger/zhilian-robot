# IncCoreV2 Schema 与 Wikidata 字段映射说明

本文档说明当前 wiki pipeline 如何按照 [IncCoreV2.schema](/Users/caixudong/Downloads/zhilian-robot/IncCoreV2.schema) 的字段定义，将 Wikidata 中已有字段映射为图节点属性与关系。

## 1. 设计原则

当前映射遵循三个原则：

1. 先严格对齐 `IncCoreV2.schema` 已定义字段，不额外发明企业画像字段。
2. 能由 Wikidata 原始字段直接给出的属性，优先做一对一映射。
3. 不能稳定从 Wikidata 直接拿到的字段，先留空，不做主观拼装。

当前映射入口有两层：

- [IncIndustryWiki.routing.schema.yaml](/Users/caixudong/Downloads/zhilian-robot/configs/industry_wiki/IncIndustryWiki.routing.schema.yaml)
  负责把 Wikidata property 映射成 `IncCoreV2` 的属性名或关系名。
- [graph_mapper.py](/Users/caixudong/Downloads/zhilian-robot/backend/app/wiki_industry_pipeline/graph_mapper.py)
  负责把候选实体基础字段、中英文 label、alias 和 routed claim 合成为最终图节点。

## 2. 当前已实现的实体映射

### 2.1 Enterprise

`IncCoreV2.schema` 定义的企业字段中，当前已接入：

| IncCoreV2 字段 | 来源 | 当前实现方式 |
| --- | --- | --- |
| `name` | Wikidata label | 候选实体主 label，优先中文 |
| `officialName` | `P1448` / label | 有 `P1448` 时使用 `P1448`，否则初始化为主 label |
| `shortName` | `P1813` | routing schema intrinsic 映射 |
| `alias` | Wikidata aliases | 候选实体 aliases 直接写入 |
| `description` | Wikidata description | 候选实体 description 直接写入 |
| `nameEn` | Wikidata `labels.en` | graph mapper 从 candidate labels 中抽取英文名 |
| `officialWebsite` | `P856` | routing schema intrinsic 映射，MultiValue 存储 |
| `inception` | `P571` | routing schema intrinsic 映射，并标准化为 `YYYY-MM-DD` |
| `companyScale` | `P1128` | routing schema intrinsic 映射，当前以字符串形式写入 |

`Enterprise` 当前已接入的关系：

| IncCoreV2 关系 | Wikidata 字段 | 当前实现 |
| --- | --- | --- |
| `belongsToIndustry` | `P452` | 企业 -> 行业 |
| `region` | `P159` / `P17` / `P131` / `P276` | 企业 -> 区域，统一收敛到 `region` |
| `shareholder` | `P127` | 企业 -> 企业 |
| `childOrganization` | `P355` | 企业 -> 企业 |
| `manufacturer` 反向补边 | `P1056` | 生成 `ProductModel -> manufacturer -> Enterprise` |

`Enterprise` 当前未实现但 schema 中已定义的字段：

- `unifiedSocialCreditCode`
- `status`
- `mainBusiness`
- `businessScope`

这几个字段当前不能稳定从 Wikidata 通用 claim 直接拿到，后续需要额外对照 property 或使用文本补全。

### 2.2 ProductModel

`ProductModel` 当前已接入：

| IncCoreV2 字段 | 来源 | 当前实现方式 |
| --- | --- | --- |
| `name` | Wikidata label | 候选实体主 label |
| `officialName` | `P1448` / label | 有 `P1448` 时使用 `P1448` |
| `shortName` | `P1813` | routing schema intrinsic 映射 |
| `alias` | Wikidata aliases | 直接写入 |
| `description` | Wikidata description | 直接写入 |
| `nameEn` | Wikidata `labels.en` | graph mapper 提取英文名 |
| `brand` | `P1716` | routing schema intrinsic 映射 |
| `model` | `P528` | routing schema intrinsic 映射 |
| `publishDate` | `P577` | routing schema intrinsic 映射，并标准化为 `YYYY-MM-DD` |

`ProductModel` 当前已接入的关系：

| IncCoreV2 关系 | Wikidata 字段 | 当前实现 |
| --- | --- | --- |
| `manufacturer` | `P176` / `P178` | 产品型号 -> 企业 |
| `belongsToProduct` | `P31` / `P279` | 产品型号 -> 标准产品 |

`ProductModel` 当前未实现但 schema 中已定义的字段：

- `series`
- `specification`
- `productLifecycleStatus`

### 2.3 Product

`Product` 当前主要作为标准产品/上位产品节点出现，已接入：

| IncCoreV2 字段 | 来源 | 当前实现方式 |
| --- | --- | --- |
| `name` | Wikidata label | stub 或候选节点名称 |
| `officialName` | `P1448` / label | 若后续进入 intrinsic 路由可直接支持 |
| `shortName` | `P1813` | 路由规则已可扩展 |
| `alias` | Wikidata aliases | 候选时可直接写入 |
| `description` | Wikidata description | 候选时可直接写入 |

`Product` 当前已接入的关系：

| IncCoreV2 关系 | Wikidata 字段 | 当前实现 |
| --- | --- | --- |
| `belongsToIndustry` | 预留 | 当前尚未补齐 |
| `subclassOf` | `P279` | 可进一步扩为 Product 层级 |

当前 `Product` 还偏轻，主要作为 `ProductModel.belongsToProduct` 的承接节点。

### 2.4 Industry

`Industry` 当前已接入：

| IncCoreV2 字段 | 来源 | 当前实现方式 |
| --- | --- | --- |
| `name` | Wikidata label | 候选主 label |
| `officialName` | `P1448` / label | routing schema intrinsic 映射 |
| `shortName` | `P1813` | routing schema intrinsic 映射 |
| `alias` | Wikidata aliases | 候选时可直接写入 |
| `description` | Wikidata description | 候选时可直接写入 |

### 2.5 Region

`Region` 当前已接入：

| IncCoreV2 字段 | 来源 | 当前实现方式 |
| --- | --- | --- |
| `name` | Wikidata label | 候选主 label |
| `officialName` | `P1448` / label | routing schema intrinsic 映射 |
| `shortName` | `P1813` | routing schema intrinsic 映射 |
| `alias` | Wikidata aliases | 候选时可直接写入 |
| `description` | Wikidata description | 候选时可直接写入 |

`Region` 当前已接入的关系：

| IncCoreV2 关系 | Wikidata 字段 | 当前实现 |
| --- | --- | --- |
| `belongToRegion` | `P131` / `P17` | 区域层级关系 |

## 3. 当前映射覆盖的 Wikidata 属性

当前已经进入 routing schema 的核心属性如下：

| Wikidata Property | 含义 | 映射去向 |
| --- | --- | --- |
| `P1448` | official name | `officialName` |
| `P1813` | short name | `shortName` |
| `P571` | inception | `inception` |
| `P856` | official website | `officialWebsite` |
| `P1128` | employees | `companyScale` |
| `P452` | industry | `belongsToIndustry` |
| `P1056` | product produced | 反向生成 `manufacturer` |
| `P127` | owned by | `shareholder` |
| `P355` | subsidiary | `childOrganization` |
| `P159` | headquarters location | `region` |
| `P17` | country | `region` / `belongToRegion` |
| `P131` | located in administrative territorial entity | `region` / `belongToRegion` |
| `P276` | location | `region` |
| `P176` | manufacturer | `manufacturer` |
| `P178` | developer | `manufacturer` |
| `P1716` | brand | `brand` |
| `P528` | catalog code / model | `model` |
| `P577` | publication date | `publishDate` |

## 4. 当前还缺的映射

和 `IncCoreV2.schema` 比，当前最值得继续补的字段是：

### Enterprise

- `status`
- `mainBusiness`
- `businessScope`
- `unifiedSocialCreditCode`

### ProductModel

- `series`
- `specification`
- `productLifecycleStatus`

### Product

- `classificationLevel`
- `isLeaf`
- `extensionBasis`
- `belongsToIndustry`
- `subclassOf`
- `rawMaterial / component / equipment / auxiliaryMaterial / applicationTerminal`

## 5. 下一步建议

下一步最合适的工作不是再设计新 DTO，而是继续补 schema 映射：

1. 先把 `Enterprise / ProductModel / Product / Region / Technology` 的字段映射表补全。
2. 对每个字段标注：
   - 可直接由 Wikidata claim 提供
   - 需要文本拼装
   - 当前无法稳定获得
3. 基于补全后的映射表，重新跑样本导图并检查字段丰富度。

这样后续生成的“常识层企业节点”就不是只有几个骨架关系，而是会逐步逼近 `IncCoreV2.schema` 中本来定义好的字段集合。
