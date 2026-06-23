"""KAG-backed extraction adapter with safe fallback semantics."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from config.settings import settings

from app.knowledge_extraction_operators.dto import ChunkDTO


logger = logging.getLogger(__name__)

_BACKEND_LOCK = Lock()
_BACKEND_DISABLED_REASON: Optional[str] = None


@dataclass
class KagExtractionPayload:
    entities: List[Dict[str, Any]]
    standardized_entities: List[Dict[str, Any]]
    relations: List[List[Any]]
    events: List[Dict[str, Any]]


def _ensure_kag_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    kag_root = repo_root / "modules" / "kag"
    kag_root_str = str(kag_root)
    if kag_root.exists() and kag_root_str not in sys.path:
        sys.path.insert(0, kag_root_str)


def _resolve_project_host() -> Optional[str]:
    return (
        os.getenv("KNOWLEDGE_OPERATOR_KAG_HOST_ADDR")
        or os.getenv("KAG_PROJECT_HOST_ADDR")
        or "http://127.0.0.1:8887"
    )


def _resolve_project_id() -> Optional[int]:
    raw = (
        os.getenv("KNOWLEDGE_OPERATOR_KAG_PROJECT_ID")
        or os.getenv("KAG_PROJECT_ID")
        or "3"
    )
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return None


def _build_task_config(host_addr: str, project_id: int):
    from kag.common.conf import KAGConfigAccessor, KAGConfigMgr, KAGConstants

    task_id = f"knowledge_operator_kag::{project_id}@{host_addr}"
    mgr = KAGConfigMgr()
    mgr.global_config.initialize(
        **{
            KAGConstants.KAG_PROJECT_ID_KEY: project_id,
            KAGConstants.KAG_PROJECT_HOST_ADDR_KEY: host_addr,
            KAGConstants.KAG_LANGUAGE_KEY: "zh",
            KAGConstants.KAG_BIZ_SCENE_KEY: "default",
        }
    )
    KAGConfigAccessor.set_task_config(task_id, mgr)
    return task_id


class KagSchemaConstraintBackend:
    """Thin adapter around KAG SchemaConstraintExtractor methods."""

    def __init__(self):
        _ensure_kag_import_path()

        from kag.builder.component.extractor.schema_constraint_extractor import (
            SchemaConstraintExtractor,
        )
        from kag.builder.prompt.spg_prompt import (  # noqa: F401
            SPGEventPrompt,
            SPGRelationPrompt,
        )
        from kag.builder.model.chunk import Chunk as KagChunk
        from kag.common.llm.openai_client import OpenAIClient
        from kag.interface import PromptABC

        host_addr = _resolve_project_host()
        project_id = _resolve_project_id()
        if not host_addr or project_id is None:
            raise RuntimeError("missing KAG project host/project configuration")
        if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL or not settings.OPENAI_API_BASE:
            raise RuntimeError("missing OpenAI settings for KAG extractor")

        self._task_id = _build_task_config(host_addr=host_addr, project_id=project_id)
        self._chunk_cls = KagChunk
        self._extractor = SchemaConstraintExtractor(
            llm=OpenAIClient(
                base_url=settings.OPENAI_API_BASE,
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
                kag_qa_task_config_key=self._task_id,
            ),
            relation_prompt=PromptABC.from_config({"type": "spg_relation"}),
            event_prompt=PromptABC.from_config({"type": "spg_event"}),
            kag_qa_task_config_key=self._task_id,
        )

    def extract(self, chunk: ChunkDTO) -> KagExtractionPayload:
        kag_chunk = self._chunk_cls(
            id=chunk.chunk_id,
            name=chunk.section_title or f"chunk_{chunk.chunk_index}",
            content=chunk.text,
            document_id=chunk.document_id,
            **chunk.metadata,
        )
        passage = f"{kag_chunk.name}\n{kag_chunk.content}"
        entities = self._extractor.named_entity_recognition(passage)
        named_entities = [
            {"name": item.get("name"), "category": item.get("category")}
            for item in entities
            if item.get("name") and item.get("category")
        ]
        standardized_entities = self._extractor.named_entity_standardization(
            passage, named_entities
        )
        self._extractor.append_official_name(entities, standardized_entities)
        relations = self._extractor.relations_extraction(passage, named_entities)
        events = self._extractor.event_extraction(passage)
        return KagExtractionPayload(
            entities=entities or [],
            standardized_entities=standardized_entities or [],
            relations=relations or [],
            events=events or [],
        )


@lru_cache(maxsize=1)
def _create_backend() -> Optional[KagSchemaConstraintBackend]:
    global _BACKEND_DISABLED_REASON
    with _BACKEND_LOCK:
        if _BACKEND_DISABLED_REASON is not None:
            return None
        try:
            backend = KagSchemaConstraintBackend()
            logger.info("KAG extraction backend initialized for knowledge operators.")
            return backend
        except Exception as exc:  # pragma: no cover - covered via monkeypatched paths
            _BACKEND_DISABLED_REASON = str(exc)
            logger.warning("KAG extraction backend unavailable, fallback enabled: %s", exc)
            return None


def get_kag_backend() -> Optional[KagSchemaConstraintBackend]:
    return _create_backend()


def disable_kag_backend(reason: str) -> None:
    global _BACKEND_DISABLED_REASON
    with _BACKEND_LOCK:
        _BACKEND_DISABLED_REASON = reason
        _create_backend.cache_clear()


def reset_kag_backend_state() -> None:
    global _BACKEND_DISABLED_REASON
    with _BACKEND_LOCK:
        _BACKEND_DISABLED_REASON = None
        _create_backend.cache_clear()
