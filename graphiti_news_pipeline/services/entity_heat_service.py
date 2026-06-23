from __future__ import annotations

from datetime import datetime, time, timedelta
import json
import math
from typing import Any
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
FORMULA_VERSION = "entity_heat_v1"

ENTITY_HEAT_FORMULA = {
    "formula_version": FORMULA_VERSION,
    "mention_weight": 0.45,
    "news_hotness_weight": 0.20,
    "source_weight": 0.15,
    "freshness_weight": 0.10,
    "anchor_weight": 0.10,
}

ENTITY_TYPE_LABELS = {
    "Enterprise": ["Enterprise", "Company", "Organization"],
    "Product": ["Product", "ProductModel", "ProductTerm", "ProductObject"],
    "Person": ["Person"],
    "Technology": ["Technology"],
    "Region": ["Region"],
}


def _as_aware_datetime(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(SHANGHAI_TZ)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=SHANGHAI_TZ)
        return value.astimezone(SHANGHAI_TZ)
    if hasattr(value, "to_native"):
        return _as_aware_datetime(value.to_native())

    raw = str(value).strip()
    if not raw:
        return datetime.now(SHANGHAI_TZ)
    if len(raw) == 10:
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=SHANGHAI_TZ)
    normalized = raw.replace("Z", "+00:00")
    match = re_match_datetime_fraction(normalized)
    if match:
        head, fraction, tail = match
        normalized = f"{head}.{fraction[:6]}{tail}"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SHANGHAI_TZ)
    return parsed.astimezone(SHANGHAI_TZ)


def re_match_datetime_fraction(value: str) -> tuple[str, str, str] | None:
    if "." not in value:
        return None
    head, rest = value.split(".", 1)
    fraction = []
    index = 0
    for char in rest:
        if not char.isdigit():
            break
        fraction.append(char)
        index += 1
    if len(fraction) <= 6:
        return None
    return head, "".join(fraction), rest[index:]


def resolve_period_window(period_type: str, as_of: str | datetime | None = None) -> tuple[datetime, datetime]:
    as_of_dt = _as_aware_datetime(as_of)
    normalized_type = str(period_type or "daily").strip().lower()
    if normalized_type == "daily":
        start = datetime.combine(as_of_dt.date(), time.min, tzinfo=SHANGHAI_TZ)
        end = datetime.combine(as_of_dt.date(), time.max, tzinfo=SHANGHAI_TZ)
        return start, end
    if normalized_type == "weekly":
        start_date = as_of_dt.date() - timedelta(days=as_of_dt.weekday())
        end_date = start_date + timedelta(days=6)
        start = datetime.combine(start_date, time.min, tzinfo=SHANGHAI_TZ)
        end = datetime.combine(end_date, time.max, tzinfo=SHANGHAI_TZ)
        return start, end
    raise ValueError("period_type must be 'daily' or 'weekly'")


def _log_norm(value: Any, max_value: float) -> float:
    numeric = max(float(value or 0), 0.0)
    if max_value <= 0:
        return 0.0
    return min(math.log1p(numeric) / max_value, 1.0)


def _round_component(value: float) -> float:
    return round(max(min(float(value), 1.0), 0.0), 4)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_heat_rankings(
    rows: list[dict[str, Any]],
    *,
    entity_type: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    max_mention = max((math.log1p(max(float(row.get("mention_count") or 0), 0.0)) for row in rows), default=0.0)
    max_hotness = max((math.log1p(max(float(row.get("news_hotness_sum") or 0), 0.0)) for row in rows), default=0.0)
    max_source = max((math.log1p(max(float(row.get("source_count") or 0), 0.0)) for row in rows), default=0.0)

    scored: list[dict[str, Any]] = []
    for row in rows:
        mention_norm = _round_component(_log_norm(row.get("mention_count"), max_mention))
        news_hotness_norm = _round_component(_log_norm(row.get("news_hotness_sum"), max_hotness))
        source_norm = _round_component(_log_norm(row.get("source_count"), max_source))
        freshness_norm = _round_component(_safe_float(row.get("freshness_score")))
        anchor_norm = _round_component(_safe_float(row.get("anchor_score"), 0.2))

        heat_score = 100.0 * (
            (ENTITY_HEAT_FORMULA["mention_weight"] * mention_norm)
            + (ENTITY_HEAT_FORMULA["news_hotness_weight"] * news_hotness_norm)
            + (ENTITY_HEAT_FORMULA["source_weight"] * source_norm)
            + (ENTITY_HEAT_FORMULA["freshness_weight"] * freshness_norm)
            + (ENTITY_HEAT_FORMULA["anchor_weight"] * anchor_norm)
        )
        item = {
            "entity_uuid": row.get("entity_uuid"),
            "entity_name": row.get("entity_name") or row.get("entity_uuid"),
            "entity_labels": list(row.get("entity_labels") or []),
            "entity_type": entity_type,
            "heat_score": round(heat_score, 2),
            "mention_count": int(row.get("mention_count") or 0),
            "source_count": int(row.get("source_count") or 0),
            "news_hotness_sum": round(_safe_float(row.get("news_hotness_sum")), 4),
            "freshness_score": freshness_norm,
            "anchor_score": anchor_norm,
            "anchor_id": row.get("anchor_id"),
            "top_evidence": list(row.get("top_evidence") or []),
            "components": {
                "mention_norm": mention_norm,
                "news_hotness_norm": news_hotness_norm,
                "source_norm": source_norm,
                "freshness_norm": freshness_norm,
                "anchor_norm": anchor_norm,
            },
        }
        scored.append(item)

    scored.sort(
        key=lambda item: (
            item["heat_score"],
            item["mention_count"],
            item["news_hotness_sum"],
            item["entity_name"],
        ),
        reverse=True,
    )
    if limit is not None:
        scored = scored[: max(int(limit), 0)]
    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank
    return scored


def _serialize_formula() -> dict[str, float]:
    return {key: value for key, value in ENTITY_HEAT_FORMULA.items() if key != "formula_version"}


def _normalize_entity_type(entity_type: str | None) -> str | None:
    if entity_type is None:
        return None
    normalized = str(entity_type).strip()
    return normalized if normalized else None


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class EntityHeatRankingService:
    def __init__(self, driver):
        self.driver = driver

    async def generate_and_store_rankings(
        self,
        *,
        period_type: str,
        as_of: str | datetime | None = None,
        entity_type: str | None = None,
        limit_per_type: int = 50,
    ) -> dict[str, Any]:
        target_types = [_normalize_entity_type(entity_type)] if entity_type else list(ENTITY_TYPE_LABELS)
        target_types = [item for item in target_types if item]
        period_start, period_end = resolve_period_window(period_type, as_of)

        type_results = []
        for current_type in target_types:
            rows = await self._load_candidate_rows(
                entity_type=current_type,
                period_start=period_start,
                period_end=period_end,
            )
            ranked = compute_heat_rankings(rows, entity_type=current_type, limit=limit_per_type)
            await self._replace_snapshots(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                entity_type=current_type,
                ranked=ranked,
            )
            type_results.append(
                self._build_payload(
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    entity_type=current_type,
                    items=ranked,
                )
            )

        if len(type_results) == 1:
            return type_results[0]
        return {
            "period_type": period_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "entity_type": "all",
            "formula_version": FORMULA_VERSION,
            "formula": _serialize_formula(),
            "type_results": type_results,
            "items": [item for result in type_results for item in result["items"]],
        }

    async def query_rankings(
        self,
        *,
        period_type: str,
        date: str | datetime | None = None,
        entity_type: str | None = "Enterprise",
        limit: int = 50,
    ) -> dict[str, Any]:
        normalized_type = _normalize_entity_type(entity_type) or "Enterprise"
        normalized_period_type = str(period_type or "daily").strip().lower()
        requested_latest = date is None or str(date).strip().lower() in {"", "latest"}
        if requested_latest:
            latest_period_start = await self._load_latest_period_start(
                period_type=normalized_period_type,
                entity_type=normalized_type,
            )
            period_start, period_end = resolve_period_window(normalized_period_type, latest_period_start)
        else:
            period_start, period_end = resolve_period_window(normalized_period_type, date)
        query = """
        MATCH (snapshot:EntityHeatSnapshot {
            period_type: $period_type,
            period_start: $period_start,
            entity_type: $entity_type,
            formula_version: $formula_version
        })
        RETURN properties(snapshot) AS snapshot
        ORDER BY snapshot.rank ASC
        LIMIT $limit
        """
        records, _, _ = await self.driver.execute_query(
            query,
            period_type=normalized_period_type,
            period_start=period_start.isoformat(),
            entity_type=normalized_type,
            formula_version=FORMULA_VERSION,
            limit=limit,
        )
        items = [self._snapshot_to_item(dict(record["snapshot"])) for record in records]
        return self._build_payload(
            period_type=normalized_period_type,
            period_start=period_start,
            period_end=period_end,
            entity_type=normalized_type,
            items=items,
        )

    async def _load_latest_period_start(self, *, period_type: str, entity_type: str) -> str | None:
        query = """
        MATCH (snapshot:EntityHeatSnapshot {
            period_type: $period_type,
            entity_type: $entity_type,
            formula_version: $formula_version
        })
        RETURN snapshot.period_start AS period_start
        ORDER BY snapshot.period_start DESC
        LIMIT 1
        """
        records, _, _ = await self.driver.execute_query(
            query,
            period_type=str(period_type).strip().lower(),
            entity_type=entity_type,
            formula_version=FORMULA_VERSION,
        )
        if not records:
            return None
        return _to_iso(records[0].get("period_start"))

    async def _load_candidate_rows(
        self,
        *,
        entity_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        labels = ENTITY_TYPE_LABELS.get(entity_type, [entity_type])
        query = """
        MATCH (ep:Episodic)-[mention]-(entity:Entity)
        WHERE type(mention) IN ['MENTIONS', 'mentions']
          AND coalesce(ep.publish_time, ep.valid_at, ep.created_at) >= datetime($period_start)
          AND coalesce(ep.publish_time, ep.valid_at, ep.created_at) <= datetime($period_end)
          AND any(label IN labels(entity) WHERE label IN $labels)
        WITH entity, collect(DISTINCT ep) AS episodes
        OPTIONAL MATCH (entity)-[:refersTo]->(anchor:CommonSenseAnchor)
        WITH entity, episodes, collect(DISTINCT anchor.anchor_id) AS ref_anchor_ids
        OPTIONAL MATCH (entity)-[:candidateRefersTo]->(candidate:CommonSenseAnchor)
        WITH entity, episodes, ref_anchor_ids, collect(DISTINCT candidate.anchor_id) AS candidate_anchor_ids
        UNWIND episodes AS evidenceEp
        WITH entity, episodes, ref_anchor_ids, candidate_anchor_ids, evidenceEp
        ORDER BY coalesce(evidenceEp.news_hotness_score, 0.0) DESC
        WITH
          entity,
          episodes,
          ref_anchor_ids,
          candidate_anchor_ids,
          collect({
            episode_uuid: evidenceEp.uuid,
            title: coalesce(evidenceEp.title, evidenceEp.name, ''),
            source: coalesce(evidenceEp.news_source, evidenceEp.source, ''),
            url: coalesce(evidenceEp.news_url, ''),
            publish_time: toString(coalesce(evidenceEp.publish_time, evidenceEp.valid_at, evidenceEp.created_at)),
            news_hotness_score: coalesce(evidenceEp.news_hotness_score, 0.0)
          })[0..3] AS top_evidence
        WITH
          entity,
          episodes,
          top_evidence,
          [anchor_id IN ref_anchor_ids WHERE anchor_id IS NOT NULL][0] AS ref_anchor_id,
          [anchor_id IN candidate_anchor_ids WHERE anchor_id IS NOT NULL][0] AS candidate_anchor_id
        WITH
          entity,
          episodes,
          top_evidence,
          ref_anchor_id,
          candidate_anchor_id,
          reduce(total = 0.0, ep IN episodes | total + coalesce(ep.news_hotness_score, 0.0)) AS hotness_sum
        RETURN
          entity.uuid AS entity_uuid,
          coalesce(entity.name, entity.uuid) AS entity_name,
          labels(entity) AS entity_labels,
          size(episodes) AS mention_count,
          hotness_sum AS news_hotness_sum,
          [ep IN episodes | coalesce(ep.news_source, ep.source, '')] AS source_names,
          [ep IN episodes | coalesce(ep.publish_time, ep.valid_at, ep.created_at)] AS publish_times,
          CASE
            WHEN ref_anchor_id IS NOT NULL THEN 1.0
            WHEN candidate_anchor_id IS NOT NULL THEN 0.6
            ELSE 0.2
          END AS anchor_score,
          coalesce(ref_anchor_id, candidate_anchor_id) AS anchor_id,
          top_evidence AS top_evidence
        """
        records, _, _ = await self.driver.execute_query(
            query,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            labels=labels,
        )
        return [self._record_to_row(record, period_start=period_start, period_end=period_end) for record in records]

    async def _replace_snapshots(
        self,
        *,
        period_type: str,
        period_start: datetime,
        period_end: datetime,
        entity_type: str,
        ranked: list[dict[str, Any]],
    ) -> None:
        await self.driver.execute_query(
            """
            MATCH (snapshot:EntityHeatSnapshot {
                period_type: $period_type,
                period_start: $period_start,
                entity_type: $entity_type,
                formula_version: $formula_version
            })
            DETACH DELETE snapshot
            """,
            period_type=str(period_type).strip().lower(),
            period_start=period_start.isoformat(),
            entity_type=entity_type,
            formula_version=FORMULA_VERSION,
        )
        items = [self._snapshot_properties(item, period_type, period_start, period_end) for item in ranked]
        await self.driver.execute_query(
            """
            UNWIND $items AS item
            MATCH (entity:Entity {uuid: item.entity_uuid})
            MERGE (snapshot:EntityHeatSnapshot {snapshot_id: item.snapshot_id})
            SET snapshot += item.snapshot_properties
            MERGE (snapshot)-[:RANKS_ENTITY]->(entity)
            WITH snapshot, item
            UNWIND item.evidence_links AS evidence
            MATCH (ep:Episodic {uuid: evidence.episode_uuid})
            MERGE (snapshot)-[rel:EVIDENCED_BY {rank: evidence.rank}]->(ep)
            SET rel.news_hotness_score = evidence.news_hotness_score
            """,
            items=items,
        )

    @staticmethod
    def _record_to_row(record: Any, *, period_start: datetime, period_end: datetime) -> dict[str, Any]:
        row = dict(record)
        if row.get("source_count") is None:
            source_names = [str(item).strip() for item in row.get("source_names") or [] if str(item).strip()]
            row["source_count"] = len(set(source_names))
        if row.get("freshness_score") is None and row.get("publish_times"):
            row["freshness_score"] = _average_freshness(row["publish_times"], period_start, period_end)
        return row

    @staticmethod
    def _snapshot_properties(
        item: dict[str, Any],
        period_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        snapshot_id = "|".join(
            [
                FORMULA_VERSION,
                str(period_type).strip().lower(),
                period_start.isoformat(),
                item["entity_type"],
                str(item["entity_uuid"]),
            ]
        )
        evidence_links = []
        for index, evidence in enumerate(item.get("top_evidence") or [], start=1):
            episode_uuid = evidence.get("episode_uuid")
            if not episode_uuid:
                continue
            evidence_links.append(
                {
                    "rank": index,
                    "episode_uuid": episode_uuid,
                    "news_hotness_score": _safe_float(evidence.get("news_hotness_score")),
                }
            )
        snapshot_properties = {
            "snapshot_id": snapshot_id,
            "formula_version": FORMULA_VERSION,
            "period_type": str(period_type).strip().lower(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "entity_type": item["entity_type"],
            "entity_uuid": item["entity_uuid"],
            "entity_name": item["entity_name"],
            "entity_labels": item["entity_labels"],
            "rank": item["rank"],
            "heat_score": item["heat_score"],
            "mention_count": item["mention_count"],
            "source_count": item["source_count"],
            "news_hotness_sum": item["news_hotness_sum"],
            "freshness_score": item["freshness_score"],
            "anchor_score": item["anchor_score"],
            "anchor_id": item.get("anchor_id"),
            "components_json": json.dumps(item.get("components") or {}, ensure_ascii=False),
            "top_evidence_json": json.dumps(item.get("top_evidence") or [], ensure_ascii=False, default=str),
            "updated_at": datetime.now(SHANGHAI_TZ).isoformat(),
        }
        return {
            "snapshot_id": snapshot_id,
            "entity_uuid": item["entity_uuid"],
            "snapshot_properties": snapshot_properties,
            "evidence_links": evidence_links,
        }

    @staticmethod
    def _snapshot_to_item(snapshot: dict[str, Any]) -> dict[str, Any]:
        top_evidence = []
        raw_evidence = snapshot.get("top_evidence_json")
        if raw_evidence:
            try:
                top_evidence = json.loads(raw_evidence)
            except json.JSONDecodeError:
                top_evidence = []
        components = {}
        raw_components = snapshot.get("components_json")
        if raw_components:
            try:
                components = json.loads(raw_components)
            except json.JSONDecodeError:
                components = {}
        return {
            "rank": int(snapshot.get("rank") or 0),
            "entity_uuid": snapshot.get("entity_uuid"),
            "entity_name": snapshot.get("entity_name"),
            "entity_labels": snapshot.get("entity_labels") or [],
            "entity_type": snapshot.get("entity_type"),
            "heat_score": _safe_float(snapshot.get("heat_score")),
            "mention_count": int(snapshot.get("mention_count") or 0),
            "source_count": int(snapshot.get("source_count") or 0),
            "news_hotness_sum": _safe_float(snapshot.get("news_hotness_sum")),
            "freshness_score": _safe_float(snapshot.get("freshness_score")),
            "anchor_score": _safe_float(snapshot.get("anchor_score")),
            "anchor_id": snapshot.get("anchor_id"),
            "components": components,
            "top_evidence": top_evidence,
        }

    @staticmethod
    def _build_payload(
        *,
        period_type: str,
        period_start: datetime,
        period_end: datetime,
        entity_type: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "period_type": str(period_type).strip().lower(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "entity_type": entity_type,
            "formula_version": FORMULA_VERSION,
            "formula": _serialize_formula(),
            "items": items,
        }


def _average_freshness(publish_times: list[Any], period_start: datetime, period_end: datetime) -> float:
    scores = []
    period_seconds = max((period_end - period_start).total_seconds(), 1.0)
    for value in publish_times:
        published = _as_aware_datetime(_to_iso(value))
        age_seconds = max((period_end - published).total_seconds(), 0.0)
        scores.append(max(0.0, min(1.0, 1.0 - (age_seconds / period_seconds))))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
