import asyncio
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from .graphiti_service import graphiti_service


STORYLINE_REBUILD_LOCK = asyncio.Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(
    name: str,
    default: float,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    raw = os.getenv(name)
    if raw is None:
        value = default
    else:
        try:
            value = float(raw)
        except ValueError:
            logging.warning("Invalid %s=%s; fallback to %.4f", name, raw, default)
            value = default

    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    return value


def _env_int(
    name: str,
    default: int,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw = os.getenv(name)
    if raw is None:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError:
            logging.warning("Invalid %s=%s; fallback to %s", name, raw, default)
            value = default

    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    return value


THREAD_DEFAULT_WINDOW_DAYS = _env_int("THREAD_WINDOW_DAYS", 30, 1, 365)
THREAD_MIN_EPISODE_COUNT = _env_int("THREAD_MIN_EPISODE_COUNT", 1, 1, 500)
THREAD_MIN_HOTNESS = _env_float("THREAD_MIN_HOTNESS", 0.0, 0.0, 1000000.0)
THREAD_MAX_COMPANY_MEMBERSHIP_PER_EPISODE = _env_int(
    "THREAD_MAX_COMPANY_MEMBERSHIP_PER_EPISODE",
    1,
    0,
    10,
)
THREAD_MAX_PRODUCT_MEMBERSHIP_PER_EPISODE = _env_int(
    "THREAD_MAX_PRODUCT_MEMBERSHIP_PER_EPISODE",
    1,
    0,
    10,
)

THREAD_EXCLUDE_MIN_CONTENT_CHARS = _env_int(
    "THREAD_EXCLUDE_MIN_CONTENT_CHARS",
    12,
    0,
    1000,
)
THREAD_EXCLUDE_MAX_HOTNESS = _env_float(
    "THREAD_EXCLUDE_MAX_HOTNESS",
    0.2,
    0.0,
    1000.0,
)
THREAD_DEFAULT_SOURCE_QUALITY = _env_float(
    "THREAD_DEFAULT_SOURCE_QUALITY",
    1.0,
    0.2,
    2.0,
)

COMPANY_LABELS = {"Company", "Enterprise"}
PRODUCT_LABELS = {"ProductObject", "Product", "ProductModel"}


def _is_company_entity(labels: set[str]) -> bool:
    return bool(labels.intersection(COMPANY_LABELS))


def _is_product_entity(labels: set[str]) -> bool:
    return bool(labels.intersection(PRODUCT_LABELS))


def _parse_source_quality_overrides() -> dict[str, float]:
    raw = os.getenv("THREAD_SOURCE_QUALITY_MAP", "").strip()
    if not raw:
        return {}

    result: dict[str, float] = {}
    for item in raw.split(","):
        pair = item.strip()
        if not pair or "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        source_name = key.strip().lower()
        if not source_name:
            continue
        try:
            result[source_name] = max(0.2, min(float(value.strip()), 2.0))
        except ValueError:
            logging.warning("Invalid source quality override: %s", pair)
    return result


_SOURCE_QUALITY_OVERRIDES = _parse_source_quality_overrides()


def _source_quality(source: str) -> float:
    key = (source or "").strip().lower()
    if not key:
        return THREAD_DEFAULT_SOURCE_QUALITY
    return _SOURCE_QUALITY_OVERRIDES.get(key, THREAD_DEFAULT_SOURCE_QUALITY)


def _to_aware_utc(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if hasattr(value, "to_native"):
        value = value.to_native()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _build_thread_uuid(thread_type: str, anchor_entity_uuid: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"storythread:{thread_type}:{anchor_entity_uuid}"))


def _build_thread_title(
    thread_type: str,
    anchor_entity_name: str,
    top_entities: list[str],
) -> str:
    anchor = (anchor_entity_name or "").strip() or "未知主体"
    if thread_type == "company":
        if "公司" not in anchor:
            return f"{anchor}公司脉络"
        return f"{anchor}脉络"
    if thread_type == "product":
        return f"{anchor}产品脉络"

    entity_part = " / ".join(top_entities[:2]) if top_entities else anchor
    return f"{entity_part}脉络"


def _build_thread_summary(episodes: list["EpisodeFeature"]) -> str:
    if not episodes:
        return "无摘要"
    latest = episodes[-1]
    base = latest.title or latest.content or "无摘要"
    summary = _normalize_text(base)
    return summary[:220] if len(summary) > 220 else summary


def _should_exclude_episode(feature: "EpisodeFeature") -> bool:
    content_len = len((feature.content or "").strip())
    if (
        not feature.title
        and content_len < THREAD_EXCLUDE_MIN_CONTENT_CHARS
        and feature.hotness <= THREAD_EXCLUDE_MAX_HOTNESS
        and len(feature.entity_ids) == 0
    ):
        return True
    return False


@dataclass
class AnchorMention:
    entity_uuid: str
    entity_name: str
    score: float


@dataclass
class EpisodeFeature:
    uuid: str
    title: str
    content: str
    source: str
    publish_at: datetime
    hotness: float
    source_quality: float
    entity_ids: set[str]
    entity_names: dict[str, str]
    entity_weights: dict[str, float]
    company_mentions: list[AnchorMention]
    product_mentions: list[AnchorMention]


@dataclass
class EpisodeMembership:
    episode: EpisodeFeature
    membership_score: float
    is_primary: bool
    joined_reason: str


def _rank_mentions(
    mention_scores: dict[str, float],
    entity_names: dict[str, str],
) -> list[AnchorMention]:
    ranked: list[AnchorMention] = []
    for entity_uuid, score in mention_scores.items():
        ranked.append(
            AnchorMention(
                entity_uuid=entity_uuid,
                entity_name=entity_names.get(entity_uuid, entity_uuid),
                score=float(score),
            )
        )
    ranked.sort(key=lambda item: (item.score, item.entity_name), reverse=True)
    return ranked


class StorylineService:
    async def _load_episode_features(self, since_days: int) -> list[EpisodeFeature]:
        driver = graphiti_service.graphiti.driver
        since_time = datetime.now(timezone.utc) - timedelta(days=since_days)

        episode_query = """
        MATCH (ep:Episodic)
        WHERE coalesce(ep.publish_time, ep.valid_at, ep.created_at) >= $since_time
        RETURN
            ep.uuid AS uuid,
            coalesce(ep.title, ep.name, '') AS title,
            coalesce(ep.content, '') AS content,
            coalesce(ep.news_source, '') AS source,
            coalesce(ep.publish_time, ep.valid_at, ep.created_at) AS publish_at,
            coalesce(ep.news_hotness_score, 0.0) AS hotness
        ORDER BY coalesce(ep.publish_time, ep.valid_at, ep.created_at) DESC
        """
        episode_records, _, _ = await driver.execute_query(episode_query, since_time=since_time)
        if not episode_records:
            return []

        episode_uuids = [record["uuid"] for record in episode_records if record["uuid"]]
        mention_query = """
        MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
        WHERE ep.uuid IN $episode_uuids
        RETURN
            ep.uuid AS episode_uuid,
            e.uuid AS entity_uuid,
            coalesce(e.name, '') AS entity_name,
            labels(e) AS labels,
            coalesce(e.momentum_score, 0.0) AS momentum_score,
            coalesce(e.pageRank, 0.0) AS page_rank
        """
        mention_records, _, _ = await driver.execute_query(
            mention_query,
            episode_uuids=episode_uuids,
        )

        mention_by_episode: dict[str, list[dict]] = {}
        for record in mention_records:
            episode_uuid = record["episode_uuid"]
            mention_by_episode.setdefault(episode_uuid, []).append(record)

        features: list[EpisodeFeature] = []
        for record in episode_records:
            episode_uuid = record["uuid"]
            mentions = mention_by_episode.get(episode_uuid, [])

            entity_ids: set[str] = set()
            entity_names: dict[str, str] = {}
            entity_weights: dict[str, float] = {}
            company_scores: dict[str, float] = {}
            product_scores: dict[str, float] = {}

            for mention in mentions:
                entity_uuid = mention["entity_uuid"]
                if not entity_uuid:
                    continue

                labels = set(mention.get("labels") or [])
                entity_name = mention.get("entity_name") or entity_uuid
                momentum_score = float(mention.get("momentum_score") or 0.0)
                page_rank = float(mention.get("page_rank") or 0.0)
                weight = max(1.0 + (0.03 * momentum_score) + (8.0 * page_rank), 0.1)

                entity_ids.add(entity_uuid)
                entity_names[entity_uuid] = entity_name
                entity_weights[entity_uuid] = max(entity_weights.get(entity_uuid, 0.0), weight)

                if _is_company_entity(labels):
                    company_scores[entity_uuid] = max(company_scores.get(entity_uuid, 0.0), weight)
                if _is_product_entity(labels):
                    product_scores[entity_uuid] = max(product_scores.get(entity_uuid, 0.0), weight)

            title = (record["title"] or "").strip()
            content = (record["content"] or "").strip()
            source = (record["source"] or "").strip()
            feature = EpisodeFeature(
                uuid=episode_uuid,
                title=title,
                content=content,
                source=source,
                publish_at=_to_aware_utc(record["publish_at"]),
                hotness=float(record["hotness"] or 0.0),
                source_quality=_source_quality(source),
                entity_ids=entity_ids,
                entity_names=entity_names,
                entity_weights=entity_weights,
                company_mentions=_rank_mentions(company_scores, entity_names),
                product_mentions=_rank_mentions(product_scores, entity_names),
            )

            if _should_exclude_episode(feature):
                continue
            features.append(feature)

        return features

    @staticmethod
    def _compute_membership_score(feature: EpisodeFeature, mention_score: float) -> float:
        base = max(mention_score, 0.1) * max(feature.source_quality, 0.2)
        hotness_boost = 1.0 + min(max(feature.hotness, 0.0), 30.0) * 0.01
        return float(base * hotness_boost)

    @staticmethod
    def _compute_thread_hotness(memberships: list[EpisodeMembership]) -> float:
        if not memberships:
            return 0.0
        ordered = sorted(memberships, key=lambda item: item.episode.publish_at)
        hotness = 0.0
        total = len(ordered)
        for rank, membership in enumerate(ordered, start=1):
            recency_factor = max(1.0, total - rank + 1)
            contribution = (
                ((membership.episode.hotness * membership.episode.source_quality) + 1.0)
                * recency_factor
                * max(0.5, min(membership.membership_score, 3.0))
            )
            hotness += contribution
        return float(hotness)

    def _build_thread_payloads(self, features: list[EpisodeFeature]) -> tuple[list[dict], int]:
        buckets: dict[tuple[str, str], dict] = {}
        linked_episode_count = 0

        for feature in features:
            company_candidates = feature.company_mentions[:THREAD_MAX_COMPANY_MEMBERSHIP_PER_EPISODE]
            product_candidates = feature.product_mentions[:THREAD_MAX_PRODUCT_MEMBERSHIP_PER_EPISODE]

            if company_candidates:
                linked_episode_count += 1
            if product_candidates:
                linked_episode_count += 1

            for index, mention in enumerate(company_candidates):
                key = ("company", mention.entity_uuid)
                bucket = buckets.setdefault(
                    key,
                    {
                        "thread_type": "company",
                        "anchor_entity_uuid": mention.entity_uuid,
                        "anchor_entity_name": mention.entity_name,
                        "memberships": [],
                    },
                )
                bucket["memberships"].append(
                    EpisodeMembership(
                        episode=feature,
                        membership_score=self._compute_membership_score(feature, mention.score),
                        is_primary=index == 0,
                        joined_reason="anchor_mentioned",
                    )
                )

            for index, mention in enumerate(product_candidates):
                key = ("product", mention.entity_uuid)
                bucket = buckets.setdefault(
                    key,
                    {
                        "thread_type": "product",
                        "anchor_entity_uuid": mention.entity_uuid,
                        "anchor_entity_name": mention.entity_name,
                        "memberships": [],
                    },
                )
                bucket["memberships"].append(
                    EpisodeMembership(
                        episode=feature,
                        membership_score=self._compute_membership_score(feature, mention.score),
                        is_primary=index == 0,
                        joined_reason="anchor_mentioned",
                    )
                )

        thread_payloads: list[dict] = []
        for bucket in buckets.values():
            memberships = bucket["memberships"]
            if len(memberships) < THREAD_MIN_EPISODE_COUNT:
                continue

            memberships.sort(key=lambda item: item.episode.publish_at)
            thread_hotness = self._compute_thread_hotness(memberships)
            if thread_hotness < THREAD_MIN_HOTNESS:
                continue

            episodes = [membership.episode for membership in memberships]
            entity_counter = Counter()
            entity_name_map: dict[str, str] = {}
            for membership in memberships:
                episode = membership.episode
                for entity_id in episode.entity_ids:
                    entity_counter[entity_id] += episode.entity_weights.get(entity_id, 1.0)
                    entity_name_map[entity_id] = episode.entity_names.get(entity_id, entity_id)

            top_entities = [entity_name_map[entity_id] for entity_id, _ in entity_counter.most_common(5)]
            thread_type = bucket["thread_type"]
            anchor_entity_uuid = bucket["anchor_entity_uuid"]
            anchor_entity_name = bucket["anchor_entity_name"]
            thread_title = _build_thread_title(thread_type, anchor_entity_name, top_entities)
            summary = _build_thread_summary(episodes)

            episode_links: list[dict] = []
            total = len(memberships)
            for rank, membership in enumerate(memberships, start=1):
                normalized_rank_score = (total - rank + 1) / max(total, 1)
                membership_score = float(membership.membership_score)
                episode_links.append(
                    {
                        "episode_uuid": membership.episode.uuid,
                        "rank": rank,
                        "score": round(normalized_rank_score, 4),
                        "membership_type": thread_type,
                        "membership_score": round(membership_score, 4),
                        "is_primary": bool(membership.is_primary),
                        "joined_reason": membership.joined_reason,
                        # Keep compatibility with the previous explain schema.
                        "similarity_score": round(membership_score, 4),
                        "similarity_entity": round(membership_score, 4),
                        "similarity_semantic": 0.0,
                        "similarity_time": 0.0,
                        "similarity_event": 0.0,
                    }
                )

            key_entities: list[dict] = []
            for rank, (entity_id, weight) in enumerate(entity_counter.most_common(8), start=1):
                key_entities.append(
                    {
                        "entity_uuid": entity_id,
                        "entity_name": entity_name_map.get(entity_id, entity_id),
                        "weight": float(weight),
                        "rank": rank,
                    }
                )

            first_seen_at = episodes[0].publish_at
            last_seen_at = episodes[-1].publish_at
            thread_payloads.append(
                {
                    "storyline_uuid": _build_thread_uuid(thread_type, anchor_entity_uuid),
                    "thread_type": thread_type,
                    "anchor_entity_uuid": anchor_entity_uuid,
                    "anchor_entity_name": anchor_entity_name,
                    "title": thread_title,
                    "summary": summary,
                    "first_seen_at": first_seen_at,
                    "last_seen_at": last_seen_at,
                    "episode_count": len(memberships),
                    "thread_hotness": float(thread_hotness),
                    "updated_at": datetime.now(timezone.utc),
                    "episode_links": episode_links,
                    "key_entities": key_entities,
                }
            )

        return thread_payloads, linked_episode_count

    async def rebuild_storylines(self, since_days: int = THREAD_DEFAULT_WINDOW_DAYS) -> dict:
        if STORYLINE_REBUILD_LOCK.locked():
            logging.warning("Storyline rebuild is already running. Waiting for lock.")

        async with STORYLINE_REBUILD_LOCK:
            features = await self._load_episode_features(since_days=since_days)
            if not features:
                await self._clear_storylines()
                return {
                    "status": "success",
                    "message": "No episodic data found in window; storyline data cleared.",
                    "since_days": since_days,
                    "thread_count": 0,
                    "episode_count": 0,
                    "linked_episode_count": 0,
                }

            thread_payloads, linked_episode_count = self._build_thread_payloads(features)
            await self._replace_storylines(thread_payloads)

            return {
                "status": "success",
                "message": "Storyline rebuild completed.",
                "since_days": since_days,
                "thread_count": len(thread_payloads),
                "episode_count": len(features),
                "linked_episode_count": linked_episode_count,
            }

    async def _clear_storylines(self) -> None:
        driver = graphiti_service.graphiti.driver
        await driver.execute_query("MATCH (t:StoryThread) DETACH DELETE t")

    async def _replace_storylines(self, thread_payloads: list[dict]) -> None:
        driver = graphiti_service.graphiti.driver
        await self._clear_storylines()

        if not thread_payloads:
            return

        create_thread_query = """
        UNWIND $threads AS thread
        CREATE (t:StoryThread {
            uuid: thread.storyline_uuid,
            thread_type: thread.thread_type,
            anchor_entity_uuid: thread.anchor_entity_uuid,
            anchor_entity_name: thread.anchor_entity_name,
            title: thread.title,
            summary: thread.summary,
            first_seen_at: thread.first_seen_at,
            last_seen_at: thread.last_seen_at,
            episode_count: thread.episode_count,
            thread_hotness: thread.thread_hotness,
            updated_at: thread.updated_at
        })
        """
        await driver.execute_query(create_thread_query, threads=thread_payloads)

        link_episode_query = """
        UNWIND $threads AS thread
        MATCH (t:StoryThread {uuid: thread.storyline_uuid})
        UNWIND thread.episode_links AS link
        MATCH (ep:Episodic {uuid: link.episode_uuid})
        CREATE (ep)-[:IN_THREAD {
            score: link.score,
            rank: link.rank,
            membership_type: link.membership_type,
            membership_score: link.membership_score,
            is_primary: link.is_primary,
            joined_reason: link.joined_reason,
            similarity_score: link.similarity_score,
            similarity_entity: link.similarity_entity,
            similarity_semantic: link.similarity_semantic,
            similarity_time: link.similarity_time,
            similarity_event: link.similarity_event
        }]->(t)
        """
        await driver.execute_query(link_episode_query, threads=thread_payloads)

        link_entity_query = """
        UNWIND $threads AS thread
        MATCH (t:StoryThread {uuid: thread.storyline_uuid})
        UNWIND thread.key_entities AS key_entity
        MATCH (e:Entity {uuid: key_entity.entity_uuid})
        CREATE (t)-[:KEY_ENTITY {
            weight: key_entity.weight,
            rank: key_entity.rank
        }]->(e)
        """
        await driver.execute_query(link_entity_query, threads=thread_payloads)

    async def list_storylines(
        self,
        limit: int = 20,
        min_episode_count: int = 2,
        thread_type: str | None = None,
    ) -> list[dict]:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (t:StoryThread)
        WHERE t.episode_count >= $min_episode_count
          AND ($thread_type IS NULL OR t.thread_type = $thread_type)
        OPTIONAL MATCH (t)-[ke:KEY_ENTITY]->(e:Entity)
        WITH t, e, ke ORDER BY ke.rank ASC
        WITH t, collect({
            uuid: e.uuid,
            name: e.name,
            weight: ke.weight,
            rank: ke.rank
        }) AS key_entities
        RETURN
            t.uuid AS uuid,
            t.thread_type AS thread_type,
            t.anchor_entity_uuid AS anchor_entity_uuid,
            t.anchor_entity_name AS anchor_entity_name,
            t.title AS title,
            t.summary AS summary,
            t.first_seen_at AS first_seen_at,
            t.last_seen_at AS last_seen_at,
            t.episode_count AS episode_count,
            t.thread_hotness AS thread_hotness,
            t.updated_at AS updated_at,
            key_entities
        ORDER BY t.thread_hotness DESC, t.last_seen_at DESC
        LIMIT $limit
        """
        records, _, _ = await driver.execute_query(
            query,
            limit=limit,
            min_episode_count=min_episode_count,
            thread_type=thread_type,
        )

        storylines: list[dict] = []
        for record in records:
            storylines.append(
                {
                    "uuid": record["uuid"],
                    "thread_type": record["thread_type"],
                    "anchor_entity_uuid": record["anchor_entity_uuid"],
                    "anchor_entity_name": record["anchor_entity_name"],
                    "title": record["title"],
                    "summary": record["summary"],
                    "first_seen_at": record["first_seen_at"],
                    "last_seen_at": record["last_seen_at"],
                    "episode_count": record["episode_count"],
                    "thread_hotness": record["thread_hotness"],
                    "updated_at": record["updated_at"],
                    "key_entities": [item for item in (record["key_entities"] or []) if item.get("uuid")],
                }
            )
        return storylines

    async def list_storylines_by_anchor(
        self,
        anchor_entity_uuid: str,
        limit: int = 20,
        min_episode_count: int = 1,
        thread_type: str | None = None,
    ) -> list[dict]:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (t:StoryThread)
        WHERE t.anchor_entity_uuid = $anchor_entity_uuid
          AND t.episode_count >= $min_episode_count
          AND ($thread_type IS NULL OR t.thread_type = $thread_type)
        OPTIONAL MATCH (t)-[ke:KEY_ENTITY]->(e:Entity)
        WITH t, e, ke ORDER BY ke.rank ASC
        WITH t, collect({
            uuid: e.uuid,
            name: e.name,
            weight: ke.weight,
            rank: ke.rank
        }) AS key_entities
        RETURN
            t.uuid AS uuid,
            t.thread_type AS thread_type,
            t.anchor_entity_uuid AS anchor_entity_uuid,
            t.anchor_entity_name AS anchor_entity_name,
            t.title AS title,
            t.summary AS summary,
            t.first_seen_at AS first_seen_at,
            t.last_seen_at AS last_seen_at,
            t.episode_count AS episode_count,
            t.thread_hotness AS thread_hotness,
            t.updated_at AS updated_at,
            key_entities
        ORDER BY t.thread_hotness DESC, t.last_seen_at DESC
        LIMIT $limit
        """
        records, _, _ = await driver.execute_query(
            query,
            anchor_entity_uuid=anchor_entity_uuid,
            limit=limit,
            min_episode_count=min_episode_count,
            thread_type=thread_type,
        )

        storylines: list[dict] = []
        for record in records:
            storylines.append(
                {
                    "uuid": record["uuid"],
                    "thread_type": record["thread_type"],
                    "anchor_entity_uuid": record["anchor_entity_uuid"],
                    "anchor_entity_name": record["anchor_entity_name"],
                    "title": record["title"],
                    "summary": record["summary"],
                    "first_seen_at": record["first_seen_at"],
                    "last_seen_at": record["last_seen_at"],
                    "episode_count": record["episode_count"],
                    "thread_hotness": record["thread_hotness"],
                    "updated_at": record["updated_at"],
                    "key_entities": [item for item in (record["key_entities"] or []) if item.get("uuid")],
                }
            )
        return storylines

    async def _get_storyline_detail(
        self,
        episode_uuid: str,
        storyline_uuid: str,
        limit: int = 30,
        debug: bool = False,
    ) -> dict | None:
        driver = graphiti_service.graphiti.driver
        thread_query = """
        MATCH (ep:Episodic {uuid: $episode_uuid})-[in_thread:IN_THREAD]->(t:StoryThread {uuid: $storyline_uuid})
        OPTIONAL MATCH (t)-[ke:KEY_ENTITY]->(e:Entity)
        WITH ep, in_thread, t, e, ke ORDER BY ke.rank ASC
        WITH ep, in_thread, t, collect({
            uuid: e.uuid,
            name: e.name,
            weight: ke.weight,
            rank: ke.rank
        }) AS key_entities
        RETURN
            t.uuid AS storyline_uuid,
            t.thread_type AS thread_type,
            t.anchor_entity_uuid AS anchor_entity_uuid,
            t.anchor_entity_name AS anchor_entity_name,
            t.title AS title,
            t.summary AS summary,
            t.first_seen_at AS first_seen_at,
            t.last_seen_at AS last_seen_at,
            t.episode_count AS episode_count,
            t.thread_hotness AS thread_hotness,
            in_thread.rank AS current_episode_rank,
            coalesce(in_thread.membership_type, t.thread_type, '') AS current_membership_type,
            coalesce(in_thread.membership_score, in_thread.score, 0.0) AS current_membership_score,
            coalesce(in_thread.is_primary, false) AS current_is_primary,
            key_entities
        LIMIT 1
        """
        thread_records, _, _ = await driver.execute_query(
            thread_query,
            episode_uuid=episode_uuid,
            storyline_uuid=storyline_uuid,
        )
        if not thread_records:
            return None

        thread_record = thread_records[0]
        timeline_query = """
        MATCH (ep:Episodic)-[in_thread:IN_THREAD]->(t:StoryThread {uuid: $storyline_uuid})
        RETURN
            ep.uuid AS uuid,
            coalesce(ep.title, ep.name, '') AS title,
            coalesce(ep.content, '') AS content,
            coalesce(ep.publish_time, ep.valid_at, ep.created_at) AS publish_at,
            coalesce(ep.news_source, '') AS source,
            coalesce(ep.news_hotness_score, 0.0) AS news_hotness_score,
            in_thread.rank AS rank,
            coalesce(in_thread.score, 0.0) AS score,
            coalesce(in_thread.membership_type, t.thread_type, '') AS membership_type,
            coalesce(in_thread.membership_score, in_thread.score, 0.0) AS membership_score,
            coalesce(in_thread.is_primary, false) AS is_primary,
            coalesce(in_thread.similarity_score, in_thread.membership_score, in_thread.score, 0.0) AS similarity_score,
            coalesce(in_thread.similarity_entity, in_thread.membership_score, in_thread.score, 0.0) AS similarity_entity,
            coalesce(in_thread.similarity_semantic, 0.0) AS similarity_semantic,
            coalesce(in_thread.similarity_time, 0.0) AS similarity_time,
            coalesce(in_thread.similarity_event, 0.0) AS similarity_event,
            coalesce(in_thread.joined_reason, '') AS joined_reason
        ORDER BY in_thread.rank ASC, publish_at ASC
        LIMIT $limit
        """
        timeline_records, _, _ = await driver.execute_query(
            timeline_query,
            storyline_uuid=storyline_uuid,
            limit=limit,
        )

        timeline: list[dict] = []
        for record in timeline_records:
            item = {
                "uuid": record["uuid"],
                "title": record["title"],
                "content": record["content"],
                "publish_at": record["publish_at"],
                "source": record["source"],
                "news_hotness_score": record["news_hotness_score"],
                "rank": record["rank"],
                "membership_type": record["membership_type"],
                "membership_score": record["membership_score"],
                "is_primary": record["is_primary"],
            }
            if debug:
                item["explain"] = {
                    "score": record["score"],
                    "membership_score": record["membership_score"],
                    "similarity_score": record["similarity_score"],
                    "similarity_entity": record["similarity_entity"],
                    "similarity_semantic": record["similarity_semantic"],
                    "similarity_time": record["similarity_time"],
                    "similarity_event": record["similarity_event"],
                    "joined_reason": record["joined_reason"],
                }
            timeline.append(item)

        return {
            "storyline_uuid": thread_record["storyline_uuid"],
            "thread_type": thread_record["thread_type"],
            "anchor_entity_uuid": thread_record["anchor_entity_uuid"],
            "anchor_entity_name": thread_record["anchor_entity_name"],
            "title": thread_record["title"],
            "summary": thread_record["summary"],
            "first_seen_at": thread_record["first_seen_at"],
            "last_seen_at": thread_record["last_seen_at"],
            "episode_count": thread_record["episode_count"],
            "thread_hotness": thread_record["thread_hotness"],
            "current_episode_rank": thread_record["current_episode_rank"],
            "current_membership_type": thread_record["current_membership_type"],
            "current_membership_score": thread_record["current_membership_score"],
            "current_is_primary": thread_record["current_is_primary"],
            "key_entities": [item for item in (thread_record["key_entities"] or []) if item.get("uuid")],
            "timeline": timeline,
        }

    async def get_storylines_for_episode(
        self,
        episode_uuid: str,
        limit: int = 30,
        debug: bool = False,
        max_storylines: int = 10,
    ) -> list[dict]:
        driver = graphiti_service.graphiti.driver
        ref_query = """
        MATCH (ep:Episodic {uuid: $episode_uuid})-[in_thread:IN_THREAD]->(t:StoryThread)
        WITH t, in_thread,
             CASE t.thread_type WHEN 'company' THEN 2 WHEN 'product' THEN 1 ELSE 0 END AS type_priority,
             coalesce(in_thread.membership_score, in_thread.score, 0.0) AS membership_score
        RETURN
            t.uuid AS storyline_uuid
        ORDER BY
            type_priority DESC,
            coalesce(in_thread.is_primary, false) DESC,
            membership_score DESC,
            coalesce(t.thread_hotness, 0.0) DESC
        LIMIT $max_storylines
        """
        ref_records, _, _ = await driver.execute_query(
            ref_query,
            episode_uuid=episode_uuid,
            max_storylines=max_storylines,
        )
        if not ref_records:
            return []

        storylines: list[dict] = []
        for record in ref_records:
            storyline_uuid = record.get("storyline_uuid")
            if not storyline_uuid:
                continue
            detail = await self._get_storyline_detail(
                episode_uuid=episode_uuid,
                storyline_uuid=storyline_uuid,
                limit=limit,
                debug=debug,
            )
            if detail:
                storylines.append(detail)
        return storylines

    async def get_storyline_for_episode(
        self,
        episode_uuid: str,
        limit: int = 30,
        debug: bool = False,
    ) -> dict | None:
        storylines = await self.get_storylines_for_episode(
            episode_uuid=episode_uuid,
            limit=limit,
            debug=debug,
            max_storylines=1,
        )
        if not storylines:
            return None
        return storylines[0]


storyline_service = StorylineService()
