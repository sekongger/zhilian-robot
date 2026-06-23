"""Neo4j-backed writer/reader for Graphiti anchor linking."""

from __future__ import annotations

import os
from typing import Any, Optional

from app.news_graph_mcp.neo4j_client import Neo4jGraphClient
from app.news_graph_pipeline.dto import CommonSenseAnchorDTO, EntityLinkDecisionDTO


class GraphitiAnchorClient:
    """Write anchors and link decisions into the Graphiti Neo4j database."""

    def __init__(self, *, neo4j: Optional[Any] = None) -> None:
        self.neo4j = neo4j or Neo4jGraphClient(
            uri=os.getenv("GRAPHITI_NEWS_NEO4J_URI"),
            user=os.getenv("GRAPHITI_NEWS_NEO4J_USER"),
            password=os.getenv("GRAPHITI_NEWS_NEO4J_PASSWORD"),
            database=os.getenv("GRAPHITI_NEWS_NEO4J_DATABASE"),
        )

    def load_news_entities(self, *, group_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        return self.neo4j.execute_query(
            """
            MATCH (ep:Episodic)-[mention_rel]-(entity)
            WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
              AND (ep.group_id = $group_id OR ep.fusion_batch_id = $group_id)
            WITH DISTINCT entity, properties(entity) AS props, labels(entity) AS entity_labels
            WHERE NOT entity:CommonSenseAnchor
            RETURN
              coalesce(props.uuid, props.id, elementId(entity)) AS id,
              coalesce(props.name, props.title, props.label) AS name,
              coalesce(props.type_name, props.sourceType, head([label IN entity_labels WHERE label <> 'Entity'])) AS type,
              entity_labels AS labels,
              props AS properties
            LIMIT $limit
            """,
            {"group_id": group_id, "limit": int(limit)},
        )

    def sync_anchors(self, anchors: list[CommonSenseAnchorDTO]) -> dict[str, int]:
        synced = 0
        for chunk in self._chunks([self._anchor_params(anchor) for anchor in anchors], size=1000):
            if not chunk:
                continue
            self.neo4j.execute_query(
                """
                UNWIND $anchors AS anchor
                MERGE (a:CommonSenseAnchor {anchor_id: anchor.anchor_id})
                SET
                  a.id = anchor.anchor_id,
                  a.canonicalGraphId = anchor.anchor_id,
                  a.type_name = anchor.type_name,
                  a.name = anchor.name,
                  a.aliases = anchor.aliases,
                  a.description = anchor.description,
                  a.source_graph = anchor.source_graph,
                  a.source_version = anchor.source_version,
                  a.properties_json = anchor.properties_json,
                  a.updated_at = datetime()
                RETURN count(a) AS synced
                """,
                {"anchors": chunk},
            )
            synced += len(chunk)
        return {"synced": synced, "skipped": 0}

    def write_entity_links(self, decisions: list[EntityLinkDecisionDTO]) -> dict[str, int]:
        stats = {"refersTo": 0, "candidateRefersTo": 0, "unresolved": 0}
        for decision in decisions:
            stats[decision.decision] = stats.get(decision.decision, 0) + 1
            if decision.decision not in {"refersTo", "candidateRefersTo"} or not decision.candidate_anchor_id:
                self._mark_unresolved(decision)
                continue
            rel_type = decision.decision
            self.neo4j.execute_query(
                f"""
                MATCH (entity)
                WHERE coalesce(entity.uuid, entity.id, elementId(entity)) = $news_entity_id
                MATCH (anchor:CommonSenseAnchor {{anchor_id: $candidate_anchor_id}})
                MERGE (entity)-[r:{rel_type}]->(anchor)
                SET
                  r.matchScore = $match_score,
                  r.matchMethod = $match_method,
                  r.reason = $reason,
                  r.group_id = $group_id,
                  r.updated_at = datetime(),
                  entity.canonicalGraphId = CASE
                    WHEN $decision = 'refersTo' THEN $candidate_anchor_id
                    ELSE entity.canonicalGraphId
                  END,
                  entity.matchScore = $match_score,
                  entity.matchMethod = $match_method
                RETURN count(r) AS linked
                """,
                decision.dict(),
            )
        return stats

    def clear_news_group(self, *, group_id: str) -> dict[str, int]:
        self.neo4j.execute_query(
            """
            MATCH (ep:Episodic)
            WHERE ep.group_id = $group_id OR ep.fusion_batch_id = $group_id
            DETACH DELETE ep
            """,
            {"group_id": group_id},
        )
        return {"cleared_group": 1}

    def _mark_unresolved(self, decision: EntityLinkDecisionDTO) -> None:
        self.neo4j.execute_query(
            """
            MATCH (entity)
            WHERE coalesce(entity.uuid, entity.id, elementId(entity)) = $news_entity_id
            SET
              entity.linkDecision = 'unresolved',
              entity.linkReason = $reason,
              entity.linkGroupId = $group_id,
              entity.matchScore = $match_score,
              entity.matchMethod = $match_method
            RETURN count(entity) AS updated
            """,
            decision.dict(),
        )

    @staticmethod
    def _anchor_params(anchor: CommonSenseAnchorDTO) -> dict[str, Any]:
        import json

        return {
            "anchor_id": anchor.anchor_id,
            "type_name": anchor.type_name,
            "name": anchor.name,
            "aliases": anchor.aliases,
            "description": anchor.description,
            "source_graph": anchor.source_graph,
            "source_version": anchor.source_version,
            "properties_json": json.dumps(anchor.properties, ensure_ascii=False, default=str),
        }

    @staticmethod
    def _chunks(items: list[dict[str, Any]], *, size: int) -> list[list[dict[str, Any]]]:
        return [items[index : index + size] for index in range(0, len(items), size)]
