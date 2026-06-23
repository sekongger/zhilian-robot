"""News pipeline constants and helpers."""

from __future__ import annotations

from typing import Dict

SOURCE_NEWS_COLLECTION = "news_pipeline_source_news"
ENTITY_COLLECTION = "news_pipeline_entity_instances"
STATEMENT_COLLECTION = "news_pipeline_statements"
EVIDENCE_COLLECTION = "news_pipeline_statement_evidences"
KG_INPUT_QUEUE_COLLECTION = "kg_input_queue"
KG_BUILD_RUN_COLLECTION = "kg_build_runs"

ENTITY_CATEGORY_MAP: Dict[str, str] = {
    "companies": "subject",
    "persons": "subject",
    "products": "element",
    "technologies": "element",
    "locations": "concept",
}

ENTITY_TYPE_MAP: Dict[str, str] = {
    "companies": "company",
    "persons": "person",
    "products": "product",
    "technologies": "technology",
    "locations": "location",
}

ENTITY_CLASS_MAP: Dict[str, str] = {
    "companies": "ont:Company",
    "persons": "ont:Person",
    "products": "ont:Product",
    "technologies": "ont:Technology",
    "locations": "ont:Location",
    "events": "ont:Event",
    "documents": "ont:Document",
}

PREDICATE_MAP: Dict[str, str] = {
    "collaborates_with": "rel:collaborates_with",
    "cooperate_with": "rel:collaborates_with",
    "partner_with": "rel:collaborates_with",
    "合作": "rel:collaborates_with",
    "战略合作": "rel:collaborates_with",
}

DEFAULT_SOURCE_TYPE = "news"
DEFAULT_EXTRACTION_METHOD = "llm"
