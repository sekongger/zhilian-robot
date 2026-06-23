"""Load a Neo4j v2 export package into fusion DTOs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import (
    Neo4jV2ExportPackageDTO,
    V2SourceEdgeDTO,
    V2SourceNodeDTO,
)


class Neo4jV2ExportLoader:
    """Parse the exported `manifest.json`, `nodes.jsonl`, and `edges.jsonl` package."""

    def load(self, export_dir: str | Path) -> Neo4jV2ExportPackageDTO:
        export_path = Path(export_dir)
        manifest_path = export_path / "manifest.json"
        nodes_path = export_path / "nodes.jsonl"
        edges_path = export_path / "edges.jsonl"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        node_lookup = self._read_nodes(nodes_path)
        edges = self._read_edges(edges_path, node_lookup=node_lookup)

        return Neo4jV2ExportPackageDTO(
            package_name=str(manifest.get("package_name") or export_path.name),
            manifest=manifest,
            export_dir=str(export_path),
            nodes=[payload for _, payload in node_lookup.values()],
            edges=edges,
        )

    def _read_nodes(self, path: Path) -> Dict[str, Tuple[str, V2SourceNodeDTO]]:
        node_lookup: Dict[str, Tuple[str, V2SourceNodeDTO]] = {}
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                source_label = self._select_source_label(raw.get("labels") or [])
                props = dict(raw.get("properties") or {})
                source_uuid = str(props.get("uuid") or raw.get("node_id") or "")
                name = props.get("name") or props.get("title")
                summary = props.get("summary") or props.get("content") or props.get("description")
                node = V2SourceNodeDTO(
                    source_system="neo4j_v2",
                    source_label=source_label,
                    source_uuid=source_uuid,
                    name=str(name) if name not in (None, "") else None,
                    summary=str(summary) if summary not in (None, "") else None,
                    properties=props,
                )
                node_lookup[str(raw.get("node_id"))] = (source_label, node)
        return node_lookup

    def _read_edges(
        self,
        path: Path,
        *,
        node_lookup: Dict[str, Tuple[str, V2SourceNodeDTO]],
    ) -> list[V2SourceEdgeDTO]:
        edges: list[V2SourceEdgeDTO] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                props = dict(raw.get("properties") or {})
                source_node = node_lookup.get(str(raw.get("source_node_id")))
                target_node = node_lookup.get(str(raw.get("target_node_id")))
                subject_uuid = str(
                    props.get("source_node_uuid")
                    or (source_node[1].source_uuid if source_node else raw.get("source_node_id"))
                )
                object_uuid = str(
                    props.get("target_node_uuid")
                    or (target_node[1].source_uuid if target_node else raw.get("target_node_id"))
                )
                predicate = self._normalize_edge_predicate(
                    edge_type=str(raw.get("type") or ""),
                    relation_name=str(props.get("name") or ""),
                )
                edges.append(
                    V2SourceEdgeDTO(
                        source_system="neo4j_v2",
                        source_edge_uuid=str(props.get("uuid") or raw.get("edge_id") or ""),
                        predicate=predicate,
                        subject_source_uuid=subject_uuid,
                        object_source_uuid=object_uuid,
                        subject_source_type=source_node[0] if source_node else None,
                        object_source_type=target_node[0] if target_node else None,
                        properties=props,
                    )
                )
        return edges

    @staticmethod
    def _select_source_label(labels: list[str]) -> str:
        for label in reversed(labels):
            if label != "Entity":
                return label
        return labels[-1] if labels else "Unknown"

    @staticmethod
    def _normalize_edge_predicate(*, edge_type: str, relation_name: str) -> str:
        normalized_type = edge_type.strip().upper()
        if normalized_type == "MENTIONS":
            return "mentions"
        if normalized_type == "RELATES_TO":
            if relation_name:
                return relation_name.strip().lower()
            return "relates_to"
        return edge_type.strip().lower() or "unknown"
