"""Online Wikidata fetcher for the industry-chain graph pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Set

import httpx
import yaml

from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO


DEFAULT_WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
DEFAULT_WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
DEFAULT_USER_AGENT = "zhilian-robot-wiki-industry-pipeline/0.1"
DEFAULT_EXPAND_PROPERTIES = {
    "P31",
    "P279",
    "P1056",
    "P452",
    "P159",
    "P571",
    "P856",
    "P1128",
    "P176",
    "P178",
    "P127",
    "P749",
    "P355",
    "P17",
    "P131",
    "P276",
}


@dataclass(frozen=True)
class WikidataSeedConfig:
    domain: str
    keywords_by_lang: Dict[str, List[str]]
    seed_qids: List[str]


class WikidataOnlineFetcher:
    """Fetch small, reproducible Wikidata slices through public APIs.

    This is intentionally not a full Wikidata dump crawler. The first objective
    is to establish a real online data acquisition path for domain-scoped graph
    construction, then persist that raw slice as JSONL for repeatable builds.
    """

    def __init__(
        self,
        *,
        api_url: str = DEFAULT_WIKIDATA_API_URL,
        sparql_url: str = DEFAULT_WIKIDATA_SPARQL_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 20.0,
        client=None,
    ) -> None:
        self.api_url = api_url
        self.sparql_url = sparql_url
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def fetch_records_from_seed_config(
        self,
        seed_terms_path: str | Path,
        *,
        search_limit_per_term: int = 3,
        max_entities: int = 100,
        expand_depth: int = 1,
        sparql_limit: int = 20,
    ) -> List[WikiDumpRecordDTO]:
        seed_config = load_seed_config(seed_terms_path)
        return self.fetch_records(
            keywords_by_lang=seed_config.keywords_by_lang,
            seed_qids=seed_config.seed_qids,
            search_limit_per_term=search_limit_per_term,
            max_entities=max_entities,
            expand_depth=expand_depth,
            sparql_limit=sparql_limit,
        )

    def fetch_records(
        self,
        *,
        keywords_by_lang: Mapping[str, Sequence[str]],
        seed_qids: Sequence[str],
        search_limit_per_term: int = 3,
        max_entities: int = 100,
        expand_depth: int = 1,
        sparql_limit: int = 20,
    ) -> List[WikiDumpRecordDTO]:
        ordered_qids = _dedupe_qids(seed_qids)
        if sparql_limit > 0:
            ordered_qids.extend(
                qid
                for qid in self.query_relation_rich_qids(
                    keywords=_flatten_keywords(keywords_by_lang),
                    limit=sparql_limit,
                )
                if qid not in ordered_qids
            )
        for language, keywords in keywords_by_lang.items():
            for keyword in keywords:
                ordered_qids.extend(
                    qid
                    for qid in self.search_entities(
                        keyword,
                        language=language,
                        limit=search_limit_per_term,
                    )
                    if qid not in ordered_qids
                )
                if len(ordered_qids) >= max_entities:
                    break
            if len(ordered_qids) >= max_entities:
                break

        records_by_qid: Dict[str, WikiDumpRecordDTO] = {}
        frontier = ordered_qids[:max_entities]
        for _ in range(max(0, expand_depth) + 1):
            remaining = [qid for qid in frontier if qid not in records_by_qid]
            if not remaining:
                break
            fetched = self.fetch_entities(remaining[: max_entities - len(records_by_qid)])
            for record in fetched:
                records_by_qid.setdefault(record.entity_id, record)
            if len(records_by_qid) >= max_entities:
                break
            frontier = [
                qid
                for qid in _linked_entity_ids((record.raw for record in fetched), DEFAULT_EXPAND_PROPERTIES)
                if qid not in records_by_qid
            ][: max_entities - len(records_by_qid)]

        return list(records_by_qid.values())

    def query_relation_rich_qids(self, *, keywords: Sequence[str], limit: int = 20) -> List[str]:
        regex = _keyword_regex(keywords)
        if not regex:
            return []
        query = f"""
SELECT DISTINCT ?item WHERE {{
  {{
    VALUES ?prop {{ wdt:P1056 wdt:P452 wdt:P176 wdt:P178 wdt:P159 wdt:P571 }}
    ?item ?prop ?value .
    ?item rdfs:label ?label .
  }}
  UNION
  {{
    VALUES ?prop {{ wdt:P1056 wdt:P452 wdt:P176 wdt:P178 }}
    ?item ?prop ?value .
    ?value rdfs:label ?label .
  }}
  FILTER(LANG(?label) = "en" || LANG(?label) = "zh")
  FILTER(REGEX(LCASE(STR(?label)), "{regex}", "i"))
}}
LIMIT {max(1, int(limit))}
""".strip()
        payload = self._get_sparql(query)
        bindings = ((payload.get("results") or {}).get("bindings") or [])
        return _dedupe_qids(_qid_from_uri(((item.get("item") or {}).get("value") or "")) for item in bindings)

    def search_entities(self, keyword: str, *, language: str = "en", limit: int = 3) -> List[str]:
        keyword = str(keyword or "").strip()
        if not keyword:
            return []
        payload = self._get(
            {
                "action": "wbsearchentities",
                "format": "json",
                "language": language or "en",
                "uselang": language or "en",
                "search": keyword,
                "limit": max(1, limit),
            }
        )
        return _dedupe_qids(item.get("id") for item in payload.get("search", []) or [])

    def fetch_entities(self, qids: Sequence[str]) -> List[WikiDumpRecordDTO]:
        records: List[WikiDumpRecordDTO] = []
        for chunk in _chunks(_dedupe_qids(qids), 50):
            payload = self._get(
                {
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": "|".join(chunk),
                    "props": "labels|aliases|descriptions|claims|sitelinks",
                    "languages": "zh|en",
                    "languagefallback": "1",
                }
            )
            entities = payload.get("entities", {}) or {}
            for qid in chunk:
                entity = entities.get(qid) or {}
                if entity.get("missing") is not None:
                    continue
                entity_id = str(entity.get("id") or qid).strip()
                if entity_id:
                    records.append(WikiDumpRecordDTO(entity_id=entity_id, raw=entity))
        return records

    def _get(self, params: Dict[str, object]) -> Dict[str, object]:
        response = self.client.get(
            self.api_url,
            params=params,
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _get_sparql(self, query: str) -> Dict[str, object]:
        response = self.client.get(
            self.sparql_url,
            params={"query": query, "format": "json"},
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/sparql-results+json",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


def load_seed_config(path: str | Path) -> WikidataSeedConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    keywords_payload = payload.get("keywords", {}) or {}
    seed_payload = payload.get("seed_qids", {}) or {}
    return WikidataSeedConfig(
        domain=str(payload.get("domain") or "wiki_industry"),
        keywords_by_lang={
            str(language): [str(item).strip() for item in values or [] if str(item).strip()]
            for language, values in keywords_payload.items()
        },
        seed_qids=_dedupe_qids(
            qid
            for values in seed_payload.values()
            for qid in (values or [])
        ),
    )


def write_records_jsonl(records: Iterable[WikiDumpRecordDTO], path: str | Path) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.raw, ensure_ascii=False, separators=(",", ":")) + "\n")


def _linked_entity_ids(records: Iterable[dict], property_ids: Set[str]) -> List[str]:
    qids: List[str] = []
    for record in records:
        claims = record.get("claims", {}) or {}
        for property_id in property_ids:
            for claim in claims.get(property_id, []) or []:
                value = (((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
                if not isinstance(value, dict):
                    continue
                qid = str(value.get("id") or "").strip()
                if qid and qid not in qids:
                    qids.append(qid)
    return qids


def _flatten_keywords(keywords_by_lang: Mapping[str, Sequence[str]]) -> List[str]:
    return [
        str(keyword).strip()
        for keywords in keywords_by_lang.values()
        for keyword in keywords
        if str(keyword).strip()
    ]


def _keyword_regex(keywords: Sequence[str]) -> str:
    selected = []
    for keyword in keywords:
        text = str(keyword).strip().lower()
        if len(text) < 2:
            continue
        tokens = re.findall(r"[0-9a-zA-Z_\u4e00-\u9fff]+", text)
        if not tokens:
            continue
        pattern = ".*".join(tokens)
        if all(re.fullmatch(r"[0-9a-zA-Z_]+", token) for token in tokens):
            pattern = f"(^|[^0-9a-zA-Z]){pattern}([^0-9a-zA-Z]|$)"
        selected.append(pattern)
        if len(selected) >= 16:
            break
    return "|".join(selected)


def _qid_from_uri(value: str) -> str:
    match = re.search(r"/entity/(Q\d+)$", str(value or ""))
    return match.group(1) if match else str(value or "").strip()


def _dedupe_qids(values: Iterable[object]) -> List[str]:
    qids: List[str] = []
    for value in values:
        qid = str(value or "").strip()
        if qid and qid.startswith("Q") and qid not in qids:
            qids.append(qid)
    return qids


def _chunks(values: Sequence[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])
