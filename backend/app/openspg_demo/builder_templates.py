"""BuilderChain 模板（KAG 风格的演示用链路）。"""

from typing import Any, Dict, List


def get_robot_chain_mvp_builder_template() -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = [
        {
            "name": "SourceNormalize",
            "kind": "transform",
            "input": "zhilian_raw_news",
            "output": "news_normalized",
            "idempotent_key": "doc_hash",
            "description": "统一 zhilian-robot 爬虫/RSS 输出字段，补齐 doc_id/doc_hash/source/publish_time。",
        },
        {
            "name": "DomainFilter",
            "kind": "filter",
            "input": "news_normalized",
            "output": "news_robot_chain_only",
            "description": "机器人主链领域过滤（整机厂、核心零部件、集成商关键词与实体先验）。",
        },
        {
            "name": "Chunking",
            "kind": "chunk",
            "input": "news_robot_chain_only",
            "output": "news_chunks",
            "description": "标题+摘要+正文切块，供 KAG 抽取与索引。",
        },
        {
            "name": "KAGExtraction",
            "kind": "llm_extract",
            "input": "news_chunks",
            "output": "extracted_mentions_and_events",
            "description": "抽取实体、关系、事件、时间、证据片段和摘要。",
        },
        {
            "name": "EntityLinking",
            "kind": "normalize",
            "input": "extracted_mentions_and_events",
            "output": "canonicalized_entities",
            "description": "企业/产品/部件名称归一，生成 canonical entity。",
        },
        {
            "name": "EventMerge",
            "kind": "aggregate",
            "input": "canonicalized_entities",
            "output": "deduped_events",
            "idempotent_key": "event_hash",
            "description": "按事件类型+主体+客体+时间窗合并多源重复报道。",
        },
        {
            "name": "GraphAndIndexSink",
            "kind": "sink",
            "input": "deduped_events",
            "output": "openspg_graph_and_search",
            "description": "写入 OpenSPG 图谱与检索索引，保留 evidence/source_url/doc_id。",
        },
    ]

    edges = [
        ("SourceNormalize", "DomainFilter"),
        ("DomainFilter", "Chunking"),
        ("Chunking", "KAGExtraction"),
        ("KAGExtraction", "EntityLinking"),
        ("EntityLinking", "EventMerge"),
        ("EventMerge", "GraphAndIndexSink"),
    ]

    return {
        "builder_chain_name": "zhilian_robot_headlines_mvp",
        "schedule": {
            "mode": "semi_realtime",
            "recommended_interval_minutes": 15,
            "batch_source": "jsonl_or_minio",
        },
        "nodes": nodes,
        "edges": [{"from": src, "to": dst} for src, dst in edges],
        "headlines_scoring": {
            "formula": "freshness * event_weight * source_credibility * multi_source_bonus * extraction_confidence",
            "event_weights": {
                "cooperation": 1.0,
                "financing": 1.2,
                "product_release": 1.0,
                "order": 1.1,
                "capacity_expansion": 1.0,
                "policy": 1.3,
            },
        },
        "bridge_contract": {
            "required_fields": [
                "doc_id",
                "doc_hash",
                "title",
                "content",
                "source_name",
                "source_url",
                "publish_time",
                "crawl_time",
            ],
            "source_system": "zhilian-robot",
        },
    }

