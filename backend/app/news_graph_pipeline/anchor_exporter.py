"""Export common-sense Neo4j nodes into Graphiti anchor DTOs."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable, Optional

from app.news_graph_mcp.neo4j_client import Neo4jGraphClient
from app.news_graph_pipeline.dto import CommonSenseAnchorDTO


class CommonSenseAnchorExporter:
    """Read stable common-sense nodes from Neo4j and normalize anchor fields."""

    TYPE_LABELS = {
        "IncCore.Enterprise": "Enterprise",
        "Enterprise": "Enterprise",
        "Company": "Enterprise",
        "IncCore.Product": "Product",
        "Product": "Product",
        "ProductModel": "ProductModel",
        "IncCore.ProductModel": "ProductModel",
        "Technology": "Technology",
        "IncCore.Technology": "Technology",
        "Industry": "Industry",
        "IndustryGroup": "IndustryGroup",
        "EconomicSector": "EconomicSector",
        "Region": "Region",
        "IncCore.Region": "Region",
        "Organization": "Organization",
    }

    def __init__(self, *, neo4j: Optional[Any] = None, source_graph: str = "incore_common_neo4j") -> None:
        self.neo4j = neo4j or Neo4jGraphClient(
            uri=os.getenv("COMMON_GRAPH_NEO4J_URI") or os.getenv("NEWS_COMMON_NEO4J_URI"),
            user=os.getenv("COMMON_GRAPH_NEO4J_USER") or os.getenv("NEWS_COMMON_NEO4J_USER"),
            password=os.getenv("COMMON_GRAPH_NEO4J_PASSWORD") or os.getenv("NEWS_COMMON_NEO4J_PASSWORD"),
            database=os.getenv("COMMON_GRAPH_NEO4J_DATABASE") or os.getenv("NEWS_COMMON_NEO4J_DATABASE"),
        )
        self.source_graph = source_graph

    def load_anchors(self, *, limit: int = 5000) -> list[CommonSenseAnchorDTO]:
        records = self.neo4j.execute_query(self._anchor_query(), {"limit": int(limit)})
        anchors: list[CommonSenseAnchorDTO] = []
        for record in records:
            anchor = self._normalize_record(record)
            if anchor is not None:
                anchors.append(anchor)
        return anchors

    def _normalize_record(self, record: dict[str, Any]) -> CommonSenseAnchorDTO | None:
        node = dict(record.get("node") or record.get("properties") or {})
        labels = [str(item) for item in record.get("labels") or []]
        anchor_id = str(
            node.get("id")
            or node.get("graph_id")
            or node.get("canonicalGraphId")
            or node.get("uuid")
            or ""
        ).strip()
        name = str(node.get("name") or node.get("title") or node.get("label") or "").strip()
        if not anchor_id or not name:
            return None
        if self._is_legacy_news_fusion_or_stub(anchor_id=anchor_id, name=name, node=node):
            return None
        type_name = self._resolve_type(labels, node)
        aliases = self._collect_aliases(name, node)
        description = str(node.get("description") or node.get("summary") or node.get("abstract") or "").strip()
        source_version = str(
            node.get("sourceVersion")
            or node.get("source_version")
            or node.get("batchId")
            or node.get("batch_id")
            or ""
        ).strip() or None
        return CommonSenseAnchorDTO(
            anchor_id=anchor_id,
            type_name=type_name,
            name=name,
            aliases=aliases,
            description=description,
            source_graph=self.source_graph,
            source_version=source_version,
            properties=node,
        )

    def _is_legacy_news_fusion_or_stub(
        self,
        *,
        anchor_id: str,
        name: str,
        node: dict[str, Any],
    ) -> bool:
        """Reject old news-fusion output; anchors must come from stable common-sense data."""

        normalized_id = anchor_id.lower()
        if ":fusion:" in normalized_id:
            return True
        if self._is_truthy(node.get("isStub") or node.get("is_stub")):
            return True
        if name.strip() == anchor_id.strip():
            return True

        source_system = str(node.get("sourceSystem") or node.get("source_system") or "").strip().lower()
        if source_system in {"fusion_batch_stub", "graphiti_news", "octopus_news"}:
            return True

        source_values = [
            node.get("sourceVersion"),
            node.get("source_version"),
            node.get("batchId"),
            node.get("batch_id"),
        ]
        for value in source_values:
            text = str(value or "").strip().lower()
            if text.startswith(("graphiti_news_", "octopus_news_")):
                return True
        return False

    def _resolve_type(self, labels: list[str], node: dict[str, Any]) -> str:
        raw_type = str(node.get("type_name") or node.get("type") or node.get("sourceType") or "").strip()
        if raw_type:
            return self.TYPE_LABELS.get(raw_type, raw_type)
        for label in reversed(labels):
            resolved = self.TYPE_LABELS.get(label)
            if resolved:
                return resolved
        for label in reversed(labels):
            if label not in {"Entity", "IncoreFusionNode"}:
                return label.split(".")[-1]
        return "Unknown"

    def _collect_aliases(self, name: str, node: dict[str, Any]) -> list[str]:
        values: list[str] = []
        for key in ("alias", "aliases", "nameEn", "officialName", "shortName"):
            values.extend(self._iter_alias_values(node.get(key)))
        return self._unique_strings(values)

    def _iter_alias_values(self, value: Any) -> Iterable[str]:
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("[") and text.endswith("]"):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item not in (None, "")]
            return [text]
        return [str(value)]

    @staticmethod
    def _unique_strings(values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = re.sub(r"\s+", " ", str(value).strip())
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "y"}

    @staticmethod
    def _anchor_query() -> str:
        return """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
          'IncCore.Enterprise', 'Enterprise', 'Company',
          'IncCore.Product', 'Product', 'ProductModel', 'IncCore.ProductModel',
          'Technology', 'IncCore.Technology',
          'Industry', 'IndustryGroup', 'EconomicSector',
          'Region', 'IncCore.Region', 'Organization'
        ])
        WITH n, properties(n) AS p
        WITH
          n,
          coalesce(p.id, p.graph_id, p.canonicalGraphId, p.uuid, '') AS anchor_id,
          coalesce(p.name, p.title, p.label, '') AS anchor_name,
          coalesce(p.sourceSystem, p.source_system, '') AS source_system,
          coalesce(p.sourceVersion, p.source_version, p.batchId, p.batch_id, '') AS source_version,
          coalesce(p.isStub, p.is_stub, false) AS is_stub
        WHERE NOT toLower(anchor_id) CONTAINS ':fusion:'
          AND is_stub <> true
          AND anchor_name <> anchor_id
          AND NOT toLower(source_system) IN ['fusion_batch_stub', 'graphiti_news', 'octopus_news']
          AND NOT toLower(source_version) STARTS WITH 'graphiti_news_'
          AND NOT toLower(source_version) STARTS WITH 'octopus_news_'
        RETURN properties(n) AS node, labels(n) AS labels
        LIMIT $limit
        """
