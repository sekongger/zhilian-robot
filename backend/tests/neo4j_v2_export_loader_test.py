import json

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import CanonicalNodeIndexDTO
from app.incore_fusion_pipeline.loaders.neo4j_v2_export_loader import Neo4jV2ExportLoader
from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner


def test_neo4j_v2_export_loader_reads_export_package_shape(tmp_path):
    export_dir = tmp_path / "neo4j_v2_export"
    export_dir.mkdir()
    (export_dir / "manifest.json").write_text(
        json.dumps(
            {
                "package_name": "neo4j_v2_export",
                "node_count": 4,
                "edge_count": 2,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (export_dir / "nodes.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "node_id": "node-episodic-1",
                        "labels": ["Episodic"],
                        "properties": {
                            "uuid": "episode-1",
                            "title": "AI内存短缺推高了固态硬盘的价格",
                            "content": "资讯事实单元",
                            "news_source": "Octopus News Feed",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-enterprise-1",
                        "labels": ["Entity", "Enterprise"],
                        "properties": {
                            "uuid": "enterprise-1",
                            "name": "美光",
                            "summary": "Micron is one of three major NAND manufacturers",
                            "momentum_score": 1.0,
                            "pageRank": 0.55,
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-product-model-1",
                        "labels": ["Entity", "ProductModel"],
                        "properties": {
                            "uuid": "product-model-1",
                            "name": "闪迪外置固态硬盘",
                            "summary": "SanDisk external SSD prices increased by 200%",
                            "brand": "闪迪",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-product-1",
                        "labels": ["Entity", "Product"],
                        "properties": {
                            "uuid": "product-1",
                            "name": "固态硬盘",
                            "summary": "Solid-state drive category",
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (export_dir / "edges.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "edge_id": "edge-001",
                        "type": "MENTIONS",
                        "source_node_id": "node-episodic-1",
                        "target_node_id": "node-enterprise-1",
                        "properties": {
                            "uuid": "edge-mentions-1",
                            "created_at": "2026-05-10T00:00:00+00:00",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "edge_id": "edge-002",
                        "type": "RELATES_TO",
                        "source_node_id": "node-product-model-1",
                        "target_node_id": "node-product-1",
                        "properties": {
                            "uuid": "edge-rel-1",
                            "name": "IS_A",
                            "fact": "SanDisk external SSD is a model of solid-state drives",
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    package = Neo4jV2ExportLoader().load(export_dir)

    assert package.package_name == "neo4j_v2_export"
    assert len(package.nodes) == 4
    assert len(package.edges) == 2
    assert any(node.source_label == "Episodic" and node.summary == "资讯事实单元" for node in package.nodes)
    assert any(node.source_label == "Enterprise" and node.properties["pageRank"] == 0.55 for node in package.nodes)
    assert any(
        edge.predicate == "mentions"
        and edge.subject_source_uuid == "episode-1"
        and edge.object_source_uuid == "enterprise-1"
        for edge in package.edges
    )
    assert any(
        edge.predicate == "is_a"
        and edge.subject_source_uuid == "product-model-1"
        and edge.object_source_uuid == "product-1"
        for edge in package.edges
    )


def test_wikidata_v2_fusion_runner_runs_against_loaded_export_package(tmp_path):
    export_dir = tmp_path / "neo4j_v2_export"
    export_dir.mkdir()
    (export_dir / "manifest.json").write_text(
        json.dumps({"package_name": "neo4j_v2_export"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (export_dir / "nodes.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "node_id": "node-episodic-1",
                        "labels": ["Episodic"],
                        "properties": {
                            "uuid": "episode-1",
                            "title": "AI内存短缺推高了固态硬盘的价格",
                            "content": "资讯事实单元",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-enterprise-1",
                        "labels": ["Entity", "Enterprise"],
                        "properties": {
                            "uuid": "enterprise-1",
                            "name": "美光",
                            "summary": "Micron is one of three major NAND manufacturers",
                            "mainBusiness": "NAND厂商",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-product-model-1",
                        "labels": ["Entity", "ProductModel"],
                        "properties": {
                            "uuid": "product-model-1",
                            "name": "闪迪外置固态硬盘",
                            "brand": "闪迪",
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "node_id": "node-product-1",
                        "labels": ["Entity", "Product"],
                        "properties": {
                            "uuid": "product-1",
                            "name": "固态硬盘",
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (export_dir / "edges.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "edge_id": "edge-001",
                        "type": "MENTIONS",
                        "source_node_id": "node-episodic-1",
                        "target_node_id": "node-enterprise-1",
                        "properties": {"uuid": "edge-mentions-1"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "edge_id": "edge-002",
                        "type": "RELATES_TO",
                        "source_node_id": "node-product-model-1",
                        "target_node_id": "node-product-1",
                        "properties": {
                            "uuid": "edge-rel-1",
                            "name": "IS_A",
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    canonical_index = [
        CanonicalNodeIndexDTO(
            graph_id="Enterprise:wiki:Q875",
            type_name="Enterprise",
            name="美光",
            aliases=["Micron"],
            properties={"officialName": "Micron Technology"},
        )
    ]

    result = WikidataV2FusionRunner().run_export_package(
        export_dir=export_dir,
        canonical_index=canonical_index,
        batch_id="fusion_export_batch_001",
    )

    assert any(item.source_uuid == "enterprise-1" and item.decision == "merge" for item in result.node_decisions)
    assert any(node.graph_id == "NewsEntityProfile:v2:enterprise-1" for node in result.batch.entity_nodes)
    assert any(
        edge.subject_graph_id == "NewsEntityProfile:v2:enterprise-1"
        and edge.predicate == "refersTo"
        and edge.object_graph_id == "Enterprise:wiki:Q875"
        for edge in result.batch.edges
    )
    assert any(node.graph_id == "Episodic:fusion:v2:episode-1" for node in result.batch.document_nodes)
    assert any(
        edge.subject_graph_id == "ProductModel:fusion:v2:product-model-1"
        and edge.predicate == "belongsToProduct"
        and edge.object_graph_id == "Product:fusion:v2:product-1"
        for edge in result.batch.edges
    )
