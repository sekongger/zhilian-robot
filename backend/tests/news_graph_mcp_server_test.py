from __future__ import annotations

import asyncio
import json

from app.news_graph_mcp.server import register_tools


class FakeMcp:
    def __init__(self):
        self.tools = {}

    def add_tool(self, func, name):
        self.tools[name] = func


class FakeService:
    def query_entity_news_timeline(self, **kwargs):
        return {"tool": "query_entity_news_timeline", "kwargs": kwargs, "items": []}

    def query_enterprise_supply_chain_context(self, **kwargs):
        return {"tool": "query_enterprise_supply_chain_context", "kwargs": kwargs, "items": []}

    def query_news_by_source_industry(self, **kwargs):
        return {"tool": "query_news_by_source_industry", "kwargs": kwargs, "items": []}

    def query_recommended_news_candidates(self, **kwargs):
        return {"tool": "query_recommended_news_candidates", "kwargs": kwargs, "items": []}

    def query_subscription_news_feed(self, **kwargs):
        return {"tool": "query_subscription_news_feed", "kwargs": kwargs, "items": []}


def test_register_tools_exposes_news_graph_tool_catalog():
    mcp = FakeMcp()

    register_tools(mcp, FakeService())

    assert set(mcp.tools) == {
        "query_entity_news_timeline",
        "query_enterprise_supply_chain_context",
        "query_news_by_source_industry",
        "query_recommended_news_candidates",
        "query_subscription_news_feed",
    }


def test_mcp_tool_returns_json_string():
    mcp = FakeMcp()
    register_tools(mcp, FakeService())

    result = asyncio.run(mcp.tools["query_entity_news_timeline"](since_hours=12, entity_name="三星", limit=3))
    payload = json.loads(result)

    assert payload["tool"] == "query_entity_news_timeline"
    assert payload["kwargs"]["since_hours"] == 12
    assert payload["kwargs"]["entity_name"] == "三星"
    assert payload["kwargs"]["limit"] == 3


def test_mcp_enterprise_supply_chain_tool_returns_json_string():
    mcp = FakeMcp()
    register_tools(mcp, FakeService())

    result = asyncio.run(mcp.tools["query_enterprise_supply_chain_context"](entity_name="三星", since_hours=720, limit=5))
    payload = json.loads(result)

    assert payload["tool"] == "query_enterprise_supply_chain_context"
    assert payload["kwargs"]["entity_name"] == "三星"
    assert payload["kwargs"]["since_hours"] == 720
    assert payload["kwargs"]["limit"] == 5


def test_mcp_news_by_source_industry_tool_returns_json_string():
    mcp = FakeMcp()
    register_tools(mcp, FakeService())

    result = asyncio.run(
        mcp.tools["query_news_by_source_industry"](
            start_time="2026-06-01T00:00:00+00:00",
            end_time="2026-06-03T00:00:00+00:00",
            source_name="八爪鱼",
            industry="AI服务器",
            limit=5,
        )
    )
    payload = json.loads(result)

    assert payload["tool"] == "query_news_by_source_industry"
    assert payload["kwargs"]["source_name"] == "八爪鱼"
    assert payload["kwargs"]["industry"] == "AI服务器"


def test_mcp_recommended_news_candidates_tool_returns_json_string():
    mcp = FakeMcp()
    register_tools(mcp, FakeService())

    result = asyncio.run(
        mcp.tools["query_recommended_news_candidates"](
            industries=["AI服务器"],
            entity_names=["三星"],
            product_names=["HBM"],
            preference_tags=["扩产"],
            since_hours=72,
            limit=5,
        )
    )
    payload = json.loads(result)

    assert payload["tool"] == "query_recommended_news_candidates"
    assert payload["kwargs"]["industries"] == ["AI服务器"]
    assert payload["kwargs"]["entity_names"] == ["三星"]
    assert payload["kwargs"]["product_names"] == ["HBM"]


def test_mcp_subscription_news_feed_tool_returns_json_string():
    mcp = FakeMcp()
    register_tools(mcp, FakeService())

    result = asyncio.run(
        mcp.tools["query_subscription_news_feed"](
            industries=["AI PC"],
            enterprises=["高通"],
            products=["AI PC"],
            since_hours=72,
            limit=10,
        )
    )
    payload = json.loads(result)

    assert payload["tool"] == "query_subscription_news_feed"
    assert payload["kwargs"]["industries"] == ["AI PC"]
    assert payload["kwargs"]["enterprises"] == ["高通"]
    assert payload["kwargs"]["products"] == ["AI PC"]
