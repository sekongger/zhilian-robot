from app.incore_fusion_pipeline.dto.graph_import_dto import GraphImportBatchDTO
from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import (
    CanonicalNodeIndexDTO,
    FusionRunResultDTO,
    V2SourceEdgeDTO,
    V2SourceNodeDTO,
)
from app.incore_fusion_pipeline.mappers.wikidata_v2_source_mapper import WikidataV2SourceMapper
from app.incore_fusion_pipeline.resolvers.fusion_relation_planner import FusionRelationPlanner
from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner


def test_wikidata_v2_source_mapper_builds_layered_node_payload():
    mapper = WikidataV2SourceMapper()
    raw = {
        "uuid": "145f14ef-eefd-4017-b6c7-d68a855e0f37",
        "name": "美光",
        "summary": "Micron is one of three major NAND manufacturers who dominate the market",
        "mainBusiness": "NAND厂商",
        "status": "已退出消费级市场",
        "labels": ["Entity", "Enterprise"],
        "pageRank": 0.5586742135805627,
        "communityId": 408,
        "momentum_score": 1.0,
        "momentum_updated_at": "2026-05-09T05:04:02.771463000+00:00",
        "created_at": "2026-05-09T05:02:51.621916000+00:00",
    }

    node = mapper.map_node(source_label="Enterprise", raw=raw)

    assert node.original_type == "Enterprise"
    assert node.normalized_type == "Enterprise"
    assert node.match_keys["name"] == "美光"
    assert node.canonical_candidates["mainBusiness"] == "NAND厂商"
    assert node.source_profiles["v2"]["status"] == "已退出消费级市场"
    assert node.analytics["v2"]["pageRank"] == 0.5586742135805627
    assert node.fact_payload["summary"].startswith("Micron is one of three")


def test_relation_planner_routes_predicates_to_expected_layers():
    planner = FusionRelationPlanner()

    canonical_edge = V2SourceEdgeDTO(
        source_system="neo4j_v2",
        source_edge_uuid="edge-001",
        predicate="manufacturer",
        subject_source_uuid="product-model-1",
        object_source_uuid="enterprise-1",
    )
    fact_edge = V2SourceEdgeDTO(
        source_system="neo4j_v2",
        source_edge_uuid="edge-002",
        predicate="mentions",
        subject_source_uuid="episodic-1",
        object_source_uuid="enterprise-1",
    )

    canonical_plan = planner.plan(
        canonical_edge,
        resolved_subject_graph_id="ProductModel:fusion:v2:product-model-1",
        resolved_object_graph_id="Enterprise:wiki:Q875",
    )
    fact_plan = planner.plan(
        fact_edge,
        resolved_subject_graph_id="Episodic:fusion:v2:episodic-1",
        resolved_object_graph_id="Enterprise:wiki:Q875",
    )

    assert canonical_plan.target_layer == "canonical"
    assert canonical_plan.decision == "merge_canonical"
    assert fact_plan.target_layer == "fact"
    assert fact_plan.decision == "attach_fact"


def test_wikidata_v2_fusion_runner_links_matched_nodes_through_news_profiles():
    runner = WikidataV2FusionRunner()
    nodes = [
        V2SourceNodeDTO(
            source_system="neo4j_v2",
            source_label="Enterprise",
            source_uuid="enterprise-1",
            name="美光",
            summary="Micron is one of three major NAND manufacturers who dominate the market",
            properties={
                "mainBusiness": "NAND厂商",
                "labels": ["Entity", "Enterprise"],
                "momentum_score": 1.0,
                "pageRank": 0.55,
                "communityId": 408,
            },
        ),
        V2SourceNodeDTO(
            source_system="neo4j_v2",
            source_label="ProductModel",
            source_uuid="product-model-1",
            name="闪迪外置固态硬盘",
            summary="SanDisk external SSD prices increased by 200%",
            properties={
                "brand": "闪迪",
                "description": "价格自2025年12月持续上涨。",
                "labels": ["ProductModel", "Entity"],
                "momentum_score": 1.0,
            },
        ),
        V2SourceNodeDTO(
            source_system="neo4j_v2",
            source_label="Episodic",
            source_uuid="episodic-1",
            name="美光与闪迪资讯",
            summary="资讯事实单元",
            properties={"raw_text": "美光与闪迪外置固态硬盘相关资讯"},
        ),
    ]
    edges = [
        V2SourceEdgeDTO(
            source_system="neo4j_v2",
            source_edge_uuid="edge-001",
            predicate="manufacturer",
            subject_source_uuid="product-model-1",
            object_source_uuid="enterprise-1",
        ),
        V2SourceEdgeDTO(
            source_system="neo4j_v2",
            source_edge_uuid="edge-002",
            predicate="mentions",
            subject_source_uuid="episodic-1",
            object_source_uuid="enterprise-1",
        ),
    ]
    canonical_index = [
        CanonicalNodeIndexDTO(
            graph_id="Enterprise:wiki:Q875",
            type_name="Enterprise",
            name="美光",
            aliases=["Micron"],
            properties={"officialName": "Micron Technology"},
        )
    ]

    result = runner.run(
        source_nodes=nodes,
        source_edges=edges,
        canonical_index=canonical_index,
        batch_id="fusion_batch_001",
    )

    assert isinstance(result, FusionRunResultDTO)
    assert isinstance(result.batch, GraphImportBatchDTO)
    assert any(
        item.source_uuid == "enterprise-1"
        and item.decision == "merge"
        and item.resolved_graph_id == "NewsEntityProfile:v2:enterprise-1"
        and item.matched_graph_id == "Enterprise:wiki:Q875"
        for item in result.node_decisions
    )
    assert any(
        item.source_uuid == "product-model-1"
        and item.decision == "create"
        and item.resolved_graph_id == "ProductModel:fusion:v2:product-model-1"
        for item in result.node_decisions
    )
    assert any(
        node.graph_id == "NewsEntityProfile:v2:enterprise-1"
        and node.type_name == "NewsEntityProfile"
        and node.properties["canonicalGraphId"] == "Enterprise:wiki:Q875"
        and node.properties["sourceProfiles"]["v2"]["sourceType"] == "Enterprise"
        for node in result.batch.entity_nodes
    )
    assert not any(node.graph_id == "Enterprise:wiki:Q875" for node in result.batch.entity_nodes)
    assert any(node.graph_id == "ProductModel:fusion:v2:product-model-1" for node in result.batch.entity_nodes)
    assert any(node.graph_id == "Episodic:fusion:v2:episodic-1" for node in result.batch.document_nodes)
    assert any(
        edge.subject_graph_id == "ProductModel:fusion:v2:product-model-1"
        and edge.predicate == "manufacturer"
        and edge.object_graph_id == "NewsEntityProfile:v2:enterprise-1"
        for edge in result.batch.edges
    )
    assert any(
        edge.subject_graph_id == "Episodic:fusion:v2:episodic-1"
        and edge.predicate == "mentions"
        and edge.object_graph_id == "NewsEntityProfile:v2:enterprise-1"
        for edge in result.batch.edges
    )
    assert any(
        edge.subject_graph_id == "NewsEntityProfile:v2:enterprise-1"
        and edge.predicate == "refersTo"
        and edge.object_graph_id == "Enterprise:wiki:Q875"
        and edge.properties["targetLayer"] == "identity_link"
        for edge in result.batch.edges
    )
