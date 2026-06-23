"""Build a canonical node index from exported Wikidata graph shard batches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import CanonicalNodeIndexDTO


class WikidataShardCanonicalIndexLoader:
    """Load canonical node views from `graph_batch_*.json` shard files."""

    NODE_BUCKETS = ("entity_nodes", "concept_nodes")

    def load_from_dir(self, shard_dir: str | Path) -> list[CanonicalNodeIndexDTO]:
        shard_path = Path(shard_dir)
        shard_files = sorted(shard_path.glob("graph_batch_*.json"))
        return self.load_from_files(shard_files)

    def load_from_files(self, shard_files: Iterable[str | Path]) -> list[CanonicalNodeIndexDTO]:
        nodes_by_graph_id: dict[str, CanonicalNodeIndexDTO] = {}
        for shard_file in shard_files:
            payload = json.loads(Path(shard_file).read_text(encoding="utf-8"))
            for bucket_name in self.NODE_BUCKETS:
                for raw_node in payload.get(bucket_name, []) or []:
                    node = self._build_index_node(raw_node)
                    existing = nodes_by_graph_id.get(node.graph_id)
                    if existing is None:
                        nodes_by_graph_id[node.graph_id] = node
                        continue
                    nodes_by_graph_id[node.graph_id] = self._merge_index_nodes(existing, node)
        return list(nodes_by_graph_id.values())

    def _build_index_node(self, raw_node: dict) -> CanonicalNodeIndexDTO:
        properties = dict(raw_node.get("properties") or {})
        aliases = self._collect_aliases(raw_node.get("name"), properties)
        return CanonicalNodeIndexDTO(
            graph_id=str(raw_node.get("graph_id") or ""),
            type_name=str(raw_node.get("type_name") or ""),
            name=str(raw_node.get("name") or properties.get("name") or ""),
            aliases=aliases,
            properties=properties,
        )

    def _merge_index_nodes(
        self,
        left: CanonicalNodeIndexDTO,
        right: CanonicalNodeIndexDTO,
    ) -> CanonicalNodeIndexDTO:
        merged_aliases = self._unique_strings([*left.aliases, *right.aliases])
        merged_properties = dict(left.properties)
        for key, value in right.properties.items():
            if key not in merged_properties or merged_properties[key] in (None, "", [], {}):
                merged_properties[key] = value
        return CanonicalNodeIndexDTO(
            graph_id=left.graph_id,
            type_name=left.type_name or right.type_name,
            name=left.name or right.name,
            aliases=merged_aliases,
            properties=merged_properties,
        )

    def _collect_aliases(self, node_name: object, properties: dict) -> list[str]:
        values: list[str] = []
        if node_name not in (None, ""):
            values.append(str(node_name))
        for key in ("alias", "aliases", "nameEn"):
            value = properties.get(key)
            if isinstance(value, list):
                values.extend(str(item) for item in value if item not in (None, ""))
            elif value not in (None, ""):
                values.append(str(value))
        for key in ("officialName", "shortName"):
            value = properties.get(key)
            if value not in (None, ""):
                values.append(str(value))
        return self._unique_strings(values)

    @staticmethod
    def _unique_strings(values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered
