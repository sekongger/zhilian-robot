from __future__ import annotations

from datetime import datetime, timezone

from app.news_graph_mcp.service import NewsGraphQueryService


class FakeNeo4j:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute_query(self, query, parameters=None):
        self.calls.append({"query": query, "parameters": parameters or {}})
        if not self.responses:
            return []
        return self.responses.pop(0)


def test_query_entity_news_timeline_uses_canonical_or_name_filter():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "uuid": "ep-2",
                        "name": "腾讯发布 AI 基础设施更新",
                        "summary": "腾讯云升级 AI 基础设施。",
                        "source": "36Kr",
                        "source_url": "https://36kr.com/p/3822747968196993?f=rss",
                    },
                    "labels": ["Episodic"],
                    "publish_time": "2026-06-01T02:00:00+00:00",
                    "entities": [
                        {
                            "id": "NewsEntityProfile:v2:tencent",
                            "name": "腾讯",
                            "type": "Enterprise",
                            "canonicalGraphId": "Enterprise:wiki:Q860580",
                        }
                    ],
                    "events": [],
                    "relations": [],
                }
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j, clock=lambda: datetime(2026, 6, 1, 12, tzinfo=timezone.utc))

    payload = service.query_entity_news_timeline(canonical_graph_id="Enterprise:wiki:Q860580", since_hours=72)

    assert payload["entity"]["canonical_graph_id"] == "Enterprise:wiki:Q860580"
    assert payload["items"][0]["title"] == "腾讯发布 AI 基础设施更新"
    assert neo4j.calls[0]["parameters"]["canonical_graph_id"] == "Enterprise:wiki:Q860580"
    assert "CommonSenseAnchor" in neo4j.calls[0]["query"]
    assert "refersTo" in neo4j.calls[0]["query"]


def test_query_enterprise_supply_chain_context_returns_llm_ready_context():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "enterprise": {
                        "id": "Enterprise:wiki:Q20716",
                        "name": "三星",
                        "summary": "韩国综合性企业集团。",
                    },
                    "enterprise_labels": ["Entity", "IncCore.Enterprise"],
                    "related_entities": [
                        {
                            "relation": "produces",
                            "direction": "outgoing",
                            "node": {
                                "id": "ProductModel:wiki:hbm",
                                "name": "HBM",
                                "type_name": "ProductModel",
                                "summary": "高带宽内存产品。",
                            },
                            "labels": ["IncoreFusionNode", "ProductModel"],
                            "evidence": "三星扩大 HBM 供给。",
                        },
                        {
                            "relation": "supplies",
                            "direction": "incoming",
                            "node": {
                                "id": "Enterprise:wiki:Q123",
                                "name": "上游材料企业",
                                "type_name": "Enterprise",
                            },
                            "labels": ["IncoreFusionNode", "Enterprise"],
                            "evidence": "上游材料企业向三星供应材料。",
                        },
                    ],
                    "news_items": [
                        {
                            "news": {
                                "id": "ep-samsung-1",
                                "title": "三星 HBM 供给扩张",
                                "summary": "三星扩大 HBM 产能。",
                                "content": "三星扩大 HBM 产能，带动上游设备和材料需求。",
                                "source_name": "八爪鱼",
                                "source_url": "https://www.icloudnews.net/a/116914.html",
                            },
                            "labels": ["Episodic"],
                            "publish_time": "2026-06-01T01:00:00+00:00",
                            "entities": [],
                            "events": [],
                            "relations": [],
                        }
                    ],
                }
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j)

    payload = service.query_enterprise_supply_chain_context(entity_name="三星", since_hours=720, limit=10)

    assert payload["query"] == "enterprise_supply_chain_context"
    assert payload["enterprise"]["name"] == "三星"
    assert payload["products"][0]["name"] == "HBM"
    assert payload["upstream_enterprises"][0]["name"] == "上游材料企业"
    assert payload["news_timeline"][0]["title"] == "三星 HBM 供给扩张"
    assert "三星" in payload["llm_context"]
    assert "HBM" in payload["llm_context"]
    assert neo4j.calls[0]["parameters"]["entity_name"] == "三星"
    assert "CommonSenseAnchor" in neo4j.calls[0]["query"]


def test_query_news_by_source_industry_returns_summary_and_full_content():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "id": "ep-ai-1",
                        "name": "AI 服务器需求增长",
                        "sourceProfiles": {
                            "graphiti_news": {
                                "title": "AI 服务器需求增长",
                                "news_source": "八爪鱼",
                                "news_url": "https://www.icloudnews.net/a/116914.html",
                                "publish_time": "2026-06-02T08:00:00+00:00",
                                "content": "这是 AI 服务器产业资讯的完整原文。",
                            }
                        },
                        "factPayload": {
                            "summary": "AI 服务器需求继续增长。",
                            "raw_text": "这是 AI 服务器产业资讯的完整原文。",
                        },
                    },
                    "labels": ["IncoreFusionNode", "Episodic"],
                    "entities": [{"name": "AI服务器", "type": "Product"}],
                    "events": [],
                    "relations": [],
                }
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j)

    payload = service.query_news_by_source_industry(
        start_time="2026-06-01T00:00:00+00:00",
        end_time="2026-06-03T00:00:00+00:00",
        source_name="八爪鱼",
        industry="AI服务器",
        limit=5,
    )

    item = payload["items"][0]
    assert payload["query"] == "news_by_source_industry"
    assert payload["filters"]["source_name"] == "八爪鱼"
    assert payload["filters"]["industry"] == "AI服务器"
    assert item["summary"] == "AI 服务器需求继续增长。"
    assert item["content"] == "这是 AI 服务器产业资讯的完整原文。"
    assert item["source_name"] == "八爪鱼"
    assert neo4j.calls[0]["parameters"]["source_name"] == "八爪鱼"
    assert "toString(coalesce(ep.sourceProfiles" not in neo4j.calls[0]["query"]
    assert "toString(coalesce(ep.factPayload" not in neo4j.calls[0]["query"]


def test_query_news_by_source_industry_excludes_placeholder_source_urls():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "id": "ep-placeholder",
                        "title": "手工测试资讯",
                        "summary": "这条资讯带有占位链接。",
                        "source_url": "https://example.com/graphiti-news-small-20260524",
                    },
                    "labels": ["Episodic"],
                    "entities": [{"name": "三星", "type": "Enterprise"}],
                    "events": [],
                    "relations": [],
                },
                {
                    "news": {
                        "id": "ep-real",
                        "title": "真实资讯",
                        "summary": "这条资讯带有真实原文链接。",
                        "source_url": "https://www.icloudnews.net/a/116914.html",
                    },
                    "labels": ["Episodic"],
                    "entities": [{"name": "三星", "type": "Enterprise"}],
                    "events": [],
                    "relations": [],
                },
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j)

    payload = service.query_news_by_source_industry(source_name="Octopus", industry="三星", limit=2)

    assert [item["news_id"] for item in payload["items"]] == ["ep-real"]
    assert payload["items"][0]["source_url"] == "https://www.icloudnews.net/a/116914.html"


def test_query_recommended_news_candidates_returns_scored_agent_ready_items():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "id": "ep-rec-1",
                        "title": "三星扩大 HBM 产能",
                        "summary": "三星扩大 HBM 产能以满足 AI 服务器需求。",
                        "content": "三星扩大 HBM 产能以满足 AI 服务器需求，上游设备厂商受益。",
                        "source_name": "Octopus News Feed",
                        "source_url": "https://www.icloudnews.net/a/116914.html",
                    },
                    "labels": ["IncoreFusionNode", "Episodic"],
                    "publish_time": "2026-06-02T08:00:00+00:00",
                    "entities": [
                        {"name": "三星", "type": "Enterprise", "canonicalGraphId": "Enterprise:wiki:Q20716"},
                        {"name": "HBM", "type": "ProductModel"},
                        {"name": "AI服务器", "type": "Product"},
                    ],
                    "events": [{"event_type": "capacity_expansion", "summary": "扩大 HBM 产能"}],
                    "relations": [{"subject": "三星", "predicate": "supplies", "object": "HBM"}],
                }
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j, clock=lambda: datetime(2026, 6, 3, 12, tzinfo=timezone.utc))

    payload = service.query_recommended_news_candidates(
        industries=["AI服务器"],
        entity_names=["三星"],
        product_names=["HBM"],
        preference_tags=["扩产"],
        since_hours=72,
        limit=5,
    )

    item = payload["items"][0]
    assert payload["query"] == "recommended_news_candidates"
    assert payload["filters"]["industries"] == ["AI服务器"]
    assert item["title"] == "三星扩大 HBM 产能"
    assert item["recommendation"]["score"] >= 80
    assert "三星" in item["recommendation"]["matched_terms"]
    assert "AI服务器" in item["recommendation"]["matched_terms"]
    assert "CommonSenseAnchor" in neo4j.calls[0]["query"]
    assert item["recommendation"]["reasons"]
    assert "推荐" in payload["llm_context"]
    assert neo4j.calls[0]["parameters"]["entity_names"] == ["三星"]
    assert "toString(coalesce(ep.sourceProfiles" not in neo4j.calls[0]["query"]
    assert "toString(coalesce(ep.factPayload" not in neo4j.calls[0]["query"]
    assert "toString(coalesce(entity.anchor.aliases" not in neo4j.calls[0]["query"]


def test_query_recommended_news_candidates_excludes_placeholder_source_urls():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "id": "ep-placeholder",
                        "title": "小范围测试资讯：三星存储芯片价格变化",
                        "summary": "三星集团相关存储芯片和企业级SSD需求变化资讯。",
                        "source_url": "https://example.com/graphiti-news-small-20260524",
                    },
                    "labels": ["Episodic"],
                    "entities": [
                        {"name": "三星", "type": "Enterprise"},
                        {"name": "企业级SSD", "type": "ProductModel"},
                    ],
                    "events": [{"event_type": "demand_change", "summary": "需求变化"}],
                    "relations": [{"subject": "三星", "predicate": "supplies", "object": "企业级SSD"}],
                },
                {
                    "news": {
                        "id": "ep-real",
                        "title": "三星下一代Exynos芯片或将采用1.4 纳米工艺",
                        "summary": "三星下一代Exynos芯片或将采用先进制程。",
                        "source_url": "https://www.icloudnews.net/a/116914.html",
                    },
                    "labels": ["Episodic"],
                    "entities": [{"name": "三星", "type": "Enterprise"}],
                    "events": [],
                    "relations": [],
                },
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j)

    payload = service.query_recommended_news_candidates(entity_names=["三星"], limit=2)

    assert [item["news_id"] for item in payload["items"]] == ["ep-real"]
    assert payload["items"][0]["source_url"] == "https://www.icloudnews.net/a/116914.html"


def test_query_subscription_news_feed_returns_feed_for_user_interests():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "news": {
                        "id": "ep-feed-1",
                        "title": "高通发布 AI PC 芯片",
                        "summary": "高通发布面向 AI PC 的新芯片。",
                        "content": "高通发布面向 AI PC 的新芯片，强调端侧 AI 推理能力。",
                        "source_name": "Octopus News Feed",
                        "source_url": "https://36kr.com/p/3822747968196993?f=rss",
                    },
                    "labels": ["IncoreFusionNode", "Episodic"],
                    "publish_time": "2026-06-02T09:00:00+00:00",
                    "entities": [
                        {"name": "高通", "type": "Enterprise", "canonicalGraphId": "Enterprise:wiki:Q544847"},
                        {"name": "AI PC", "type": "Product"},
                    ],
                    "events": [],
                    "relations": [{"subject": "高通", "predicate": "releases", "object": "AI PC 芯片"}],
                }
            ]
        ]
    )
    service = NewsGraphQueryService(neo4j=neo4j, clock=lambda: datetime(2026, 6, 3, 12, tzinfo=timezone.utc))

    payload = service.query_subscription_news_feed(
        industries=["AI PC"],
        enterprises=["高通"],
        products=["AI PC"],
        since_hours=72,
        limit=10,
    )

    item = payload["items"][0]
    assert payload["query"] == "subscription_news_feed"
    assert payload["subscription_profile"]["enterprises"] == ["高通"]
    assert item["title"] == "高通发布 AI PC 芯片"
    assert item["matched_subscription"]["enterprises"] == ["高通"]
    assert item["matched_subscription"]["products"] == ["AI PC"]
    assert "高通" in payload["feed_summary"]
    assert neo4j.calls[0]["parameters"]["products"] == ["AI PC"]
