"""Wikidata type whitelist for IncCore all-industry extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Set

import yaml


@dataclass(frozen=True)
class WikidataTypeWhitelist:
    profile: str
    type_qid_to_category: Dict[str, str]
    property_to_category: Dict[str, str]
    excluded_type_qids: Set[str]
    payload: Dict[str, Any]

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        profile: str = "all_industry",
    ) -> "WikidataTypeWhitelist":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        profile_payload = ((payload.get("profiles") or {}).get(profile)) or {}

        type_qid_to_category: Dict[str, str] = {}
        categories = profile_payload.get("categories", {}) or {}
        for category, category_payload in categories.items():
            for item in category_payload.get("include", []) or []:
                qid = str((item or {}).get("qid") or "").strip()
                if qid:
                    type_qid_to_category[qid] = category

        property_to_category: Dict[str, str] = {}
        property_triggers = profile_payload.get("property_triggers", {}) or {}
        for category, items in property_triggers.items():
            for item in items or []:
                property_id = str((item or {}).get("property_id") or "").strip()
                if property_id:
                    property_to_category[property_id] = category

        excluded_type_qids: Set[str] = set()
        exclusions = profile_payload.get("exclusions", {}) or {}
        for items in exclusions.values():
            for item in items or []:
                qid = str((item or {}).get("qid") or "").strip()
                if qid:
                    excluded_type_qids.add(qid)

        return cls(
            profile=profile,
            type_qid_to_category=type_qid_to_category,
            property_to_category=property_to_category,
            excluded_type_qids=excluded_type_qids,
            payload=payload,
        )
