from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import CanonicalNodeIndexDTO
from app.incore_fusion_pipeline.loaders.graphiti_news_neo4j_loader import GraphitiNewsNeo4jLoader
from app.incore_fusion_pipeline.runners.graphiti_news_fusion_runner import GraphitiNewsFusionRunner


def test_graphiti_news_loader_maps_graphiti_nodes_to_fusion_dtos():
    loader = GraphitiNewsNeo4jLoader()

    package = loader.load_from_records(
        node_records=[
            {
                "node_id": "n1",
                "labels": ["Entity", "Enterprise"],
                "properties": {
                    "uuid": "enterprise-1",
                    "name": "三星",
                    "summary": "三星发布存储相关动态",
                    "group_id": "news-group",
                },
            },
            {
                "node_id": "n2",
                "labels": ["Episodic"],
                "properties": {
                    "uuid": "episode-1",
                    "name": "存储市场新闻",
                    "content": "三星在存储市场出现新的价格动态。",
                    "group_id": "news-group",
                },
            },
        ],
        edge_records=[
            {
                "edge_id": "e1",
                "type": "MENTIONS",
                "source_node_id": "n2",
                "target_node_id": "n1",
                "properties": {"uuid": "edge-1"},
            }
        ],
    )

    assert package.package_name == "graphiti_news_records"
    assert len(package.nodes) == 2
    assert package.nodes[0].source_system == "graphiti_news"
    assert package.nodes[0].source_label == "Enterprise"
    assert package.nodes[0].source_uuid == "enterprise-1"
    assert package.nodes[1].source_label == "Episodic"
    assert len(package.edges) == 1
    assert package.edges[0].predicate == "mentions"
    assert package.edges[0].subject_source_uuid == "episode-1"
    assert package.edges[0].object_source_uuid == "enterprise-1"


def test_graphiti_news_fusion_runner_attaches_news_profile_to_wikidata_node():
    loader = GraphitiNewsNeo4jLoader()
    package = loader.load_from_records(
        node_records=[
            {
                "node_id": "n1",
                "labels": ["Entity", "Enterprise"],
                "properties": {
                    "uuid": "enterprise-1",
                    "name": "三星",
                    "summary": "三星发布存储相关动态",
                },
            },
            {
                "node_id": "n2",
                "labels": ["Episodic"],
                "properties": {
                    "uuid": "episode-1",
                    "name": "存储市场新闻",
                    "content": "三星在存储市场出现新的价格动态。",
                },
            },
        ],
        edge_records=[
            {
                "edge_id": "e1",
                "type": "MENTIONS",
                "source_node_id": "n2",
                "target_node_id": "n1",
                "properties": {"uuid": "edge-1"},
            }
        ],
    )
    runner = GraphitiNewsFusionRunner()

    result = runner.run_package(
        package=package,
        canonical_index=[
            CanonicalNodeIndexDTO(
                graph_id="Enterprise:wiki:Q20716",
                type_name="Enterprise",
                name="三星",
                aliases=["Samsung", "Samsung Group"],
                properties={"officialName": "三星集团"},
            )
        ],
        batch_id="graphiti_batch_001",
    )

    assert result.batch.metadata["source_namespace"] == "graphiti"
    assert any(
        node.graph_id == "NewsEntityProfile:graphiti:enterprise-1"
        and node.type_name == "NewsEntityProfile"
        and node.properties["canonicalGraphId"] == "Enterprise:wiki:Q20716"
        and node.properties["sourceSystem"] == "graphiti_news"
        for node in result.batch.entity_nodes
    )
    assert any(
        node.graph_id == "Episodic:fusion:graphiti:episode-1"
        for node in result.batch.document_nodes
    )
    assert any(
        edge.subject_graph_id == "NewsEntityProfile:graphiti:enterprise-1"
        and edge.predicate == "refersTo"
        and edge.object_graph_id == "Enterprise:wiki:Q20716"
        for edge in result.batch.edges
    )
    assert any(
        edge.subject_graph_id == "Episodic:fusion:graphiti:episode-1"
        and edge.predicate == "mentions"
        and edge.object_graph_id == "NewsEntityProfile:graphiti:enterprise-1"
        for edge in result.batch.edges
    )
