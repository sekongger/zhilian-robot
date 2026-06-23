from app.openspg_demo.builder_templates import get_robot_chain_mvp_builder_template
from app.openspg_demo.bridge import export_news_batch_to_jsonl_lines
from app.openspg_demo.schema_templates import (
    get_my_news_demo_schema_script,
    get_robot_chain_mvp_schema_template,
)


def test_schema_template_contains_required_types_and_relations():
    data = get_robot_chain_mvp_schema_template()
    labels = {item["label"] for item in data["types"]}
    relation_labels = {item["label"] for item in data["relations"]}

    assert "NewsArticle" in labels
    assert "IndustryEvent" in labels
    assert "Company" in labels
    assert "reports" in relation_labels
    assert "involves" in relation_labels


def test_builder_template_contains_expected_chain_nodes():
    data = get_robot_chain_mvp_builder_template()
    node_names = [node["name"] for node in data["nodes"]]
    assert node_names[:3] == ["SourceNormalize", "DomainFilter", "Chunking"]
    assert "EventMerge" in node_names
    assert "GraphAndIndexSink" in node_names


def test_my_news_demo_schema_script_contains_core_types_and_relations():
    script = get_my_news_demo_schema_script()
    assert script.startswith("namespace ")
    assert "namespace MyNewsDemo" in script
    assert "Document(资讯文档): EntityType" in script
    assert "KnowledgePoint(知识点): EntityType" in script
    assert "mentionsCompany(提及公司): Company" in script
    assert "fromChunk(源自文本块): Chunk" in script


def test_bridge_export_normalizes_news_into_jsonl_lines():
    rows = [
        {
            "title": "某机器人公司与某汽车厂签署合作协议",
            "content": "双方将联合推进产线自动化升级。",
            "url": "https://example.com/a",
            "source": "rss_36kr",
            "published_at": "2026-02-26T10:00:00",
        }
    ]
    lines = export_news_batch_to_jsonl_lines(rows)
    assert len(lines) == 1
    assert "\"doc_id\"" in lines[0]
    assert "\"doc_hash\"" in lines[0]
    assert "\"source_name\":\"rss_36kr\"" in lines[0]
