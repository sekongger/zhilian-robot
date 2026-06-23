import json

from app.incore_fusion_pipeline.loaders.wikidata_shard_canonical_index_loader import (
    WikidataShardCanonicalIndexLoader,
)
from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner


def test_wikidata_shard_canonical_index_loader_reads_graph_batch_entity_nodes(tmp_path):
    shard_dir = tmp_path / "wikidata_shards"
    shard_dir.mkdir()
    (shard_dir / "graph_batch_000001.json").write_text(
        json.dumps(
            {
                "project": "IncCore",
                "namespace": "IncCore",
                "batch_id": "graph_batch_000001",
                "concept_nodes": [],
                "entity_nodes": [
                    {
                        "type_name": "Enterprise",
                        "graph_id": "Enterprise:wiki:Q875",
                        "name": "美光",
                        "properties": {
                            "officialName": "Micron Technology",
                            "alias": ["镁光"],
                            "nameEn": ["Micron"],
                            "_source": "wikidata",
                        },
                    },
                    {
                        "type_name": "Product",
                        "graph_id": "Product:wiki:Q123",
                        "name": "固态硬盘",
                        "properties": {
                            "alias": ["SSD"],
                            "_source": "wikidata",
                        },
                    },
                ],
                "event_nodes": [],
                "document_nodes": [],
                "chunk_nodes": [],
                "edges": [],
                "metadata": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    index = WikidataShardCanonicalIndexLoader().load_from_dir(shard_dir)

    assert len(index) == 2
    assert any(
        node.graph_id == "Enterprise:wiki:Q875"
        and node.type_name == "Enterprise"
        and node.name == "美光"
        and "镁光" in node.aliases
        and "Micron" in node.aliases
        for node in index
    )
    assert any(
        node.graph_id == "Product:wiki:Q123"
        and node.type_name == "Product"
        and "SSD" in node.aliases
        for node in index
    )


def test_wikidata_v2_fusion_runner_runs_against_wikidata_shard_directory(tmp_path):
    shard_dir = tmp_path / "wikidata_shards"
    shard_dir.mkdir()
    (shard_dir / "graph_batch_000001.json").write_text(
        json.dumps(
            {
                "project": "IncCore",
                "namespace": "IncCore",
                "batch_id": "graph_batch_000001",
                "concept_nodes": [],
                "entity_nodes": [
                    {
                        "type_name": "Enterprise",
                        "graph_id": "Enterprise:wiki:Q875",
                        "name": "美光",
                        "properties": {
                            "officialName": "Micron Technology",
                            "alias": ["镁光"],
                            "nameEn": ["Micron"],
                            "_source": "wikidata",
                        },
                    },
                    {
                        "type_name": "Product",
                        "graph_id": "Product:wiki:Q123",
                        "name": "固态硬盘",
                        "properties": {
                            "alias": ["SSD"],
                            "_source": "wikidata",
                        },
                    },
                ],
                "event_nodes": [],
                "document_nodes": [],
                "chunk_nodes": [],
                "edges": [],
                "metadata": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

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
                        "node_id": "node-enterprise-1",
                        "labels": ["Entity", "Enterprise"],
                        "properties": {
                            "uuid": "enterprise-1",
                            "name": "美光",
                            "summary": "Micron is one of three major NAND manufacturers",
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
        )
        + "\n",
        encoding="utf-8",
    )

    result = WikidataV2FusionRunner().run_export_package_with_wikidata_shards(
        export_dir=export_dir,
        wikidata_shard_dir=shard_dir,
        batch_id="fusion_export_batch_001",
    )

    assert any(item.source_uuid == "enterprise-1" and item.decision == "merge" for item in result.node_decisions)
    assert any(item.source_uuid == "product-1" and item.decision == "merge" for item in result.node_decisions)
    assert any(node.graph_id == "NewsEntityProfile:v2:enterprise-1" for node in result.batch.entity_nodes)
    assert any(node.graph_id == "NewsEntityProfile:v2:product-1" for node in result.batch.entity_nodes)
    assert not any(node.graph_id == "Enterprise:wiki:Q875" for node in result.batch.entity_nodes)
    assert not any(node.graph_id == "Product:wiki:Q123" for node in result.batch.entity_nodes)
    assert any(
        edge.subject_graph_id == "ProductModel:fusion:v2:product-model-1"
        and edge.predicate == "belongsToProduct"
        and edge.object_graph_id == "NewsEntityProfile:v2:product-1"
        for edge in result.batch.edges
    )
    assert any(
        edge.subject_graph_id == "NewsEntityProfile:v2:enterprise-1"
        and edge.predicate == "refersTo"
        and edge.object_graph_id == "Enterprise:wiki:Q875"
        for edge in result.batch.edges
    )
    assert any(
        edge.subject_graph_id == "NewsEntityProfile:v2:product-1"
        and edge.predicate == "refersTo"
        and edge.object_graph_id == "Product:wiki:Q123"
        for edge in result.batch.edges
    )
