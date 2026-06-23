from __future__ import annotations

from openks.common.adapters import MongoKnowledgeAdapter
from openks.common.base.core import BaseSolver


class NewsKgSolver(BaseSolver):
    def __init__(self, *, mongo_adapter=None):
        self.mongo = mongo_adapter or MongoKnowledgeAdapter()

    def solve(self, query):
        payload = dict(query or {})
        keyword = str(payload.get("keyword") or payload.get("entity_name") or "").strip()
        try:
            statements = self.mongo.find_many("inc_statement", query={"source_kg": "news_kg"}, limit=200, sort=[("created_at", -1)])
            entities = {
                item.get("entity_id") or item.get("_id"): item
                for item in self.mongo.find_many("entity_instances", query={"source_kg": "news_kg"}, limit=500)
            }
        except Exception:
            return {"query": payload, "results": []}

        if not keyword:
            return {"query": payload, "results": statements[:20]}

        results = []
        keyword_lower = keyword.lower()
        for statement in statements:
            subject = entities.get(statement.get("subject_id")) or {}
            obj = entities.get(statement.get("object_entity_id")) or {}
            haystack = " ".join(
                [
                    str(subject.get("canonical_name") or ""),
                    str(obj.get("canonical_name") or ""),
                    str(statement.get("predicate_label") or ""),
                    str(statement.get("evidence_text") or ""),
                ]
            ).lower()
            if keyword_lower in haystack:
                results.append(
                    {
                        "statement_id": statement.get("statement_id") or statement.get("_id"),
                        "subject": subject.get("canonical_name"),
                        "predicate": statement.get("predicate_label") or statement.get("predicate_id"),
                        "object": obj.get("canonical_name"),
                        "doc_id": statement.get("doc_id"),
                        "confidence": statement.get("confidence"),
                    }
                )
        return {"query": payload, "results": results[:20]}
