"""Persistence for published knowledge computing pipelines."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List

from app.database.mongodb import MongoDBConnection
from app.knowledge_extraction_operators.dto import (
    PipelineEdgeDTO,
    PipelineNodeDTO,
    PublishedPipelineDTO,
    PublishPipelineRequestDTO,
)


PIPELINE_COLLECTION = "knowledge_computing_pipelines"


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip()).strip("-").lower()
    return text or "pipeline"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_edges(nodes: List[PipelineNodeDTO]) -> List[PipelineEdgeDTO]:
    if len(nodes) < 2:
        return []
    return [
        PipelineEdgeDTO(source=nodes[index].key, target=nodes[index + 1].key)
        for index in range(len(nodes) - 1)
    ]


def _normalize_edge(raw: Dict[str, str]) -> PipelineEdgeDTO:
    return PipelineEdgeDTO(
        source=raw.get("source") or raw.get("from") or "",
        target=raw.get("target") or raw.get("to") or "",
    )


class PublishedPipelineRepository:
    def __init__(self, mongodb: MongoDBConnection | None = None):
        self.mongodb = mongodb or MongoDBConnection()
        self.collection_name = PIPELINE_COLLECTION

    def _collection(self):
        return self.mongodb.get_collection(self.collection_name)

    def ensure_builtin_pipelines(self, templates: List[Dict[str, object]]) -> None:
        collection = self._collection()
        for template in templates:
            key = str(template["key"])
            now = _now_iso()
            insert_doc = {
                "_id": key,
                "key": key,
                "name": template.get("name", key),
                "is_builtin": True,
                "published_by": "system",
                "created_at": template.get("created_at") or now,
            }
            mutable_doc = {
                "description": template.get("description", ""),
                "source_types": list(template.get("source_types", [])),
                "nodes": list(template.get("nodes", [])),
                "edges": [_normalize_edge(edge).model_dump() for edge in template.get("edges", [])],
                "operators": [node.get("operator") for node in template.get("nodes", []) if node.get("operator")],
                "updated_at": now,
            }
            collection.update_one(
                {"_id": key},
                {
                    "$setOnInsert": insert_doc,
                    "$set": mutable_doc,
                },
                upsert=True,
            )

    def list_pipelines(self) -> List[PublishedPipelineDTO]:
        rows = self.mongodb.find_many(
            self.collection_name,
            sort=[("is_builtin", -1), ("updated_at", -1), ("name", 1)],
        )
        pipelines = []
        for row in rows:
            pipelines.append(
                PublishedPipelineDTO(
                    key=row.get("key") or str(row.get("_id")),
                    name=row.get("name") or "",
                    description=row.get("description") or "",
                    source_types=list(row.get("source_types") or []),
                    nodes=[PipelineNodeDTO.model_validate(node) for node in row.get("nodes") or []],
                    edges=[_normalize_edge(edge) for edge in row.get("edges") or []],
                    operators=list(row.get("operators") or []),
                    is_builtin=bool(row.get("is_builtin")),
                    published_by=row.get("published_by") or "system",
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at"),
                )
            )
        return pipelines

    def publish_pipeline(self, request: PublishPipelineRequestDTO) -> PublishedPipelineDTO:
        collection = self._collection()
        base_key = _slugify(request.name)
        key = base_key
        now = _now_iso()
        suffix = 2
        while collection.find_one({"_id": key}) is not None:
            key = f"{base_key}-{suffix}"
            suffix += 1

        nodes = [
            PipelineNodeDTO(
                key=node.key or f"{key}-step-{index + 1}",
                operator=node.operator,
                title=node.title,
                lane=index,
            )
            for index, node in enumerate(request.nodes)
        ]
        edges = _build_edges(nodes)
        doc = {
            "_id": key,
            "key": key,
            "name": request.name.strip(),
            "description": request.description.strip(),
            "source_types": list(request.source_types),
            "nodes": [node.model_dump() for node in nodes],
            "edges": [edge.model_dump() for edge in edges],
            "operators": [node.operator for node in nodes],
            "is_builtin": False,
            "published_by": request.published_by or "admin",
            "created_at": now,
            "updated_at": now,
        }
        collection.insert_one(doc)
        return PublishedPipelineDTO(
            key=doc["key"],
            name=doc["name"],
            description=doc["description"],
            source_types=doc["source_types"],
            nodes=nodes,
            edges=edges,
            operators=doc["operators"],
            is_builtin=False,
            published_by=doc["published_by"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
