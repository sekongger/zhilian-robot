from app.services.big_graph_service import BigGraphService


class FakeNeo4j:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute_query(self, query, parameters=None):
        self.calls.append({"query": query, "parameters": parameters or {}})
        if not self.responses:
            return []
        return self.responses.pop(0)


def test_get_entity_overview_returns_canonical_news_profiles_and_relations():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "properties": {"id": "Enterprise:wiki:Q20716", "name": '"Q20716"'},
                    "labels": ["Entity", "IncCore.Enterprise"],
                }
            ],
            [
                {
                    "properties": {
                        "id": "NewsEntityProfile:v2:samsung",
                        "name": "三星",
                        "canonicalGraphId": "Enterprise:wiki:Q20716",
                        "batchId": "batch-1",
                    },
                    "labels": ["IncoreFusionNode", "NewsEntityProfile"],
                }
            ],
            [
                {
                    "source": {"id": "NewsEntityProfile:v2:samsung", "name": "三星"},
                    "source_labels": ["NewsEntityProfile"],
                    "target": {"id": "Enterprise:wiki:Q20716", "name": '"Q20716"'},
                    "target_labels": ["Entity", "IncCore.Enterprise"],
                    "relationship": {"predicate": "refersTo"},
                    "relationship_type": "refersTo",
                }
            ],
            [],
        ]
    )

    payload = BigGraphService(neo4j=neo4j).get_entity_overview("Enterprise:wiki:Q20716", batch_id="batch-1")

    assert payload["canonical"]["id"] == "Enterprise:wiki:Q20716"
    assert payload["news_profiles"][0]["id"] == "NewsEntityProfile:v2:samsung"
    assert payload["key_relations"][0]["relationship"]["type"] == "refersTo"
    assert neo4j.calls[1]["parameters"]["batch_id"] == "batch-1"


def test_search_entity_returns_canonical_and_news_profile_results():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "properties": {"id": "Enterprise:wiki:Q860580", "name": '"Q860580"', "alias": '["腾讯"]'},
                    "labels": ["Entity", "IncCore.Enterprise"],
                }
            ],
            [
                {
                    "properties": {
                        "id": "NewsEntityProfile:v2:tencent",
                        "name": "腾讯",
                        "canonicalGraphId": "Enterprise:wiki:Q860580",
                    },
                    "labels": ["IncoreFusionNode", "NewsEntityProfile"],
                }
            ],
        ]
    )

    payload = BigGraphService(neo4j=neo4j).search_entity("腾讯")

    assert payload["query"] == "腾讯"
    assert payload["items"][0]["layer"] == "canonical"
    assert payload["items"][1]["layer"] == "news_profile"
    assert len(neo4j.calls) == 2


def test_get_local_subgraph_filters_layers_in_service():
    neo4j = FakeNeo4j(
        [
            [
                {
                    "nodes": [
                        {"id": "Enterprise:wiki:Q20716", "name": '"Q20716"', "labels": ["Entity", "IncCore.Enterprise"]},
                        {
                            "id": "NewsEntityProfile:v2:samsung",
                            "name": "三星",
                            "labels": ["IncoreFusionNode", "NewsEntityProfile"],
                        },
                    ],
                    "relationships": [
                        {
                            "source": "NewsEntityProfile:v2:samsung",
                            "target": "Enterprise:wiki:Q20716",
                            "type": "refersTo",
                            "properties": {},
                        }
                    ],
                }
            ]
        ]
    )

    payload = BigGraphService(neo4j=neo4j).get_local_subgraph(
        "Enterprise:wiki:Q20716",
        depth=1,
        layers=["news"],
    )

    assert [node["id"] for node in payload["nodes"]] == ["NewsEntityProfile:v2:samsung"]
    assert payload["edges"] == []
