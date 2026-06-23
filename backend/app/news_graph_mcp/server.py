"""MCP server exposing read-only fused news graph tools."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.news_graph_mcp.service import NewsGraphQueryService


def register_tools(mcp_server: Any, service: NewsGraphQueryService) -> None:
    """Register MCP tools on a FastMCP-compatible server."""

    async def query_entity_news_timeline(
        entity_name: Optional[str] = None,
        canonical_graph_id: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> str:
        """Query recent news timeline for an enterprise, product, technology, or canonical graph id."""

        return _json(
            service.query_entity_news_timeline(
                entity_name=entity_name,
                canonical_graph_id=canonical_graph_id,
                since_hours=since_hours,
                limit=limit,
            )
        )

    async def query_enterprise_supply_chain_context(
        entity_name: Optional[str] = None,
        canonical_graph_id: Optional[str] = None,
        since_hours: int = 720,
        limit: int = 30,
    ) -> str:
        """Query LLM-readable upstream, downstream, product, and news context for an enterprise."""

        return _json(
            service.query_enterprise_supply_chain_context(
                entity_name=entity_name,
                canonical_graph_id=canonical_graph_id,
                since_hours=since_hours,
                limit=limit,
            )
        )

    async def query_news_by_source_industry(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        source_name: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Query news by time range, source, and industry, returning both summary and full original text."""

        return _json(
            service.query_news_by_source_industry(
                start_time=start_time,
                end_time=end_time,
                since_hours=since_hours,
                source_name=source_name,
                industry=industry,
                limit=limit,
            )
        )

    async def query_recommended_news_candidates(
        industries: Optional[list[str]] = None,
        entity_names: Optional[list[str]] = None,
        product_names: Optional[list[str]] = None,
        preference_tags: Optional[list[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> str:
        """Query scored news candidates for recommendation and briefing agents."""

        return _json(
            service.query_recommended_news_candidates(
                industries=industries,
                entity_names=entity_names,
                product_names=product_names,
                preference_tags=preference_tags,
                start_time=start_time,
                end_time=end_time,
                since_hours=since_hours,
                limit=limit,
            )
        )

    async def query_subscription_news_feed(
        industries: Optional[list[str]] = None,
        enterprises: Optional[list[str]] = None,
        products: Optional[list[str]] = None,
        preference_tags: Optional[list[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> str:
        """Query a personalized news feed from industry, enterprise, and product subscriptions."""

        return _json(
            service.query_subscription_news_feed(
                industries=industries,
                enterprises=enterprises,
                products=products,
                preference_tags=preference_tags,
                start_time=start_time,
                end_time=end_time,
                since_hours=since_hours,
                limit=limit,
            )
        )

    mcp_server.add_tool(query_entity_news_timeline, name="query_entity_news_timeline")
    mcp_server.add_tool(query_enterprise_supply_chain_context, name="query_enterprise_supply_chain_context")
    mcp_server.add_tool(query_news_by_source_industry, name="query_news_by_source_industry")
    mcp_server.add_tool(query_recommended_news_candidates, name="query_recommended_news_candidates")
    mcp_server.add_tool(query_subscription_news_feed, name="query_subscription_news_feed")


def create_mcp_server(*, port: int = 3010, service: Optional[NewsGraphQueryService] = None):
    """Create the FastMCP server lazily so tests do not require the MCP package."""

    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        message = (
            "The IncCore news graph MCP server requires 'mcp==1.6.0' and Python 3.10+. "
            "Use the backend Docker image or install backend/requirements.txt in a Python 3.10+ environment."
        )
        raise ModuleNotFoundError(message) from exc

    mcp_server = FastMCP("incore-news-graph-mcp", port=port)
    register_tools(mcp_server, service or NewsGraphQueryService())
    return mcp_server


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
