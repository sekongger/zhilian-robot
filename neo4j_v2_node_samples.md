# Neo4j v2 节点类型样本

说明：每个类型展示 1 条样本；若当前库没有该类型节点，会标注“暂无样本”。

## EconomicSector

暂无样本

## IndustryGroup

暂无样本

## Industry

```json
{
  "summary": "机器人交警用于警务场景",
  "pageRank": 0.5914599233244573,
  "momentum_updated_at": "2026-04-29T04:08:39.338355000+00:00",
  "attributes__应用功能": "交通管理等警务场景",
  "created_at": "2026-04-29T04:07:34.095232000+00:00",
  "attributes__应用案例": "全球首个大型赛事\"机器人交警\"",
  "uuid": "be6499bd-12e2-4d4e-a5a4-16f016cd0bf1",
  "labels": [
    "Entity",
    "IndustryNode"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "_schema_migrated_at": "2026-05-09T04:37:10.810449+00:00",
  "name": "警务场景",
  "entity_types": [
    "Entity",
    "IndustryNode"
  ],
  "attributes__合作方": "魔法原子与无锡市公安局",
  "communityId": 427,
  "attributes__推广计划": "计划推广至全国"
}
```

## ProductTerm

暂无样本

## Product

```json
{
  "summary": "阿里巴巴高德 released the quadruped robot named 高德途途\n高德途途 is based on the ABot technology system\n高德途途 assists visually impaired people with obstacle avoidance and navigation tasks using ABot technology\nABot achieved SOTA results in 15 global benchmarks and was trained on millions of multimodal data points across thousands of scenarios",
  "pageRank": 0.9203542241869351,
  "momentum_updated_at": "2026-05-09T05:09:55.025476000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "高德途途",
  "created_at": "2026-05-09T05:04:56.953062000+00:00",
  "description": "四足机器人，协助视障人士完成避障、穿行等任务",
  "communityId": 497,
  "uuid": "ae09e3ef-24a5-4d63-90d0-1faca27b4e5a",
  "labels": [
    "Entity",
    "Product"
  ]
}
```

## ProductModel

```json
{
  "summary": "SanDisk external SSD is a model of solid-state drives\nSanDisk external SSD prices increased by 200%",
  "pageRank": 0.5531526928804541,
  "momentum_updated_at": "2026-05-09T05:04:02.659842000+00:00",
  "description": "价格自2025年12月持续上涨，NVMe固态硬盘价格达2-3倍。闪迪外置固态硬盘涨价200%。",
  "created_at": "2026-05-09T05:02:51.621818000+00:00",
  "uuid": "28854b0d-fea8-4f13-bb45-1dfa93e75f0e",
  "labels": [
    "ProductModel",
    "Entity"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "name": "闪迪外置固态硬盘",
  "communityId": 489,
  "brand": "闪迪"
}
```

## Enterprise

```json
{
  "summary": "Micron is one of three major NAND manufacturers who dominate the market\nMicron's NAND revenue increased 169% after exiting consumer market",
  "pageRank": 0.5586742135805627,
  "momentum_updated_at": "2026-05-09T05:04:02.771463000+00:00",
  "mainBusiness": "NAND厂商",
  "created_at": "2026-05-09T05:02:51.621916000+00:00",
  "uuid": "145f14ef-eefd-4017-b6c7-d68a855e0f37",
  "labels": [
    "Entity",
    "Enterprise"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "name": "美光",
  "communityId": 408,
  "status": "已退出消费级市场"
}
```

## Technology

```json
{
  "summary": "阿里巴巴高德 developed the full-stack embodied AGI technology system ABot\n高德途途 is based on the ABot technology system\n高德途途 assists visually impaired people with obstacle avoidance and navigation tasks using ABot technology\nABot achieved SOTA results in 15 global benchmarks and was trained on millions of multimodal data points across thousands of scenarios",
  "pageRank": 0.9203542241869351,
  "momentum_updated_at": "2026-05-09T05:09:55.009530000+00:00",
  "description": "全球首个AGI全栈具身技术体系，基于上万场景和千万级多模态数据，其模型已在全球15项测试中获SOTA",
  "created_at": "2026-05-09T05:04:56.953050000+00:00",
  "uuid": "1e61ef33-69fd-41aa-8a59-8d5fc81ae7ec",
  "labels": [
    "Entity",
    "Technology"
  ],
  "applicationScenario": [
    "协助视障人士完成避障、穿行等任务"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "name": "ABot",
  "entity_types": [
    "Entity",
    "Technology"
  ],
  "communityId": 497,
  "belongsToProduct": "高德途途"
}
```

## Patent

暂无样本

## Organization

```json
{
  "summary": "Hitch Open and 智元 co-organized the HOPE AI challenge at APC 2026\nHitch Open initiated the HOPE AI challenge",
  "pageRank": 0.8168197076052347,
  "momentum_updated_at": "2026-05-09T05:10:25.414631000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "Hitch Open",
  "created_at": "2026-05-09T05:09:58.549246000+00:00",
  "description": "全球首个AI自主决策机器人乒乓球赛事\"HOPE AI挑战赛\"发起方，该赛事为Hitch Open世界AI竞速锦标赛2026赛季新赛项，首次以完全自主决策人形机器人为参赛主体。",
  "communityId": 295,
  "uuid": "d638032f-9eab-48df-a64f-5b7e3293ba0f",
  "labels": [
    "Organization",
    "Entity"
  ]
}
```

## Person

```json
{
  "summary": "某企业宣布新品",
  "pageRank": 0.9612404689154856,
  "momentum_updated_at": "2026-05-09T04:37:52.682927000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "某企业",
  "description": "华东某机器人企业发布新一代协作机器人控制平台，平台已在汽车零部件产线试点，并计划于下月面向工业客户开放。该企业同时宣布与一家自动化设备供应商达成合作。",
  "created_at": "2026-05-09T04:37:39.103999000+00:00",
  "communityId": 480,
  "uuid": "e872a421-ce27-4ef9-99e9-f382c68ccec8",
  "labels": [
    "Person",
    "Entity"
  ]
}
```

## Region

```json
{
  "summary": "刘立荣 is selling furniture in 印尼",
  "pageRank": 0.7404149557862525,
  "momentum_updated_at": "2026-04-29T04:32:00.881796000+00:00",
  "created_at": "2026-04-29T04:29:24.512124000+00:00",
  "uuid": "98eb01ac-9b3b-4f4f-8769-bf03db28d4f1",
  "labels": [
    "Entity",
    "Region"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "entity_types": [
    "Entity",
    "Region"
  ],
  "name": "印尼",
  "communityId": 395,
  "attributes__related_news": "金立创始人刘立荣在印尼卖家具"
}
```

## Policy

暂无样本

## Index

```json
{
  "summary": "The '毕加索SPAD-SoC' chip achieves a photon detection efficiency of 40%",
  "pageRank": 0.5721672538531223,
  "momentum_updated_at": "2026-04-29T06:08:06.265237000+00:00",
  "created_at": "2026-04-29T06:06:17.683503000+00:00",
  "attributes__value": "40%",
  "uuid": "fc711130-96b5-442e-a6ca-72814b82f68f",
  "labels": [
    "Entity",
    "Index"
  ],
  "attributes__source": "禾赛科技4月17日发布全球首款6D全彩激光雷达芯片\"毕加索SPAD-SoC\"",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "光子探测效率",
  "entity_types": [
    "Entity",
    "Index"
  ],
  "communityId": 205
}
```

## DataSource

```json
{
  "summary": "北大彭宇新团队在iNat21数据集上应用TARA方法，提升多模态模型层级识别能力，HCA指标提高3-6%，增强未知物种识别泛化能力。",
  "pageRank": 0.15000000000000002,
  "momentum_updated_at": "2026-04-10T12:11:48.806137000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "semanticType": "DataSource, Entity",
  "name": "iNat21数据集",
  "created_at": "2026-04-10T12:01:56.847983000+00:00",
  "communityId": 97,
  "uuid": "24dd48b9-57dc-4232-b2af-b8ba5d22db7f",
  "labels": [
    "DataSource",
    "Entity"
  ]
}
```

## Document

```json
{
  "summary": "开发者可通过腾讯文档获取海光DCU资源",
  "pageRank": 0.5724547363548631,
  "momentum_updated_at": "2026-05-09T05:02:44.124545000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "腾讯文档",
  "created_at": "2026-05-09T05:02:16.705474000+00:00",
  "description": "海光DCU完成腾讯混元Hy3模型适配，该模型295B参数，支持256K上下文，推理效率提升40%。腾讯应用于云、QQ等业务。海光DCU兼容开源框架，支持千亿模型训练，与C86 CPU协同提供算力。开发者可通过腾讯文档获取资源。国产算力与模型协同成产业关键方向。",
  "communityId": 11,
  "uuid": "8b0423be-671b-43cf-99c4-65ebbb6192c4",
  "labels": [
    "Entity",
    "Document"
  ]
}
```

## Chunk

```json
{
  "summary": "海信强调用户共创理念",
  "pageRank": 0.4469389870428051,
  "momentum_updated_at": "2026-04-10T12:57:36.083461000+00:00",
  "group_id": "",
  "momentum_score": 1.0,
  "name": "用户共创理念",
  "created_at": "2026-04-10T12:56:42.377442000+00:00",
  "source": "海信在青岛用机器人主持发布会，推出多款AI家电新品，包括智能空调、电视和陪伴机器人，强调用户共创理念。",
  "communityId": 284,
  "uuid": "665ead64-10d8-41e4-a759-ccb42dc82626",
  "labels": [
    "Chunk",
    "Entity"
  ]
}
```

## EnterpriseEvent

```json
{
  "summary": "HOPE AI挑战赛 is a new competition item in Hitch Open世界AI竞速锦标赛2026赛季",
  "publishTime": "2026-04-17T00:00:00+00:00",
  "pageRank": 0.48455367759954926,
  "momentum_updated_at": "2026-05-09T05:10:25.474480000+00:00",
  "description": "发起全球首个AI自主决策机器人乒乓球赛事\"HOPE AI挑战赛\"，该赛事首次以完全自主决策人形机器人为参赛主体",
  "created_at": "2026-05-09T05:09:58.549391000+00:00",
  "uuid": "19489dc4-7305-438f-ac42-dcce49f53aed",
  "labels": [
    "EnterpriseEvent",
    "Entity"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "name": "Hitch Open世界AI竞速锦标赛2026赛季",
  "communityId": 295
}
```

## OrganizationEvent

```json
{
  "summary": "交警机器人首次亮相是在2024年4月19日举办的北京亦庄半程马拉松比赛期间",
  "publishTime": "2024-04-19T00:00:00+00:00",
  "pageRank": 0.5914599233244573,
  "momentum_updated_at": "2026-05-09T05:04:51.991414000+00:00",
  "description": "北京首个交警机器人亮相街头，具备交通手势指挥、安全宣传、出行引导功能。未来将试点路口执勤，拓展违法识别、路况巡视等应用场景。",
  "created_at": "2026-05-09T05:04:07.110659000+00:00",
  "uuid": "1be553b6-b9b9-4b9e-be00-10a7e2936b9d",
  "labels": [
    "OrganizationEvent",
    "Entity"
  ],
  "group_id": "",
  "momentum_score": 1.0,
  "name": "北京亦庄半程马拉松",
  "location": "北京亦庄",
  "communityId": 427
}
```

## Episodic

```json
{
  "raw_text": "4 月 17 日，在2026年智元合作伙伴大会（APC 2026）具身智能教育生态分论坛，Hitch Open联合智元发起全球首个AI自主决策机器人乒乓球赛事，成为国内首家深度合作该国际开放竞技平台的具身智能头部企业。HOPE AI挑战赛，全称 Hitch Open Ping-Pong Embodiment AI 挑战赛，是Hitch Open世界AI竞速锦标赛2026赛季推出的全新旗舰赛项，也是全球首个以完全自主决策人形机器人为参赛主体的乒乓球竞技赛事。",
  "created_at": "2026-05-09T05:09:54.988928000+00:00",
  "news_url": "https://36kr.com/newsflashes/3773085063496194?f=rss",
  "source": "text",
  "title": "Hitch Open联合智元发起全球首个AI自主决策机器人乒乓球赛事",
  "uuid": "4999c2eb-c53b-46ac-b8dd-9d7f036deeaa",
  "content": "2026年4月17日，Hitch Open与智元在APC 2026具身智能教育生态分论坛发起全球首个AI自主决策机器人乒乓球赛事\"HOPE AI挑战赛\"。该赛事为Hitch Open世界AI竞速锦标赛2026赛季新赛项，首次以完全自主决策人形机器人为参赛主体。",
  "news_hotness_updated_at": "2026-05-09T05:10:26.004000000+00:00",
  "news_hotness_score": 1.2000000000000002,
  "news_source": "36Kr Newsflash Feed",
  "entity_edges": [
    "a5d5aca1-16ef-4e04-b4f5-16ac8c6dab84",
    "7921272d-be9d-46c0-acf6-97f149292680",
    "f3fa971d-50c5-45fc-8a56-41289cb62783",
    "7100f46f-46e1-4b6d-a2eb-6b106c6a2ffa",
    "1f3417c6-e764-45ab-a862-b45da94449d1"
  ],
  "group_id": "",
  "publish_time": "2026-04-18T17:40:36.000000000+00:00",
  "ingested_at": "2026-05-09T05:09:54.988928000+00:00",
  "name": "Hitch Open联合智元发起全球首个AI自主决策机器人乒乓球赛事",
  "source_description": "API text input",
  "valid_at": "2026-04-18T17:40:36.000000000+00:00"
}
```

## StoryThread

```json
{
  "summary": "迁移后验证：某企业宣布新品并进行产业合作",
  "updated_at": "2026-05-09T05:10:25.545995000+00:00",
  "episode_count": 1,
  "thread_type": "product",
  "thread_hotness": 24.599999999999998,
  "anchor_entity_uuid": "42ed86b7-84d6-459e-a6d7-06bbe1b7c75f",
  "first_seen_at": "2026-05-09T04:37:36.137251000+00:00",
  "anchor_entity_name": "新品",
  "last_seen_at": "2026-05-09T04:37:36.137251000+00:00",
  "title": "新品产品脉络",
  "uuid": "9c61b116-c0ce-5c01-a841-daec3a48d348"
}
```
