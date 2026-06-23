"""Candidate filtering for industry-relevant Wikidata entities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO, WikiEntityCandidateDTO
from app.wiki_industry_pipeline.type_whitelist import WikidataTypeWhitelist


DEFAULT_TYPE_WHITELIST_PATH = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "industry_wiki"
    / "wikidata_type_whitelist.yaml"
)


TYPE_QID_TO_CATEGORY: Dict[str, str] = {
    "Q4830453": "Enterprise",
    "Q11016": "Technology",
    "Q8148": "Industry",
    "Q170978": "Industry",
}

ALL_INDUSTRY_TYPE_QID_TO_CATEGORY: Dict[str, str] = {
    "Q4830453": "Enterprise",  # business
    "Q783794": "Enterprise",  # company
    "Q891723": "Enterprise",  # public company
    "Q6881511": "Enterprise",  # enterprise
    "Q8148": "Industry",
    "Q170978": "Industry",
    "Q11016": "Technology",
}

PROPERTY_TO_CATEGORY: Dict[str, str] = {
    "P452": "Enterprise",
    "P176": "ProductModel",
}

ALL_INDUSTRY_PROPERTY_TO_CATEGORY: Dict[str, str] = {
    # A subject with a manufacturer is usually a product/model/artifact in the
    # industry-chain graph. Enterprise industry links are routed after a company
    # is selected by P31/P279 type gates, not by P452 alone.
    "P176": "ProductModel",
}

DEFAULT_KEYWORDS = [
    "robotics",
    "industrial robot",
    "humanoid robot",
    "service robot",
    "automation",
    "sensor",
    "actuator",
    "servo motor",
    "controller",
    "machine vision",
    "lidar",
    "motion control",
    "机器人",
    "工业机器人",
    "人形机器人",
    "自动化",
    "传感器",
    "控制器",
    "运动控制",
]


@dataclass
class WikiEntityCandidateFilter:
    keywords: List[str]
    type_qid_to_category: Dict[str, str]
    property_to_category: Dict[str, str]
    excluded_type_qids: Set[str]

    @classmethod
    def default(cls) -> "WikiEntityCandidateFilter":
        return cls(
            keywords=DEFAULT_KEYWORDS,
            type_qid_to_category=TYPE_QID_TO_CATEGORY,
            property_to_category=PROPERTY_TO_CATEGORY,
            excluded_type_qids=set(),
        )

    @classmethod
    def all_industry(
        cls,
        whitelist_path: str | Path = DEFAULT_TYPE_WHITELIST_PATH,
    ) -> "WikiEntityCandidateFilter":
        whitelist = WikidataTypeWhitelist.load(whitelist_path, profile="all_industry")
        return cls(
            keywords=[],
            type_qid_to_category=whitelist.type_qid_to_category,
            property_to_category=whitelist.property_to_category,
            excluded_type_qids=whitelist.excluded_type_qids,
        )

    @classmethod
    def for_domain(
        cls,
        domain: str | None,
        type_whitelist_path: str | Path = DEFAULT_TYPE_WHITELIST_PATH,
    ) -> "WikiEntityCandidateFilter":
        normalized = (domain or "").strip().lower().replace("-", "_")
        if normalized in {"all_industry", "all", "industry", "full_industry"}:
            return cls.all_industry(type_whitelist_path)
        return cls.default()

    def filter_record(self, record: WikiDumpRecordDTO) -> Optional[WikiEntityCandidateDTO]:
        raw = record.raw
        claims = raw.get("claims", {}) or {}
        categories: List[str] = []
        reasons: List[str] = []
        type_qids = self._claim_entity_ids(claims, ["P31", "P279"])

        if self.excluded_type_qids.intersection(type_qids):
            return None

        for qid in type_qids:
            category = self.type_qid_to_category.get(qid)
            if category and category not in categories:
                categories.append(category)
                reasons.append(f"type:{qid}")

        for property_id, category in self.property_to_category.items():
            if claims.get(property_id):
                if category not in categories:
                    categories.append(category)
                reasons.append(f"property:{property_id}")

        keyword_reasons = self._keyword_reasons(raw)
        reasons.extend(keyword_reasons)

        if not categories and not keyword_reasons:
            return None

        label, language = _preferred_text(raw.get("labels", {}) or {})
        if not label:
            label = record.entity_id
        return WikiEntityCandidateDTO(
            source=record.source,
            entity_id=record.entity_id,
            label=label,
            labels=_labels(raw.get("labels", {}) or {}),
            aliases=_aliases(raw.get("aliases", {}) or {}),
            description=_preferred_text(raw.get("descriptions", {}) or {})[0],
            language=language,
            sitelinks=raw.get("sitelinks", {}) or {},
            claims=claims,
            matched_reasons=_dedupe(reasons),
            candidate_categories=categories or ["Technology"],
        )

    def _keyword_reasons(self, raw: Dict[str, object]) -> List[str]:
        searchable = " ".join(
            [
                _preferred_text(raw.get("labels", {}) or {})[0],
                _preferred_text(raw.get("descriptions", {}) or {})[0],
                " ".join(_aliases(raw.get("aliases", {}) or {})),
            ]
        ).lower()
        return [f"keyword:{keyword}" for keyword in self.keywords if keyword.lower() in searchable]

    @staticmethod
    def _claim_entity_ids(claims: Dict[str, List[dict]], property_ids: Iterable[str]) -> Set[str]:
        entity_ids: Set[str] = set()
        for property_id in property_ids:
            for claim in claims.get(property_id, []) or []:
                value = (((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
                if isinstance(value, dict):
                    qid = value.get("id")
                    if qid:
                        entity_ids.add(str(qid))
        return entity_ids


def _preferred_text(values: Dict[str, dict]) -> tuple[str, str]:
    for language in ("zh", "en"):
        item = values.get(language) or {}
        value = str(item.get("value") or "").strip()
        if value:
            return value, language
    for language, item in values.items():
        value = str((item or {}).get("value") or "").strip()
        if value:
            return value, language
    return "", "en"


def _aliases(values: Dict[str, list]) -> List[str]:
    aliases: List[str] = []
    for language in ("zh", "en"):
        for item in values.get(language, []) or []:
            value = str((item or {}).get("value") or "").strip()
            if value:
                aliases.append(value)
    return _dedupe(aliases)


def _labels(values: Dict[str, dict]) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for language, item in values.items():
        value = str((item or {}).get("value") or "").strip()
        if value:
            labels[str(language)] = value
    return labels


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def build_entity_context(raw: Dict[str, object]) -> Dict[str, object]:
    label, _ = _preferred_text(raw.get("labels", {}) or {})
    description, _ = _preferred_text(raw.get("descriptions", {}) or {})
    labels = _labels(raw.get("labels", {}) or {})
    aliases = _aliases(raw.get("aliases", {}) or {})
    claims = raw.get("claims", {}) or {}
    context: Dict[str, object] = {
        "label": label,
        "labels": labels,
        "aliases": aliases,
        "description": description,
    }
    official_name = _first_literal_claim(claims, "P1448")
    short_name = _first_literal_claim(claims, "P1813")
    if official_name:
        context["officialName"] = official_name
    if short_name:
        context["shortName"] = short_name
    return context


def _first_literal_claim(claims: Dict[str, object], property_id: str) -> str:
    property_claims = claims.get(property_id, []) or []
    for claim in property_claims:
        datavalue = ((claim.get("mainsnak") or {}).get("datavalue") or {})
        if "value" not in datavalue:
            continue
        value = datavalue.get("value")
        if isinstance(value, dict):
            text = str(value.get("text") or value.get("value") or "").strip()
        else:
            text = str(value or "").strip()
        if text:
            return text
    return ""
