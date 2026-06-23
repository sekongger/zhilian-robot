from __future__ import annotations

import asyncio
from datetime import datetime

from services.entity_heat_service import (
    ENTITY_HEAT_FORMULA,
    EntityHeatRankingService,
    compute_heat_rankings,
    resolve_period_window,
)


def test_compute_heat_rankings_uses_explainable_formula_components():
    rows = [
        {
            "entity_uuid": "entity-a",
            "entity_name": "腾讯",
            "entity_labels": ["Entity", "Enterprise"],
            "mention_count": 9,
            "news_hotness_sum": 30.0,
            "source_count": 3,
            "freshness_score": 0.8,
            "anchor_score": 1.0,
            "anchor_id": "Enterprise:wiki:Q860580",
            "top_evidence": [],
        },
        {
            "entity_uuid": "entity-b",
            "entity_name": "低热度公司",
            "entity_labels": ["Entity", "Enterprise"],
            "mention_count": 1,
            "news_hotness_sum": 2.0,
            "source_count": 1,
            "freshness_score": 0.2,
            "anchor_score": 0.2,
            "anchor_id": None,
            "top_evidence": [],
        },
    ]

    ranked = compute_heat_rankings(rows, entity_type="Enterprise")

    assert ENTITY_HEAT_FORMULA["formula_version"] == "entity_heat_v1"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["entity_name"] == "腾讯"
    assert ranked[0]["heat_score"] == 98.0
    assert ranked[0]["components"]["mention_norm"] == 1.0
    assert ranked[0]["components"]["news_hotness_norm"] == 1.0
    assert ranked[0]["components"]["source_norm"] == 1.0
    assert ranked[0]["components"]["freshness_norm"] == 0.8
    assert ranked[0]["components"]["anchor_norm"] == 1.0
    assert ranked[1]["rank"] == 2
    assert ranked[1]["heat_score"] < ranked[0]["heat_score"]


def test_resolve_period_window_supports_daily_and_monday_weekly_boundaries():
    daily_start, daily_end = resolve_period_window("daily", "2026-06-22")
    weekly_start, weekly_end = resolve_period_window("weekly", "2026-06-24")

    assert daily_start.isoformat() == "2026-06-22T00:00:00+08:00"
    assert daily_end.isoformat() == "2026-06-22T23:59:59.999999+08:00"
    assert weekly_start.isoformat() == "2026-06-22T00:00:00+08:00"
    assert weekly_end.isoformat() == "2026-06-28T23:59:59.999999+08:00"


class FakeDriver:
    def __init__(self):
        self.queries: list[tuple[str, dict]] = []

    async def execute_query(self, query, **params):
        self.queries.append((query, params))
        if "RETURN snapshot.period_start AS period_start" in query:
            return ([{"period_start": "2026-06-15T00:00:00+08:00"}], None, None)
        if "RETURN count(ep) AS episodeCount" in query:
            return ([{"episodeCount": 3}], None, None)
        if "RETURN properties(snapshot) AS snapshot" in query:
            return (
                [
                    {
                        "snapshot": {
                            "rank": 1,
                            "entity_uuid": "entity-a",
                            "entity_name": "腾讯",
                            "entity_type": "Enterprise",
                            "heat_score": 98.0,
                            "mention_count": 9,
                            "source_count": 3,
                            "news_hotness_sum": 30.0,
                            "freshness_score": 0.8,
                            "anchor_score": 1.0,
                            "anchor_id": "Enterprise:wiki:Q860580",
                            "top_evidence_json": "[]",
                        }
                    }
                ],
                None,
                None,
            )
        if "entity.uuid AS entity_uuid" in query:
            return (
                [
                    {
                        "entity_uuid": "entity-a",
                        "entity_name": "腾讯",
                        "entity_labels": ["Entity", "Enterprise"],
                        "mention_count": 9,
                        "news_hotness_sum": 30.0,
                        "source_count": 3,
                        "freshness_score": 0.8,
                        "anchor_score": 1.0,
                        "anchor_id": "Enterprise:wiki:Q860580",
                        "top_evidence": [
                            {
                                "title": "腾讯机器人资讯",
                                "source": "36Kr",
                                "url": "https://36kr.com/p/1",
                                "publish_time": "2026-06-22T10:00:00+08:00",
                                "news_hotness_score": 7.4,
                            }
                        ],
                    }
                ],
                None,
                None,
            )
        return ([], None, None)


def test_entity_heat_ranking_service_generates_idempotent_snapshot_payload():
    driver = FakeDriver()
    service = EntityHeatRankingService(driver)

    result = asyncio.run(
        service.generate_and_store_rankings(
            period_type="daily",
            as_of="2026-06-22",
            entity_type="Enterprise",
            limit_per_type=20,
        )
    )

    assert result["period_type"] == "daily"
    assert result["entity_type"] == "Enterprise"
    assert result["items"][0]["entity_name"] == "腾讯"
    assert result["items"][0]["top_evidence"][0]["url"] == "https://36kr.com/p/1"

    executed = "\n".join(query for query, _ in driver.queries)
    assert "DETACH DELETE snapshot" in executed
    assert "MERGE (snapshot:EntityHeatSnapshot" in executed
    assert "RANKS_ENTITY" in executed
    assert "EVIDENCED_BY" in executed


def test_entity_heat_candidate_query_passes_iso_periods_to_neo4j():
    driver = FakeDriver()
    service = EntityHeatRankingService(driver)

    asyncio.run(
        service.generate_and_store_rankings(
            period_type="weekly",
            as_of="2026-06-18",
            entity_type="Enterprise",
            limit_per_type=20,
        )
    )

    candidate_query, candidate_params = next(
        (query, params)
        for query, params in driver.queries
        if "entity.uuid AS entity_uuid" in query
    )
    assert "datetime($period_start)" in candidate_query
    assert "datetime($period_end)" in candidate_query
    assert candidate_params["period_start"] == "2026-06-15T00:00:00+08:00"
    assert candidate_params["period_end"] == "2026-06-21T23:59:59.999999+08:00"


def test_entity_heat_ranking_service_queries_snapshot_with_formula_contract():
    driver = FakeDriver()
    service = EntityHeatRankingService(driver)

    result = asyncio.run(
        service.query_rankings(
            period_type="daily",
            date="2026-06-22",
            entity_type="Enterprise",
            limit=10,
        )
    )

    assert result["formula_version"] == "entity_heat_v1"
    assert result["formula"]["mention_weight"] == 0.45
    assert result["items"][0]["entity_name"] == "腾讯"
    assert result["items"][0]["top_evidence"] == []


def test_entity_heat_ranking_service_queries_latest_snapshot_when_date_missing():
    driver = FakeDriver()
    service = EntityHeatRankingService(driver)

    result = asyncio.run(
        service.query_rankings(
            period_type="weekly",
            date=None,
            entity_type="Enterprise",
            limit=10,
        )
    )

    assert result["period_start"] == "2026-06-15T00:00:00+08:00"
    latest_query, latest_params = next(
        (query, params)
        for query, params in driver.queries
        if "RETURN snapshot.period_start AS period_start" in query
    )
    assert "ORDER BY snapshot.period_start DESC" in latest_query
    assert latest_params["period_type"] == "weekly"
    assert latest_params["entity_type"] == "Enterprise"
