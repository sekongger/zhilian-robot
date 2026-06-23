from __future__ import annotations

import asyncio

from services.news_graph_projection_service import (
    NEWS_GRAPH_PROJECTION_VERSION,
    NewsGraphProjectionService,
    normalize_projected_relation_type,
    normalize_projected_type,
)


def test_normalize_projected_type_prefers_business_labels_and_collapses_company():
    assert normalize_projected_type(["Entity", "Company"]) == "Enterprise"
    assert normalize_projected_type(["Entity", "ProductModel"]) == "ProductModel"
    assert normalize_projected_type(["Entity", "Technology"]) == "Technology"
    assert normalize_projected_type(["Entity"]) == "Unknown"


def test_normalize_projected_relation_type_maps_fact_text_to_business_relation():
    assert normalize_projected_relation_type("RELATES_TO", {"fact": "A supplies B"}) == "SUPPLIES_TO"
    assert normalize_projected_relation_type("RELATES_TO", {"name": "战略投资"}) == "INVESTS_IN"
    assert normalize_projected_relation_type("RELATES_TO", {"fact": "公司发布新产品"}) == "RELEASES"
    assert normalize_projected_relation_type("MENTIONS", {}) == "MENTIONS"
    assert normalize_projected_relation_type("RELATES_TO", {"fact": "相关"}) == "RELATED_TO"


class FakeDriver:
    def __init__(self):
        self.queries: list[tuple[str, dict]] = []

    async def execute_query(self, query, **params):
        self.queries.append((query, params))
        if "labels(entity) AS labels" in query:
            return (
                [
                    {
                        "entity_id": "entity-1",
                        "labels": ["Entity", "Company"],
                        "name": "腾讯",
                    },
                    {
                        "entity_id": "entity-2",
                        "labels": ["Entity", "Product"],
                        "name": "机器人",
                    },
                ],
                None,
                None,
            )
        if "elementId(source) AS source_id" in query:
            return (
                [
                    {
                        "source_id": "entity-1",
                        "target_id": "entity-2",
                        "relationship_type": "RELATES_TO",
                        "relationship_properties": {"fact": "腾讯发布机器人产品"},
                    }
                ],
                None,
                None,
            )
        return ([{"count": 1}], None, None)


def test_news_graph_projection_service_materializes_idempotent_view_layer():
    driver = FakeDriver()
    service = NewsGraphProjectionService(driver)

    result = asyncio.run(
        service.materialize_projection(
            group_id="crawl_1",
            limit=100,
            clear_existing=True,
        )
    )

    assert result["projection_version"] == NEWS_GRAPH_PROJECTION_VERSION
    assert result["group_id"] == "crawl_1"
    assert result["projected_entities"] == 2
    assert result["projected_relationships"] == 1
    assert result["relationship_type_counts"] == {"RELEASES": 1}

    executed = "\n".join(query for query, _ in driver.queries)
    assert "MATCH ()-[r]->()" in executed
    assert "REMOVE entity:NewsProjection" in executed
    assert "SET entity:NewsProjection" in executed
    assert "MERGE (source)-[projected:PROJECTED_RELEASES" in executed
    assert "projection_key" in executed
    assert any(params.get("group_id") == "crawl_1" for _, params in driver.queries)
