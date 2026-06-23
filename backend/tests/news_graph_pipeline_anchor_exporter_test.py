from app.news_graph_pipeline.anchor_exporter import CommonSenseAnchorExporter


class FakeNeo4j:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute_query(self, query, parameters=None):
        self.calls.append({"query": query, "parameters": parameters or {}})
        return self.rows


def test_anchor_exporter_loads_common_sense_nodes_with_aliases_and_source_version():
    neo4j = FakeNeo4j(
        [
            {
                "node": {
                    "id": "Enterprise:wiki:Q20716",
                    "name": "三星",
                    "alias": ["三星集团"],
                    "nameEn": ["Samsung Group"],
                    "description": "韩国综合性企业集团。",
                    "sourceVersion": "wikidata_v2_202606",
                },
                "labels": ["Entity", "IncCore.Enterprise"],
            },
            {
                "node": {
                    "graph_id": "Product:wiki:Q123",
                    "name": "高带宽内存",
                    "aliases": '["HBM"]',
                    "summary": "AI 服务器关键存储产品。",
                },
                "labels": ["Product"],
            },
        ]
    )

    anchors = CommonSenseAnchorExporter(neo4j=neo4j).load_anchors(limit=10)

    assert [item.anchor_id for item in anchors] == ["Enterprise:wiki:Q20716", "Product:wiki:Q123"]
    assert anchors[0].type_name == "Enterprise"
    assert "三星集团" in anchors[0].aliases
    assert "Samsung Group" in anchors[0].aliases
    assert anchors[0].source_graph == "incore_common_neo4j"
    assert anchors[0].source_version == "wikidata_v2_202606"
    assert anchors[1].aliases == ["HBM"]
    assert neo4j.calls[0]["parameters"]["limit"] == 10


def test_anchor_exporter_skips_legacy_news_fusion_and_stub_nodes():
    neo4j = FakeNeo4j(
        [
            {
                "node": {
                    "id": "Enterprise:fusion:graphiti:de905d80-432a-4d71-8865-a1bf4af5fee6",
                    "name": "忆联",
                    "batchId": "graphiti_news_100_all_20260607",
                    "sourceSystem": "graphiti_news",
                },
                "labels": ["IncoreFusionNode", "Enterprise"],
            },
            {
                "node": {
                    "id": "Enterprise:wiki:Q20716",
                    "name": "Enterprise:wiki:Q20716",
                    "batchId": "graphiti_news_100_all_20260607",
                    "sourceSystem": "fusion_batch_stub",
                    "isStub": True,
                },
                "labels": ["IncoreFusionNode", "Enterprise"],
            },
            {
                "node": {
                    "id": "Enterprise:wiki:Q20716",
                    "name": "三星集团",
                    "alias": ["三星", "Samsung Group"],
                    "sourceVersion": "wikidata_v2_202606",
                },
                "labels": ["IncCore.Enterprise"],
            },
        ]
    )

    anchors = CommonSenseAnchorExporter(neo4j=neo4j).load_anchors(limit=10)

    assert [item.anchor_id for item in anchors] == ["Enterprise:wiki:Q20716"]
    assert anchors[0].name == "三星集团"
    assert anchors[0].source_version == "wikidata_v2_202606"
