"""OpenSPG importer for the IncCore fusion pipeline."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Dict, Iterable, List, Tuple

import httpx

from app.incore_fusion_pipeline.dto.graph_import_dto import (
    GraphEdgeUpsertDTO,
    GraphImportBatchDTO,
    GraphImportResultDTO,
    GraphNodeUpsertDTO,
)


logger = logging.getLogger(__name__)


class OpenSPGImporter:
    """Import graph batches through OpenSPG public graph APIs."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        project_id: int | None = None,
        timeout_seconds: float | None = None,
        user_no: str | None = None,
        vertex_batch_size: int = 50,
        edge_batch_size: int = 100,
    ) -> None:
        self.base_url = (base_url or os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887").rstrip("/")
        self.project_id = project_id
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPENSPG_TIMEOUT_SECONDS") or "30")
        self.user_no = (user_no or os.getenv("OPENSPG_USER_NO") or "openspg").strip()
        self.vertex_batch_size = vertex_batch_size
        self.edge_batch_size = edge_batch_size

    def import_batch(self, batch: GraphImportBatchDTO, *, dry_run: bool = True) -> GraphImportResultDTO:
        if dry_run:
            logger.info(
                "Dry-run import batch %s: %s nodes, %s edges",
                batch.batch_id,
                batch.node_count(),
                batch.edge_count(),
            )
            return GraphImportResultDTO(
                batch_id=batch.batch_id,
                status="dry_run",
                dry_run=True,
                node_count=batch.node_count(),
                edge_count=batch.edge_count(),
                details={
                    "project": batch.project,
                    "namespace": batch.namespace,
                },
            )

        project_id = self._resolve_project_id(batch)
        headers = self._headers()
        vertex_groups = self._build_vertex_groups(batch)
        edge_groups = self._build_edge_groups(batch)

        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds, headers=headers) as client:
            for _, grouped_vertices in vertex_groups.items():
                for chunk in self._chunked(grouped_vertices, self.vertex_batch_size):
                    self._post_json(
                        client,
                        "/public/v1/graph/upsertVertex",
                        {"projectId": project_id, "vertices": chunk},
                    )

            for _, grouped_edges in edge_groups.items():
                for chunk in self._chunked(grouped_edges, self.edge_batch_size):
                    self._post_json(
                        client,
                        "/public/v1/graph/upsertEdge",
                        {"projectId": project_id, "upsertAdjacentVertices": False, "edges": chunk},
                    )

        return GraphImportResultDTO(
            batch_id=batch.batch_id,
            status="live",
            dry_run=False,
            node_count=batch.node_count(),
            edge_count=batch.edge_count(),
            details={
                "project": batch.project,
                "project_id": project_id,
                "namespace": batch.namespace,
                "vertex_groups": len(vertex_groups),
                "edge_groups": len(edge_groups),
                "openspg_base_url": self.base_url,
            },
        )

    def import_batches(
        self, batches: Iterable[GraphImportBatchDTO], *, dry_run: bool = True
    ) -> List[GraphImportResultDTO]:
        return [self.import_batch(batch, dry_run=dry_run) for batch in batches]

    def _resolve_project_id(self, batch: GraphImportBatchDTO) -> int:
        if batch.metadata.get("project_id") is not None:
            return int(batch.metadata["project_id"])
        if self.project_id is not None:
            return int(self.project_id)
        for env_name in ("OPENSPG_PROJECT_ID", "OPENSPG_DEMO_PROJECT_ID", "FACT_LIBRARY_PROJECT_ID"):
            value = os.getenv(env_name)
            if value:
                return int(value)
        raise ValueError("OpenSPG project id is not configured.")

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.user_no:
            headers["userNo"] = self.user_no
            headers["userNumber"] = self.user_no
        return headers

    def _build_vertex_groups(self, batch: GraphImportBatchDTO) -> Dict[str, List[Dict[str, object]]]:
        groups: Dict[str, Dict[Tuple[str, str], Dict[str, object]]] = {}
        for node in [
            *batch.concept_nodes,
            *batch.entity_nodes,
            *batch.event_nodes,
            *batch.document_nodes,
            *batch.chunk_nodes,
        ]:
            qualified_type = self._qualified_type(node.type_name, batch.namespace)
            properties = dict(node.properties)
            if node.name not in (None, "") and "name" not in properties:
                properties["name"] = node.name
            payload = {
                "type": qualified_type,
                "id": node.graph_id,
                "properties": self._sanitize_properties(properties),
            }
            key = (qualified_type, node.graph_id)
            bucket = groups.setdefault(qualified_type, {})
            if key not in bucket:
                bucket[key] = payload
            else:
                self._merge_properties(bucket[key]["properties"], payload["properties"])
        return {key: list(value.values()) for key, value in groups.items()}

    def _build_edge_groups(self, batch: GraphImportBatchDTO) -> Dict[Tuple[str, str, str], List[Dict[str, object]]]:
        groups: Dict[Tuple[str, str, str], Dict[Tuple[str, str, str, str, str], Dict[str, object]]] = {}
        for edge in batch.edges:
            src_type = self._qualified_type(self._type_from_graph_id(edge.subject_graph_id), batch.namespace)
            dst_type = self._qualified_type(self._type_from_graph_id(edge.object_graph_id), batch.namespace)
            payload = {
                "srcType": src_type,
                "srcId": edge.subject_graph_id,
                "dstType": dst_type,
                "dstId": edge.object_graph_id,
                "label": edge.predicate,
                "properties": self._sanitize_properties(edge.properties),
            }
            group_key = (src_type, edge.predicate, dst_type)
            dedupe_key = (src_type, edge.subject_graph_id, edge.predicate, dst_type, edge.object_graph_id)
            bucket = groups.setdefault(group_key, {})
            if dedupe_key not in bucket:
                bucket[dedupe_key] = payload
            else:
                self._merge_properties(bucket[dedupe_key]["properties"], payload["properties"])
        return {key: list(value.values()) for key, value in groups.items()}

    def _post_json(self, client: httpx.Client, path: str, payload: Dict[str, object]) -> Dict[str, object]:
        response = client.post(path, json=payload)
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and body.get("success") is False:
            raise RuntimeError(f"OpenSPG request failed for {path}: {body}")
        return body if isinstance(body, dict) else {"response": body}

    def _merge_properties(self, target: Dict[str, object], incoming: Dict[str, object]) -> None:
        for key, value in incoming.items():
            if value in (None, "", []):
                continue
            if key not in target or target[key] in (None, "", []):
                target[key] = value

    def _sanitize_properties(self, properties: Dict[str, object]) -> Dict[str, object]:
        return {
            key: self._sanitize_value(value)
            for key, value in properties.items()
            if not key.startswith("_") and value not in (None, "", [])
        }

    def _sanitize_value(self, value: object) -> object:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value if item not in (None, "", [])]
        if isinstance(value, dict):
            return {key: self._sanitize_value(item) for key, item in value.items() if item not in (None, "", [])}
        return value

    @staticmethod
    def _qualified_type(type_name: str, namespace: str) -> str:
        if "." in type_name:
            return type_name
        return f"{namespace}.{type_name}"

    @staticmethod
    def _type_from_graph_id(graph_id: str) -> str:
        if ":" not in graph_id:
            raise ValueError(f"Graph id '{graph_id}' does not contain a type prefix.")
        return graph_id.split(":", 1)[0]

    @staticmethod
    def _chunked(items: List[Dict[str, object]], size: int) -> Iterable[List[Dict[str, object]]]:
        for index in range(0, len(items), size):
            yield items[index : index + size]
