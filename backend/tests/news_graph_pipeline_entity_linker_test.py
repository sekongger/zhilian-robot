from app.news_graph_pipeline.dto import CommonSenseAnchorDTO
from app.news_graph_pipeline.entity_linker import EntityLinker


class FakeGraphiti:
    def __init__(self, entities):
        self.entities = entities
        self.synced_anchors = []
        self.linked = []

    def load_news_entities(self, *, group_id, limit):
        return self.entities[:limit]

    def sync_anchors(self, anchors):
        self.synced_anchors.extend(anchors)
        return {"synced": len(anchors), "skipped": 0}

    def write_entity_links(self, decisions):
        self.linked.extend(decisions)
        return {
            "refersTo": len([item for item in decisions if item.decision == "refersTo"]),
            "candidateRefersTo": len([item for item in decisions if item.decision == "candidateRefersTo"]),
            "unresolved": len([item for item in decisions if item.decision == "unresolved"]),
        }


def test_entity_linker_splits_high_medium_and_low_confidence_decisions():
    anchors = [
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q20716",
            type_name="Enterprise",
            name="三星",
            aliases=["三星集团", "Samsung"],
            description="",
            source_graph="incore_common_neo4j",
        ),
        CommonSenseAnchorDTO(
            anchor_id="ProductModel:wiki:Q214276",
            type_name="ProductModel",
            name="MacBook Pro",
            aliases=["MBP"],
            description="",
            source_graph="incore_common_neo4j",
        ),
    ]
    graphiti = FakeGraphiti(
        [
            {"id": "entity-1", "name": "三星集团", "type": "Enterprise"},
            {"id": "entity-2", "name": "14英寸MacBook Pro", "type": "Product"},
            {"id": "entity-3", "name": "完全未知实体", "type": "Enterprise"},
        ]
    )

    result = EntityLinker(graphiti=graphiti).link_group(group_id="crawl_1", anchors=anchors, limit=10)

    decisions = result["decisions"]
    assert [item.decision for item in decisions] == ["refersTo", "candidateRefersTo", "unresolved"]
    assert decisions[0].candidate_anchor_id == "Enterprise:wiki:Q20716"
    assert decisions[0].match_method == "exact_alias"
    assert decisions[1].candidate_anchor_id == "ProductModel:wiki:Q214276"
    assert decisions[1].match_method == "prefix_or_contains"
    assert result["write_stats"] == {"refersTo": 1, "candidateRefersTo": 1, "unresolved": 1}
    assert graphiti.synced_anchors == anchors


def test_entity_linker_rejects_short_abbreviation_and_type_incompatible_contains_matches():
    anchors = [
        CommonSenseAnchorDTO(
            anchor_id="ProductModel:wiki:Q62246",
            type_name="ProductModel",
            name="聚碳酸酯",
            aliases=["PC"],
            source_graph="incore_common_neo4j",
        ),
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q204474",
            type_name="Enterprise",
            name="Id Software",
            aliases=["id"],
            source_graph="incore_common_neo4j",
        ),
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q661845",
            type_name="Enterprise",
            name="意法半导体",
            aliases=["ST"],
            source_graph="incore_common_neo4j",
        ),
    ]
    graphiti = FakeGraphiti(
        [
            {"id": "entity-1", "name": "AI PC", "type": "Product"},
            {"id": "entity-2", "name": "Android 17", "type": "Technology"},
            {"id": "entity-3", "name": "RTX 5080 AORUS MASTER超级雕显卡", "type": "ProductModel"},
        ]
    )

    result = EntityLinker(graphiti=graphiti).link_group(group_id="crawl_1", anchors=anchors, limit=10)

    assert [item.decision for item in result["decisions"]] == ["unresolved", "unresolved", "unresolved"]


def test_entity_linker_only_uses_aliases_for_exact_matches_not_contains_matches():
    anchors = [
        CommonSenseAnchorDTO(
            anchor_id="ProductModel:wiki:Q58199",
            type_name="ProductModel",
            name="即时通讯",
            aliases=["chat", "IM"],
            source_graph="incore_common_neo4j",
        ),
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q160236",
            type_name="Enterprise",
            name="大都会艺术博物馆",
            aliases=["Met"],
            source_graph="incore_common_neo4j",
        ),
    ]
    graphiti = FakeGraphiti(
        [
            {"id": "entity-1", "name": "ChatGPT", "type": "Product"},
            {"id": "entity-2", "name": "Meta", "type": "Enterprise"},
        ]
    )

    result = EntityLinker(graphiti=graphiti).link_group(group_id="crawl_1", anchors=anchors, limit=10)

    assert [item.decision for item in result["decisions"]] == ["unresolved", "unresolved"]


def test_entity_linker_rejects_reverse_contains_and_short_ascii_primary_matches():
    anchors = [
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q751358",
            type_name="Enterprise",
            name="东芝三星储存科技",
            aliases=["TSST"],
            source_graph="incore_common_neo4j",
        ),
        CommonSenseAnchorDTO(
            anchor_id="Enterprise:wiki:Q571464",
            type_name="Enterprise",
            name="Trust",
            aliases=[],
            source_graph="incore_common_neo4j",
        ),
    ]
    graphiti = FakeGraphiti(
        [
            {"id": "entity-1", "name": "三星", "type": "Enterprise"},
            {"id": "entity-2", "name": "TRUSTe", "type": "Organization"},
        ]
    )

    result = EntityLinker(graphiti=graphiti).link_group(group_id="crawl_1", anchors=anchors, limit=10)

    assert [item.decision for item in result["decisions"]] == ["unresolved", "unresolved"]
