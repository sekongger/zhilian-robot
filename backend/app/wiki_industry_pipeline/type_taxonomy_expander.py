"""Expand Wikidata type whitelist through P279 subclass links."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Protocol, Set
from urllib.parse import urlencode
import json
import urllib.request

import yaml

from app.wiki_industry_pipeline.type_whitelist import WikidataTypeWhitelist


DEFAULT_WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"


@dataclass(frozen=True)
class WikidataSubclassDTO:
    qid: str
    label_en: str = ""
    label_zh: str = ""
    description_en: str = ""


@dataclass(frozen=True)
class TypeWhitelistExpansionResultDTO:
    input_path: str
    output_path: str
    profile: str
    max_depth: int
    seed_count: int
    added_count: int
    category_counts: Dict[str, int]


class WikidataSubclassClient(Protocol):
    def fetch_direct_subclasses(
        self,
        parent_qid: str,
        *,
        limit: int,
    ) -> List[WikidataSubclassDTO]:
        ...


class WikidataSPARQLSubclassClient:
    def __init__(
        self,
        endpoint: str = DEFAULT_WIKIDATA_SPARQL_URL,
        *,
        user_agent: str = "zhilian-robot/0.1 wikidata-type-whitelist-expander",
        timeout: int = 60,
    ):
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch_direct_subclasses(
        self,
        parent_qid: str,
        *,
        limit: int,
    ) -> List[WikidataSubclassDTO]:
        query = f"""
SELECT ?item ?itemLabel ?itemDescription WHERE {{
  ?item wdt:P279 wd:{parent_qid}.
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
LIMIT {int(limit)}
""".strip()
        url = self.endpoint + "?" + urlencode({"query": query, "format": "json"})
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.load(response)
        return [_binding_to_subclass(row) for row in payload.get("results", {}).get("bindings", [])]


def expand_type_whitelist(
    *,
    input_path: str | Path,
    output_path: str | Path,
    profile: str = "all_industry",
    max_depth: int = 2,
    limit_per_seed: int = 200,
    client: WikidataSubclassClient | None = None,
) -> TypeWhitelistExpansionResultDTO:
    source_path = Path(input_path)
    target_path = Path(output_path)
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
    whitelist = WikidataTypeWhitelist.load(source_path, profile=profile)
    active_client = client or WikidataSPARQLSubclassClient()

    profile_payload = ((payload.get("profiles") or {}).get(profile)) or {}
    categories = profile_payload.get("categories", {}) or {}
    added_count = 0
    seed_count = 0

    for category, category_payload in categories.items():
        include_items = category_payload.get("include", []) or []
        seen_qids = {str((item or {}).get("qid") or "").strip() for item in include_items}
        seed_qids = [qid for qid in seen_qids if qid]
        expandable_seed_qids = [
            str((item or {}).get("qid") or "").strip()
            for item in include_items
            if (item or {}).get("expand_subclasses", True) is not False
        ]
        expandable_seed_qids = [qid for qid in expandable_seed_qids if qid]
        seed_count += len(seed_qids)
        additions = _expand_category(
            seed_qids=expandable_seed_qids,
            category=category,
            max_depth=max_depth,
            limit_per_seed=limit_per_seed,
            client=active_client,
            seen_qids=seen_qids,
            excluded_qids=whitelist.excluded_type_qids,
        )
        include_items.extend(additions)
        added_count += len(additions)

    _attach_expansion_metadata(
        payload,
        profile=profile,
        max_depth=max_depth,
        limit_per_seed=limit_per_seed,
        added_count=added_count,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    return TypeWhitelistExpansionResultDTO(
        input_path=str(source_path),
        output_path=str(target_path),
        profile=profile,
        max_depth=max_depth,
        seed_count=seed_count,
        added_count=added_count,
        category_counts={
            category: len((category_payload.get("include") or []))
            for category, category_payload in categories.items()
        },
    )


def _expand_category(
    *,
    seed_qids: Iterable[str],
    category: str,
    max_depth: int,
    limit_per_seed: int,
    client: WikidataSubclassClient,
    seen_qids: Set[str],
    excluded_qids: Set[str],
) -> List[Dict[str, Any]]:
    additions: List[Dict[str, Any]] = []
    frontier = [(qid, 0) for qid in seed_qids]
    visited = set(seed_qids)

    while frontier:
        parent_qid, depth = frontier.pop(0)
        next_depth = depth + 1
        if next_depth > max_depth:
            continue
        for subclass in client.fetch_direct_subclasses(parent_qid, limit=limit_per_seed):
            if not subclass.qid or subclass.qid in visited:
                continue
            visited.add(subclass.qid)
            frontier.append((subclass.qid, next_depth))
            if subclass.qid in seen_qids or subclass.qid in excluded_qids:
                continue
            seen_qids.add(subclass.qid)
            additions.append(
                {
                    "qid": subclass.qid,
                    "label_en": subclass.label_en,
                    "label_zh": subclass.label_zh,
                    "description_en": subclass.description_en,
                    "match_strength": "medium",
                    "source": "wikidata_p279",
                    "parent_qid": parent_qid,
                    "depth": next_depth,
                    "reason": f"Subclass of {parent_qid}; expanded for IncCore {category} candidate gating.",
                }
            )
    return additions


def _binding_to_subclass(row: Dict[str, Any]) -> WikidataSubclassDTO:
    item = ((row.get("item") or {}).get("value") or "").rstrip("/")
    qid = item.split("/")[-1] if item else ""
    return WikidataSubclassDTO(
        qid=qid,
        label_en=(row.get("itemLabel") or {}).get("value") or "",
        description_en=(row.get("itemDescription") or {}).get("value") or "",
    )


def _attach_expansion_metadata(
    payload: Dict[str, Any],
    *,
    profile: str,
    max_depth: int,
    limit_per_seed: int,
    added_count: int,
) -> None:
    payload["expanded_from"] = {
        "profile": profile,
        "method": "wikidata P279 direct-subclass BFS",
        "max_depth": max_depth,
        "limit_per_seed": limit_per_seed,
        "added_count": added_count,
    }
