"""Read-only query service for the fused IncCore news graph."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from app.news_graph_mcp.dto import is_traceable_source_url, normalize_enterprise_context_record, normalize_news_record
from app.news_graph_mcp.neo4j_client import Neo4jGraphClient


class NewsGraphQueryService:
    """Provide agent-facing query methods over the fused news graph."""

    def __init__(self, *, neo4j: Optional[Any] = None, clock: Optional[Callable[[], datetime]] = None) -> None:
        self.neo4j = neo4j or Neo4jGraphClient()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def query_entity_news_timeline(
        self,
        *,
        entity_name: Optional[str] = None,
        canonical_graph_id: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> Dict[str, Any]:
        params = {
            "entity_name": self._clean_optional(entity_name),
            "canonical_graph_id": self._clean_optional(canonical_graph_id),
            "start_time": self._start_time_from_hours(since_hours),
            "limit": self._expanded_query_limit(limit),
        }
        records = self.neo4j.execute_query(self._entity_timeline_query(), params)
        items = self._limit_news_items(self._traceable_news_items([normalize_news_record(record) for record in records]), limit)
        return {
            "query": "entity_news_timeline",
            "entity": {"name": params["entity_name"] or "", "canonical_graph_id": params["canonical_graph_id"] or ""},
            "time_range": {"start_time": params["start_time"]},
            "items": items,
            "warnings": [] if params["entity_name"] or params["canonical_graph_id"] else ["entity_name or canonical_graph_id is required"],
        }

    def query_enterprise_supply_chain_context(
        self,
        *,
        entity_name: Optional[str] = None,
        canonical_graph_id: Optional[str] = None,
        since_hours: int = 720,
        limit: int = 30,
    ) -> Dict[str, Any]:
        params = {
            "entity_name": self._clean_optional(entity_name),
            "canonical_graph_id": self._clean_optional(canonical_graph_id),
            "start_time": self._start_time_from_hours(since_hours),
            "limit": self._expanded_query_limit(limit),
        }
        records = self.neo4j.execute_query(self._enterprise_supply_chain_query(), params)
        context = normalize_enterprise_context_record(records[0]) if records else normalize_enterprise_context_record({})
        enterprise_name = context["enterprise"].get("name")
        if params["entity_name"] and self._looks_like_qid_name(enterprise_name):
            context["enterprise"]["name"] = params["entity_name"]
            if enterprise_name:
                context["llm_context"] = context["llm_context"].replace(str(enterprise_name), params["entity_name"])
        warnings = [] if params["entity_name"] or params["canonical_graph_id"] else ["entity_name or canonical_graph_id is required"]
        if (params["entity_name"] or params["canonical_graph_id"]) and not records:
            warnings.append("no enterprise context found")
        return {
            "query": "enterprise_supply_chain_context",
            "entity": {"name": params["entity_name"] or "", "canonical_graph_id": params["canonical_graph_id"] or ""},
            "time_range": {"start_time": params["start_time"]},
            **context,
            "warnings": warnings,
        }

    def query_news_by_source_industry(
        self,
        *,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        source_name: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        params = {
            "start_time": start_time or self._start_time_from_hours(since_hours),
            "end_time": end_time,
            "source_name": self._clean_optional(source_name),
            "industry": self._clean_optional(industry),
            "limit": self._expanded_query_limit(limit),
        }
        records = self.neo4j.execute_query(self._news_by_source_industry_query(), params)
        items = self._limit_news_items(
            self._traceable_news_items([normalize_news_record(record, include_full_content=True) for record in records]),
            limit,
        )
        return {
            "query": "news_by_source_industry",
            "time_range": {"start_time": params["start_time"], "end_time": params["end_time"]},
            "filters": {"source_name": params["source_name"], "industry": params["industry"]},
            "items": items,
            "warnings": [],
        }

    def query_recommended_news_candidates(
        self,
        *,
        industries: Optional[List[str]] = None,
        entity_names: Optional[List[str]] = None,
        product_names: Optional[List[str]] = None,
        preference_tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> Dict[str, Any]:
        params = {
            "start_time": start_time or self._start_time_from_hours(since_hours),
            "end_time": end_time,
            "industries": self._clean_list(industries),
            "entity_names": self._clean_list(entity_names),
            "product_names": self._clean_list(product_names),
            "preference_tags": self._clean_list(preference_tags),
            "limit": self._expanded_query_limit(limit),
        }
        records = self.neo4j.execute_query(self._candidate_news_query(), params)
        items = self._traceable_news_items([self._with_recommendation(normalize_news_record(record), params) for record in records])
        items.sort(key=lambda item: item["recommendation"]["score"], reverse=True)
        items = self._limit_news_items(items, limit)
        return {
            "query": "recommended_news_candidates",
            "time_range": {"start_time": params["start_time"], "end_time": params["end_time"]},
            "filters": {
                "industries": params["industries"],
                "entity_names": params["entity_names"],
                "product_names": params["product_names"],
                "preference_tags": params["preference_tags"],
            },
            "items": items,
            "llm_context": self._recommendation_llm_context(items),
            "warnings": [],
        }

    def query_subscription_news_feed(
        self,
        *,
        industries: Optional[List[str]] = None,
        enterprises: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        preference_tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        since_hours: int = 168,
        limit: int = 20,
    ) -> Dict[str, Any]:
        params = {
            "start_time": start_time or self._start_time_from_hours(since_hours),
            "end_time": end_time,
            "industries": self._clean_list(industries),
            "entity_names": self._clean_list(enterprises),
            "product_names": self._clean_list(products),
            "preference_tags": self._clean_list(preference_tags),
            "limit": self._expanded_query_limit(limit),
        }
        params["products"] = params["product_names"]
        records = self.neo4j.execute_query(self._candidate_news_query(), params)
        items = []
        for record in records:
            item = self._with_recommendation(normalize_news_record(record), params)
            item["matched_subscription"] = {
                "industries": self._matched_terms(item, params["industries"]),
                "enterprises": self._matched_terms(item, params["entity_names"]),
                "products": self._matched_terms(item, params["product_names"]),
                "preference_tags": self._matched_terms(item, params["preference_tags"]),
            }
            items.append(item)
        items = self._traceable_news_items(items)
        items.sort(key=lambda item: item["recommendation"]["score"], reverse=True)
        items = self._limit_news_items(items, limit)
        subscription_profile = {
            "industries": params["industries"],
            "enterprises": params["entity_names"],
            "products": params["product_names"],
            "preference_tags": params["preference_tags"],
        }
        return {
            "query": "subscription_news_feed",
            "subscription_profile": subscription_profile,
            "time_range": {"start_time": params["start_time"], "end_time": params["end_time"]},
            "feed_summary": self._subscription_feed_summary(subscription_profile, items),
            "items": items,
            "warnings": [] if any(subscription_profile.values()) else ["at least one subscription interest is recommended"],
        }

    def _start_time_from_hours(self, since_hours: int) -> str:
        hours = max(int(since_hours or 24), 1)
        return (self.clock() - timedelta(hours=hours)).isoformat()

    @staticmethod
    def _bounded_limit(limit: int) -> int:
        return max(1, min(int(limit or 20), 100))

    @classmethod
    def _expanded_query_limit(cls, limit: int) -> int:
        return min(cls._bounded_limit(limit) * 3, 100)

    @classmethod
    @staticmethod
    def _traceable_news_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [item for item in items if is_traceable_source_url(item.get("source_url"))]

    @classmethod
    def _limit_news_items(cls, items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        return items[: cls._bounded_limit(limit)]

    @staticmethod
    def _clean_optional(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _clean_list(values: Optional[List[str]]) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [item.strip() for item in values.split(",")]
        result = []
        seen = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def _looks_like_qid_name(value: Optional[str]) -> bool:
        if not value:
            return True
        text = str(value).strip().strip('"')
        return len(text) > 1 and text[0].upper() == "Q" and text[1:].isdigit()

    def _with_recommendation(self, item: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        industry_matches = self._matched_terms(item, params["industries"])
        entity_matches = self._matched_terms(item, params["entity_names"])
        product_matches = self._matched_terms(item, params["product_names"])
        tag_matches = self._matched_terms(item, params["preference_tags"])
        matched_terms = industry_matches + entity_matches + product_matches + tag_matches
        reasons = []
        if industry_matches:
            reasons.append(f"命中关注产业：{'、'.join(industry_matches)}。")
        if entity_matches:
            reasons.append(f"命中关注企业：{'、'.join(entity_matches)}。")
        if product_matches:
            reasons.append(f"命中关注产品/技术：{'、'.join(product_matches)}。")
        if tag_matches:
            reasons.append(f"命中偏好标签：{'、'.join(tag_matches)}。")
        if item.get("events") or item.get("relations"):
            reasons.append("包含事件或关系线索，适合作为简报材料。")
        if item.get("source_url"):
            reasons.append("带有原文链接，可追溯来源。")
        if not reasons:
            reasons.append("按时间窗口召回，可作为待筛选资讯。")

        score = 30
        score += 15 * len({*industry_matches, *entity_matches, *product_matches})
        score += 10 * len(set(tag_matches))
        score += 10 if item.get("events") else 0
        score += 10 if item.get("relations") else 0
        score += 5 if item.get("source_url") else 0
        item["recommendation"] = {
            "score": min(score, 100),
            "matched_terms": list(dict.fromkeys(matched_terms)),
            "reasons": reasons,
            "suggested_use": "可作为资讯推荐候选，并可被简报 agent 作为事实材料引用。",
        }
        return item

    @classmethod
    def _matched_terms(cls, item: Dict[str, Any], terms: List[str]) -> List[str]:
        text = cls._item_search_text(item)
        return [term for term in terms if term.lower() in text]

    @staticmethod
    def _item_search_text(item: Dict[str, Any]) -> str:
        parts = [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("content_excerpt", ""),
            item.get("source_name", ""),
        ]
        for entity in item.get("entities") or []:
            parts.extend([entity.get("name", ""), entity.get("type", ""), entity.get("summary", "")])
        for event in item.get("events") or []:
            parts.extend([event.get("event_type", ""), event.get("summary", ""), event.get("evidence", "")])
        for relation in item.get("relations") or []:
            parts.extend([relation.get("subject", ""), relation.get("predicate", ""), relation.get("object", ""), relation.get("evidence", "")])
        return " ".join(str(part) for part in parts).lower()

    @staticmethod
    def _recommendation_llm_context(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "当前条件下没有召回推荐候选资讯。"
        titles = "；".join(item.get("title", "") for item in items[:5] if item.get("title"))
        return f"已召回 {len(items)} 条推荐候选资讯。推荐时优先考虑分数高、带原文链接、包含事件或关系线索的资讯。候选标题包括：{titles}。"

    @staticmethod
    def _subscription_feed_summary(subscription_profile: Dict[str, List[str]], items: List[Dict[str, Any]]) -> str:
        interests = []
        for key in ("industries", "enterprises", "products", "preference_tags"):
            interests.extend(subscription_profile.get(key) or [])
        interest_text = "、".join(interests) if interests else "未指定关注项"
        if not items:
            return f"针对 {interest_text} 暂未召回资讯。"
        titles = "；".join(item.get("title", "") for item in items[:5] if item.get("title"))
        return f"针对 {interest_text} 生成资讯流，共召回 {len(items)} 条资讯。代表性资讯包括：{titles}。"

    @staticmethod
    def _entity_timeline_query() -> str:
        return """
        MATCH (ep)
        WHERE ep:Episodic OR ep.type_name = 'Episodic'
        WITH ep, coalesce(ep.publish_time, ep.valid_at, ep.created_at, ep.ingested_at) AS news_time
        WHERE ($start_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) >= datetime($start_time))
          AND (
            ($canonical_graph_id IS NULL AND $entity_name IS NULL)
            OR EXISTS {
              MATCH (ep)-[mention_rel]-(entity)
              WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
              OPTIONAL MATCH (entity)-[link_rel:refersTo|candidateRefersTo]->(anchor:CommonSenseAnchor)
              WITH entity, anchor, link_rel
              WHERE
                ($canonical_graph_id IS NOT NULL AND (
                  anchor.anchor_id = $canonical_graph_id
                  OR anchor.canonicalGraphId = $canonical_graph_id
                  OR entity.canonicalGraphId = $canonical_graph_id
                ))
                OR ($entity_name IS NOT NULL AND toLower(
                  coalesce(entity.name, '') + ' ' +
                  coalesce(entity.title, '') + ' ' +
                  coalesce(entity.summary, '') + ' ' +
                  coalesce(anchor.name, '') + ' ' +
                  reduce(alias_text = '', alias IN coalesce(anchor.aliases, []) | alias_text + ' ' + toString(alias))
                ) CONTAINS toLower($entity_name))
              RETURN entity LIMIT 1
            }
          )
        OPTIONAL MATCH (ep)-[mention_rel]-(entity)
        WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
        OPTIONAL MATCH (entity)-[link_rel:refersTo|candidateRefersTo]->(anchor:CommonSenseAnchor)
        WITH ep, news_time, collect(DISTINCT {
          id: coalesce(entity.id, entity.graph_id, entity.uuid),
          name: coalesce(entity.name, entity.title),
          type: coalesce(entity.type_name, entity.sourceType),
          canonicalGraphId: coalesce(anchor.anchor_id, anchor.canonicalGraphId, entity.canonicalGraphId),
          matchMethod: coalesce(link_rel.matchMethod, entity.matchMethod),
          matchScore: coalesce(link_rel.matchScore, entity.matchScore),
          summary: coalesce(entity.summary, entity.description),
          anchorName: anchor.name,
          anchorType: anchor.type_name,
          linkDecision: type(link_rel)
        }) AS entities
        RETURN
          properties(ep) AS news,
          labels(ep) AS labels,
          news_time AS publish_time,
          entities AS entities,
          [] AS events,
          [] AS relations
        ORDER BY news_time DESC
        LIMIT $limit
        """

    @staticmethod
    def _enterprise_supply_chain_query() -> str:
        return """
        MATCH (anchor:CommonSenseAnchor)
        WHERE (
            ($canonical_graph_id IS NOT NULL AND (
              anchor.anchor_id = $canonical_graph_id
              OR anchor.id = $canonical_graph_id
              OR anchor.canonicalGraphId = $canonical_graph_id
            ))
            OR ($entity_name IS NOT NULL AND toLower(
              coalesce(anchor.name, '') + ' ' +
              coalesce(anchor.title, '') + ' ' +
              coalesce(anchor.summary, '') + ' ' +
              coalesce(anchor.description, '')
            ) CONTAINS toLower($entity_name))
          )
        WITH anchor
        ORDER BY CASE
          WHEN $canonical_graph_id IS NOT NULL AND (anchor.anchor_id = $canonical_graph_id OR anchor.canonicalGraphId = $canonical_graph_id) THEN 0
          WHEN $entity_name IS NOT NULL AND toLower(coalesce(anchor.name, anchor.title, '')) = toLower($entity_name) THEN 1
          ELSE 2
        END
        LIMIT 1
        OPTIONAL MATCH (linked)-[:refersTo|candidateRefersTo]->(anchor)
        WITH anchor, [anchor] + collect(DISTINCT linked) AS anchor_nodes
        CALL {
          WITH anchor_nodes
          UNWIND anchor_nodes AS enterprise_node
          MATCH (enterprise_node)-[rel]-(neighbor)
          WHERE neighbor IS NOT NULL
            AND NOT (neighbor:Episodic OR neighbor.type_name = 'Episodic')
            AND NOT type(rel) IN ['mentions', 'MENTIONS', 'refersTo', 'candidateRefersTo']
          WITH enterprise_node, rel, neighbor,
               CASE WHEN startNode(rel) = enterprise_node THEN 'outgoing' ELSE 'incoming' END AS direction
          RETURN collect(DISTINCT {
            relation: type(rel),
            direction: direction,
            node: properties(neighbor),
            labels: labels(neighbor),
            evidence: coalesce(rel.evidence, rel.evidence_text, rel.description, ''),
            publish_time: coalesce(rel.publish_time, rel.valid_at, rel.created_at)
          }) AS related_entities
        }
        CALL {
          WITH anchor_nodes
          UNWIND anchor_nodes AS enterprise_node
          MATCH (enterprise_node)-[]-(ep)
          WHERE ep:Episodic OR ep.type_name = 'Episodic'
          WITH DISTINCT ep, coalesce(ep.publish_time, ep.valid_at, ep.created_at, ep.ingested_at) AS news_time
          WHERE ($start_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) >= datetime($start_time))
          RETURN collect({
            news: properties(ep),
            labels: labels(ep),
            publish_time: news_time,
            entities: [],
            events: [],
            relations: []
          }) AS news_items
        }
        RETURN
          properties(anchor) AS enterprise,
          labels(anchor) AS enterprise_labels,
          related_entities[0..$limit] AS related_entities,
          news_items[0..$limit] AS news_items
        """

    @staticmethod
    def _news_by_source_industry_query() -> str:
        return """
        MATCH (ep)
        WHERE ep:Episodic OR ep.type_name = 'Episodic'
        WITH ep, coalesce(ep.publish_time, ep.valid_at, ep.created_at, ep.ingested_at) AS news_time,
             toLower(
               coalesce(ep.source_name, '') + ' ' +
               coalesce(ep.source, '') + ' ' +
               coalesce(ep.sourceSystem, '') + ' ' +
               coalesce(ep.data_source, '') + ' ' +
               reduce(profile_text = '', profile IN coalesce(ep.sourceProfiles, []) | profile_text + ' ' + toString(profile))
             ) AS source_text
        WHERE ($start_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) >= datetime($start_time))
          AND ($end_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) <= datetime($end_time))
          AND ($source_name IS NULL OR source_text CONTAINS toLower($source_name))
          AND (
            $industry IS NULL
            OR toLower(
              coalesce(ep.title, '') + ' ' +
              coalesce(ep.name, '') + ' ' +
              coalesce(ep.summary, '') + ' ' +
              coalesce(ep.description, '') + ' ' +
              coalesce(ep.content, '') + ' ' +
              reduce(fact_text = '', fact IN coalesce(ep.factPayload, []) | fact_text + ' ' + toString(fact))
            ) CONTAINS toLower($industry)
            OR EXISTS {
              MATCH (ep)-[]-(entity)
              WHERE toLower(
                coalesce(entity.name, '') + ' ' +
                coalesce(entity.title, '') + ' ' +
                coalesce(entity.summary, '') + ' ' +
                coalesce(entity.description, '')
              ) CONTAINS toLower($industry)
            }
          )
        OPTIONAL MATCH (ep)-[mention_rel]-(entity)
        WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
        OPTIONAL MATCH (entity)-[link_rel:refersTo|candidateRefersTo]->(anchor:CommonSenseAnchor)
        WITH ep, news_time, collect(DISTINCT {
          id: coalesce(entity.id, entity.graph_id, entity.uuid),
          name: coalesce(entity.name, entity.title),
          type: coalesce(entity.type_name, entity.sourceType),
          canonicalGraphId: coalesce(anchor.anchor_id, anchor.canonicalGraphId, entity.canonicalGraphId),
          matchMethod: coalesce(link_rel.matchMethod, entity.matchMethod),
          matchScore: coalesce(link_rel.matchScore, entity.matchScore),
          summary: coalesce(entity.summary, entity.description),
          sourceProfiles: entity.sourceProfiles,
          anchorName: anchor.name,
          anchorType: anchor.type_name,
          linkDecision: type(link_rel)
        }) AS entities
        OPTIONAL MATCH (ep)-[event_rel]-(event)
        WHERE event_rel IS NOT NULL AND (
          event.type_name ENDS WITH 'Event'
          OR any(label IN labels(event) WHERE label ENDS WITH 'Event')
        )
        WITH ep, news_time, entities, collect(DISTINCT {
          event_type: coalesce(event.type_name, event.name),
          event_time: coalesce(event.event_time, event.eventTime, event.publishTime),
          summary: coalesce(event.summary, event.description, event.name),
          evidence: coalesce(event.evidence, event.evidence_text)
        }) AS events
        OPTIONAL MATCH (ep)-[rel]-(neighbor)
        WHERE rel IS NOT NULL AND NOT type(rel) IN ['mentions', 'MENTIONS']
        RETURN
          properties(ep) AS news,
          labels(ep) AS labels,
          news_time AS publish_time,
          entities AS entities,
          events AS events,
          collect(DISTINCT {
            subject: coalesce(ep.title, ep.name),
            predicate: type(rel),
            object: coalesce(neighbor.name, neighbor.title),
            evidence: coalesce(rel.evidence, rel.evidence_text)
          }) AS relations
        ORDER BY news_time DESC
        LIMIT $limit
        """

    @staticmethod
    def _candidate_news_query() -> str:
        return """
        MATCH (ep)
        WHERE ep:Episodic OR ep.type_name = 'Episodic'
        WITH ep, coalesce(ep.publish_time, ep.valid_at, ep.created_at, ep.ingested_at) AS news_time,
             toLower(
               coalesce(ep.title, '') + ' ' +
               coalesce(ep.name, '') + ' ' +
               coalesce(ep.summary, '') + ' ' +
               coalesce(ep.description, '') + ' ' +
               coalesce(ep.content, '') + ' ' +
               reduce(fact_text = '', fact IN coalesce(ep.factPayload, []) | fact_text + ' ' + toString(fact)) + ' ' +
               reduce(profile_text = '', profile IN coalesce(ep.sourceProfiles, []) | profile_text + ' ' + toString(profile))
             ) AS news_text
        WHERE ($start_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) >= datetime($start_time))
          AND ($end_time IS NULL OR news_time IS NULL OR datetime(toString(news_time)) <= datetime($end_time))
        OPTIONAL MATCH (ep)-[mention_rel]-(entity)
        WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
        OPTIONAL MATCH (entity)-[link_rel:refersTo|candidateRefersTo]->(anchor:CommonSenseAnchor)
        WITH ep, news_time, news_text, collect(DISTINCT {entity: entity, anchor: anchor}) AS raw_entities
        WITH ep, news_time, news_text, raw_entities,
             reduce(entity_text = '', entity IN raw_entities |
               entity_text + ' ' + toLower(
                 coalesce(entity.entity.name, '') + ' ' +
                 coalesce(entity.entity.title, '') + ' ' +
                 coalesce(entity.entity.summary, '') + ' ' +
                 coalesce(entity.entity.description, '') + ' ' +
                 coalesce(entity.anchor.name, '') + ' ' +
                 coalesce(entity.anchor.description, '') + ' ' +
                 reduce(alias_text = '', alias IN coalesce(entity.anchor.aliases, []) | alias_text + ' ' + toString(alias))
               )
             ) AS entity_text
        WHERE (
            size($industries) + size($entity_names) + size($product_names) + size($preference_tags) = 0
            OR any(term IN $industries WHERE news_text CONTAINS toLower(term) OR entity_text CONTAINS toLower(term))
            OR any(term IN $entity_names WHERE news_text CONTAINS toLower(term) OR entity_text CONTAINS toLower(term))
            OR any(term IN $product_names WHERE news_text CONTAINS toLower(term) OR entity_text CONTAINS toLower(term))
            OR any(term IN $preference_tags WHERE news_text CONTAINS toLower(term) OR entity_text CONTAINS toLower(term))
          )
        WITH ep, news_time
        ORDER BY news_time DESC
        LIMIT $limit
        OPTIONAL MATCH (ep)-[mention_rel]-(entity)
        WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
        OPTIONAL MATCH (entity)-[link_rel:refersTo|candidateRefersTo]->(anchor:CommonSenseAnchor)
        WITH ep, news_time, collect(DISTINCT {entity: entity, anchor: anchor, link: link_rel}) AS raw_entities
        WITH ep, news_time, [row IN raw_entities | {
          id: coalesce(row.entity.id, row.entity.graph_id, row.entity.uuid),
          name: coalesce(row.entity.name, row.entity.title),
          type: coalesce(row.entity.type_name, row.entity.sourceType),
          canonicalGraphId: coalesce(row.anchor.anchor_id, row.anchor.canonicalGraphId, row.entity.canonicalGraphId),
          matchMethod: coalesce(row.link.matchMethod, row.entity.matchMethod),
          matchScore: coalesce(row.link.matchScore, row.entity.matchScore),
          summary: coalesce(row.entity.summary, row.entity.description),
          sourceProfiles: row.entity.sourceProfiles,
          anchorName: row.anchor.name,
          anchorType: row.anchor.type_name,
          linkDecision: type(row.link)
        }] AS entities
        OPTIONAL MATCH (ep)-[event_rel]-(event)
        WHERE event_rel IS NOT NULL AND (
          event.type_name ENDS WITH 'Event'
          OR any(label IN labels(event) WHERE label ENDS WITH 'Event')
        )
        WITH ep, news_time, entities, collect(DISTINCT {
          event_type: coalesce(event.type_name, event.name),
          event_time: coalesce(event.event_time, event.eventTime, event.publishTime),
          summary: coalesce(event.summary, event.description, event.name),
          evidence: coalesce(event.evidence, event.evidence_text)
        }) AS events
        OPTIONAL MATCH (ep)-[rel]-(neighbor)
        WHERE rel IS NOT NULL AND NOT type(rel) IN ['mentions', 'MENTIONS']
        RETURN
          properties(ep) AS news,
          labels(ep) AS labels,
          news_time AS publish_time,
          entities AS entities,
          events AS events,
          collect(DISTINCT {
            subject: coalesce(ep.title, ep.name),
            predicate: type(rel),
            object: coalesce(neighbor.name, neighbor.title),
            evidence: coalesce(rel.evidence, rel.evidence_text)
          }) AS relations
        ORDER BY news_time DESC
        """
