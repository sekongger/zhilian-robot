from app.news_graph_pipeline.dto import CommonSenseAnchorDTO
from app.news_graph_pipeline.graphiti_anchor_client import GraphitiAnchorClient


class FakeNeo4j:
    def __init__(self):
        self.calls = []

    def execute_query(self, query, parameters=None):
        self.calls.append({"query": query, "parameters": parameters or {}})
        rows = parameters.get("anchors") if parameters else []
        return [{"synced": len(rows or [])}]


def test_graphiti_anchor_client_syncs_anchors_in_batches():
    neo4j = FakeNeo4j()
    anchors = [
        CommonSenseAnchorDTO(
            anchor_id=f"Enterprise:wiki:Q{index}",
            type_name="Enterprise",
            name=f"企业{index}",
            aliases=[f"alias-{index}"],
            source_graph="incore_common_neo4j",
        )
        for index in range(3)
    ]

    result = GraphitiAnchorClient(neo4j=neo4j).sync_anchors(anchors)

    assert result == {"synced": 3, "skipped": 0}
    assert len(neo4j.calls) == 1
    assert "UNWIND $anchors AS anchor" in neo4j.calls[0]["query"]
    assert len(neo4j.calls[0]["parameters"]["anchors"]) == 3
