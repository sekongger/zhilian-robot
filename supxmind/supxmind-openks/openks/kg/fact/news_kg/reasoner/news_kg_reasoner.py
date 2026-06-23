from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from openks.common.base.core import BaseReasoner

class NewsKgReasoner(BaseReasoner):
    def infer(self, facts):
        rows = [dict(item) for item in facts or [] if isinstance(item, dict)]
        inferred = []
        grouped = defaultdict(set)
        for item in rows:
            doc_id = str(item.get("doc_id") or "")
            subject_id = str(item.get("subject_id") or "")
            object_id = str(item.get("object_entity_id") or "")
            if doc_id:
                if subject_id:
                    grouped[doc_id].add(subject_id)
                if object_id:
                    grouped[doc_id].add(object_id)
        for doc_id, entity_ids in grouped.items():
            for left_id, right_id in combinations(sorted(entity_ids), 2):
                inferred.append(
                    {
                        "doc_id": doc_id,
                        "subject_id": left_id,
                        "predicate_id": "rel:co_occurs_with",
                        "predicate_label": "共现",
                        "object_entity_id": right_id,
                        "confidence": 0.6,
                        "source": "news_kg_reasoner",
                    }
                )
        return rows + inferred
