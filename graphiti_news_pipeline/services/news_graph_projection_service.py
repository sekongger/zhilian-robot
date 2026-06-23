from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


NEWS_GRAPH_PROJECTION_VERSION = "news_projection_v1"

PROJECTED_TYPE_LABELS = {
    "EconomicSector",
    "Enterprise",
    "Industry",
    "IndustryGroup",
    "Organization",
    "Person",
    "Product",
    "ProductModel",
    "ProductTerm",
    "Region",
    "Technology",
    "Unknown",
}

RELATION_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("SUPPLIES_TO", ("supplies", "supplier", "supply", "provider", "provides", "上游", "下游", "供应")),
    ("MANUFACTURES", ("manufactures", "manufacturer", "manufacturing", "produces", "生产", "制造")),
    ("INVESTS_IN", ("invests", "investment", "financing", "funding", "融资", "投资")),
    ("COLLABORATES_WITH", ("collaborates", "cooperates", "partner", "partnership", "合作")),
    ("COMPETES_WITH", ("competes", "competition", "rival", "竞争")),
    ("RELEASES", ("releases", "released", "launches", "launched", "发布", "推出", "上市")),
    ("USES_TECHNOLOGY", ("uses", "adopts", "based on", "powered by", "使用", "采用", "搭载", "应用")),
    ("HAS_SUBSIDIARY", ("subsidiary", "owns", "owned by", "holding", "子公司", "控股")),
    ("BELONGS_TO", ("belongs", "part of", "member of", "属于", "隶属")),
    ("DRIVES_DEMAND_FOR", ("demand", "requires", "需求", "带动")),
]

ALLOWED_PROJECTED_RELATION_TYPES = {
    "BELONGS_TO",
    "COLLABORATES_WITH",
    "COMPETES_WITH",
    "DRIVES_DEMAND_FOR",
    "HAS_SUBSIDIARY",
    "INVESTS_IN",
    "MANUFACTURES",
    "MENTIONS",
    "RELATED_TO",
    "RELEASES",
    "SUPPLIES_TO",
    "USES_TECHNOLOGY",
}


def normalize_projected_type(labels: list[str] | tuple[str, ...] | None) -> str:
    label_set = {str(label) for label in labels or [] if str(label).strip()}
    if label_set.intersection({"Enterprise", "Company"}):
        return "Enterprise"
    if "ProductModel" in label_set:
        return "ProductModel"
    if "ProductTerm" in label_set:
        return "ProductTerm"
    if label_set.intersection({"Product", "ProductObject"}):
        return "Product"
    for label in [
        "Technology",
        "Person",
        "Region",
        "Industry",
        "IndustryGroup",
        "EconomicSector",
        "Organization",
    ]:
        if label in label_set:
            return label
    return "Unknown"


def normalize_projected_relation_type(
    relationship_type: str | None,
    relationship_properties: dict[str, Any] | None,
) -> str:
    raw_type = str(relationship_type or "").strip()
    if raw_type in {"MENTIONS", "mentions"}:
        return "MENTIONS"
    if raw_type.startswith("PROJECTED_"):
        return "RELATED_TO"

    props = relationship_properties or {}
    searchable = " ".join(
        str(value)
        for value in [
            raw_type,
            props.get("name"),
            props.get("fact"),
            props.get("description"),
            props.get("relation"),
            props.get("predicate"),
        ]
        if value
    ).lower()
    for projected_type, keywords in RELATION_KEYWORD_RULES:
        if any(keyword.lower() in searchable for keyword in keywords):
            return projected_type
    return "RELATED_TO"


class NewsGraphProjectionService:
    """Materialize a read-only visualization projection inside the Graphiti news graph.

    The projection does not merge news data into the common-sense graph. It only
    adds derived labels/properties and PROJECTED_* relationships to existing
    Graphiti entities so Neo4j Browser and downstream query tools can inspect a
    richer business-oriented view.
    """

    def __init__(self, driver):
        self.driver = driver

    async def materialize_projection(
        self,
        *,
        group_id: str | None = None,
        limit: int = 5000,
        clear_existing: bool = False,
    ) -> dict[str, Any]:
        normalized_group_id = str(group_id).strip() if group_id else None
        normalized_limit = max(1, int(limit or 5000))
        if clear_existing:
            await self._clear_projection(group_id=normalized_group_id)

        entity_records = await self._load_entities(group_id=normalized_group_id, limit=normalized_limit)
        entity_type_counts: Counter[str] = Counter()
        for record in entity_records:
            projected_type = normalize_projected_type(record.get("labels") or [])
            entity_type_counts[projected_type] += 1
            await self._write_entity_projection(
                entity_id=record["entity_id"],
                projected_type=projected_type,
                group_id=normalized_group_id,
            )

        relationship_records = await self._load_relationships(
            group_id=normalized_group_id,
            limit=normalized_limit,
        )
        relation_type_counts: Counter[str] = Counter()
        for record in relationship_records:
            projected_type = normalize_projected_relation_type(
                record.get("relationship_type"),
                dict(record.get("relationship_properties") or {}),
            )
            if projected_type not in ALLOWED_PROJECTED_RELATION_TYPES:
                projected_type = "RELATED_TO"
            relation_type_counts[projected_type] += 1
            await self._write_relationship_projection(
                source_id=record["source_id"],
                target_id=record["target_id"],
                source_relationship_id=record.get("relationship_id") or "",
                source_relationship_type=record.get("relationship_type") or "",
                relationship_properties=dict(record.get("relationship_properties") or {}),
                projected_type=projected_type,
                group_id=normalized_group_id,
            )

        return {
            "projection_version": NEWS_GRAPH_PROJECTION_VERSION,
            "group_id": normalized_group_id,
            "projected_entities": len(entity_records),
            "projected_relationships": len(relationship_records),
            "entity_type_counts": dict(entity_type_counts),
            "relationship_type_counts": dict(relation_type_counts),
        }

    async def projection_stats(self, *, group_id: str | None = None) -> dict[str, Any]:
        normalized_group_id = str(group_id).strip() if group_id else None
        if normalized_group_id is None:
            records, _, _ = await self.driver.execute_query(
                """
                MATCH (entity:NewsProjection)
                WITH count(DISTINCT entity) AS projected_entities
                OPTIONAL MATCH ()-[rel]->()
                WHERE rel.projection_version = $projection_version
                RETURN projected_entities, count(rel) AS projected_relationships
                """,
                projection_version=NEWS_GRAPH_PROJECTION_VERSION,
            )
            row = dict(records[0]) if records else {}
            return {
                "projection_version": NEWS_GRAPH_PROJECTION_VERSION,
                "group_id": normalized_group_id,
                "projected_entities": int(row.get("projected_entities") or 0),
                "projected_relationships": int(row.get("projected_relationships") or 0),
            }

        records, _, _ = await self.driver.execute_query(
            """
            MATCH (entity:NewsProjection)
            WHERE entity.newsProjectionGroupId = $group_id
            WITH collect(DISTINCT entity) AS entities
            OPTIONAL MATCH ()-[rel]->()
            WHERE rel.projection_version = $projection_version
              AND rel.group_id = $group_id
            RETURN
              size(entities) AS projected_entities,
              count(rel) AS projected_relationships
            """,
            group_id=normalized_group_id,
            projection_version=NEWS_GRAPH_PROJECTION_VERSION,
        )
        row = dict(records[0]) if records else {}
        return {
            "projection_version": NEWS_GRAPH_PROJECTION_VERSION,
            "group_id": normalized_group_id,
            "projected_entities": int(row.get("projected_entities") or 0),
            "projected_relationships": int(row.get("projected_relationships") or 0),
        }

    async def _clear_projection(self, *, group_id: str | None) -> None:
        if group_id is None:
            await self.driver.execute_query(
                """
                MATCH ()-[r]->()
                WHERE r.projection_version = $projection_version
                DELETE r
                """,
                projection_version=NEWS_GRAPH_PROJECTION_VERSION,
            )
            await self.driver.execute_query(
                """
                MATCH (entity:NewsProjection)
                REMOVE entity:NewsProjection
                SET
                  entity.projectedType = NULL,
                  entity.newsProjectionVersion = NULL,
                  entity.newsProjectionGroupId = NULL,
                  entity.newsProjectionUpdatedAt = NULL
                """
            )
            return

        await self.driver.execute_query(
            """
            MATCH ()-[r]->()
            WHERE r.projection_version = $projection_version
              AND r.group_id = $group_id
            DELETE r
            """,
            projection_version=NEWS_GRAPH_PROJECTION_VERSION,
            group_id=group_id,
        )
        await self.driver.execute_query(
            """
            MATCH (entity:NewsProjection)
            WHERE entity.newsProjectionGroupId = $group_id
            REMOVE entity:NewsProjection
            SET
              entity.projectedType = NULL,
              entity.newsProjectionVersion = NULL,
              entity.newsProjectionGroupId = NULL,
              entity.newsProjectionUpdatedAt = NULL
            """,
            group_id=group_id,
        )

    async def _load_entities(self, *, group_id: str | None, limit: int) -> list[dict[str, Any]]:
        records, _, _ = await self.driver.execute_query(
            """
            MATCH (ep:Episodic)-[mention]-(entity:Entity)
            WHERE type(mention) IN ['MENTIONS', 'mentions']
              AND ($group_id IS NULL OR ep.group_id = $group_id OR ep.fusion_batch_id = $group_id)
            WITH DISTINCT entity
            RETURN
              elementId(entity) AS entity_id,
              labels(entity) AS labels,
              coalesce(entity.name, entity.uuid, entity.id, '') AS name
            LIMIT $limit
            """,
            group_id=group_id,
            limit=limit,
        )
        return [dict(record) for record in records]

    async def _write_entity_projection(self, *, entity_id: str, projected_type: str, group_id: str | None) -> None:
        label = projected_type if projected_type in PROJECTED_TYPE_LABELS else "Unknown"
        now = datetime.now(timezone.utc).isoformat()
        await self.driver.execute_query(
            f"""
            MATCH (entity)
            WHERE elementId(entity) = $entity_id
            SET entity:NewsProjection:{label}
            SET
              entity.projectedType = $projected_type,
              entity.newsProjectionVersion = $projection_version,
              entity.newsProjectionGroupId = $group_id,
              entity.newsProjectionUpdatedAt = $updated_at
            """,
            entity_id=entity_id,
            projected_type=projected_type,
            projection_version=NEWS_GRAPH_PROJECTION_VERSION,
            group_id=group_id,
            updated_at=now,
        )

    async def _load_relationships(self, *, group_id: str | None, limit: int) -> list[dict[str, Any]]:
        records, _, _ = await self.driver.execute_query(
            """
            MATCH (ep:Episodic)-[mention]-(source:Entity)-[rel]->(target:Entity)
            WHERE type(mention) IN ['MENTIONS', 'mentions']
              AND type(rel) <> 'MENTIONS'
              AND type(rel) <> 'mentions'
              AND NOT type(rel) STARTS WITH 'PROJECTED_'
              AND source <> target
              AND ($group_id IS NULL OR ep.group_id = $group_id OR ep.fusion_batch_id = $group_id)
            WITH DISTINCT source, target, rel
            RETURN
              elementId(source) AS source_id,
              elementId(target) AS target_id,
              elementId(rel) AS relationship_id,
              type(rel) AS relationship_type,
              properties(rel) AS relationship_properties
            LIMIT $limit
            """,
            group_id=group_id,
            limit=limit,
        )
        return [dict(record) for record in records]

    async def _write_relationship_projection(
        self,
        *,
        source_id: str,
        target_id: str,
        source_relationship_id: str,
        source_relationship_type: str,
        relationship_properties: dict[str, Any],
        projected_type: str,
        group_id: str | None,
    ) -> None:
        relationship_type = projected_type if projected_type in ALLOWED_PROJECTED_RELATION_TYPES else "RELATED_TO"
        projection_key = "|".join(
            [
                NEWS_GRAPH_PROJECTION_VERSION,
                str(group_id or "all"),
                str(source_relationship_id or f"{source_id}->{target_id}:{relationship_type}"),
            ]
        )
        await self.driver.execute_query(
            f"""
            MATCH (source)
            WHERE elementId(source) = $source_id
            MATCH (target)
            WHERE elementId(target) = $target_id
            MERGE (source)-[projected:PROJECTED_{relationship_type} {{projection_key: $projection_key}}]->(target)
            SET
              projected.projection_version = $projection_version,
              projected.projected_type = $projected_type,
              projected.group_id = $group_id,
              projected.source_relationship_id = $source_relationship_id,
              projected.source_relationship_type = $source_relationship_type,
              projected.fact = coalesce($fact, projected.fact),
              projected.name = coalesce($name, projected.name),
              projected.updated_at = $updated_at
            """,
            source_id=source_id,
            target_id=target_id,
            projection_key=projection_key,
            projection_version=NEWS_GRAPH_PROJECTION_VERSION,
            projected_type=relationship_type,
            group_id=group_id,
            source_relationship_id=source_relationship_id,
            source_relationship_type=source_relationship_type,
            fact=relationship_properties.get("fact") or relationship_properties.get("description"),
            name=relationship_properties.get("name") or relationship_properties.get("relation"),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
