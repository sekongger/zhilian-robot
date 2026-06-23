"""Bridge utilities between workbench DTOs and KAG builder components."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional


def ensure_kag_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    kag_root = repo_root / "modules" / "kag"
    kag_root_str = str(kag_root)
    if kag_root.exists() and kag_root_str not in sys.path:
        sys.path.insert(0, kag_root_str)


def resolve_project_host() -> str:
    return (
        os.getenv("KNOWLEDGE_OPERATOR_KAG_HOST_ADDR")
        or os.getenv("KAG_PROJECT_HOST_ADDR")
        or "http://127.0.0.1:8887"
    )


def resolve_project_id() -> int:
    raw = (
        os.getenv("KNOWLEDGE_OPERATOR_KAG_PROJECT_ID")
        or os.getenv("KAG_PROJECT_ID")
        or "3"
    )
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return 3


@lru_cache(maxsize=8)
def ensure_kag_task_config(
    *,
    host_addr: Optional[str] = None,
    project_id: Optional[int] = None,
    language: str = "zh",
    biz_scene: str = "default",
    namespace: Optional[str] = None,
) -> str:
    ensure_kag_import_path()
    from kag.common.conf import KAGConfigAccessor, KAGConfigMgr, KAGConstants

    resolved_host = host_addr or resolve_project_host()
    resolved_project_id = project_id or resolve_project_id()
    resolved_namespace = namespace or os.getenv("KAG_NAMESPACE") or "IncCore"
    task_id = f"knowledge_operator_kag::{resolved_project_id}@{resolved_host}:{language}:{biz_scene}:{resolved_namespace}"
    mgr = KAGConfigMgr()
    mgr.global_config.initialize(
        **{
            KAGConstants.KAG_PROJECT_ID_KEY: resolved_project_id,
            KAGConstants.KAG_PROJECT_HOST_ADDR_KEY: resolved_host,
            KAGConstants.KAG_LANGUAGE_KEY: language,
            KAGConstants.KAG_BIZ_SCENE_KEY: biz_scene,
            KAGConstants.KAG_NAMESPACE_KEY: resolved_namespace,
        }
    )
    KAGConfigAccessor.set_task_config(task_id, mgr)
    return task_id


def unwrap_kag_outputs(outputs: Iterable[object]) -> list[object]:
    return [getattr(item, "data", item) for item in outputs]


def chunk_dto_to_kag_chunk(chunk):
    ensure_kag_import_path()
    from kag.builder.model.chunk import Chunk as KagChunk

    return KagChunk(
        id=chunk.chunk_id,
        name=chunk.section_title or f"chunk_{chunk.chunk_index}",
        content=chunk.text,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        **dict(chunk.metadata),
    )


def document_dto_to_kag_chunk(document):
    ensure_kag_import_path()
    from kag.builder.model.chunk import Chunk as KagChunk

    return KagChunk(
        id=document.document_id,
        name=document.title or document.document_id,
        content=document.content,
        document_id=document.document_id,
        content_type=document.content_type,
        source_name=document.source_name,
        **dict(document.metadata),
    )


def source_dto_to_kag_chunk(source, content: str):
    ensure_kag_import_path()
    from kag.builder.model.chunk import Chunk as KagChunk

    return KagChunk(
        id=source.source_id,
        name=source.title or source.source_id,
        content=content,
        document_id=source.source_id,
        source_name=source.source_name,
        source_type=source.source_type,
        **dict(source.metadata),
    )


def kag_chunk_to_chunk_dto(kag_chunk, *, fallback_document_id: str, chunk_index: int):
    from app.knowledge_extraction_operators.dto import ChunkDTO

    metadata = dict(getattr(kag_chunk, "kwargs", {}) or {})
    document_id = str(metadata.pop("document_id", "") or getattr(kag_chunk, "document_id", "") or fallback_document_id)
    return ChunkDTO(
        chunk_id=str(kag_chunk.id),
        document_id=document_id,
        text=str(kag_chunk.content or ""),
        chunk_index=chunk_index,
        section_title=str(kag_chunk.name) if getattr(kag_chunk, "name", None) else None,
        metadata=metadata,
    )


def kag_chunks_to_document_dto(kag_chunks, source, *, content_type: str, reader_name: str):
    from app.knowledge_extraction_operators.dto import DocumentDTO

    chunks = list(kag_chunks)
    content = "\n\n".join(str(getattr(chunk, "content", "") or "") for chunk in chunks).strip()
    metadata = dict(source.metadata)
    metadata["kag_reader"] = reader_name
    metadata["kag_chunk_count"] = len(chunks)
    return DocumentDTO(
        document_id=source.source_id,
        title=source.title,
        content=content,
        content_type=content_type,
        source_name=source.source_name,
        metadata=metadata,
    )


def graph_batch_to_kag_subgraph(batch, *, include_internal_properties: bool = True):
    ensure_kag_import_path()
    from kag.builder.model.sub_graph import SubGraph

    graph = SubGraph(nodes=[], edges=[])
    type_by_graph_id: dict[str, str] = {}
    nodes = [
        *batch.concept_nodes,
        *batch.entity_nodes,
        *batch.event_nodes,
        *batch.document_nodes,
        *batch.chunk_nodes,
    ]
    for node in nodes:
        properties = _graph_properties(
            node.properties, include_internal_properties=include_internal_properties
        )
        if node.name not in (None, "") and "name" not in properties:
            properties["name"] = node.name
        graph.add_node(
            id=node.graph_id,
            name=node.name or node.graph_id,
            label=node.type_name,
            properties=properties,
        )
        type_by_graph_id[node.graph_id] = node.type_name

    for edge in batch.edges:
        source_type = type_by_graph_id.get(
            edge.subject_graph_id
        ) or edge.subject_graph_id.split(":", 1)[0]
        target_type = type_by_graph_id.get(
            edge.object_graph_id
        ) or edge.object_graph_id.split(":", 1)[0]
        graph.add_edge(
            s_id=edge.subject_graph_id,
            s_label=source_type,
            p=edge.predicate,
            o_id=edge.object_graph_id,
            o_label=target_type,
            properties=_graph_properties(
                edge.properties, include_internal_properties=include_internal_properties
            ),
        )
    return graph


def _graph_properties(properties, *, include_internal_properties: bool):
    if include_internal_properties:
        return dict(properties)
    return {
        key: value for key, value in dict(properties).items() if not key.startswith("_")
    }
