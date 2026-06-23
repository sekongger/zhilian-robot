import os
import re
from typing import Any, Optional

import requests


class WikidataMappingService:
    """
    Standalone mapper backed by real Wikidata lookup (wbsearchentities).
    Not wired into crawler/compression flow yet.
    """

    def __init__(self) -> None:
        self._api_url = os.getenv("WIKIDATA_API_URL", "https://www.wikidata.org/w/api.php")
        self._timeout = float(os.getenv("WIKIDATA_TIMEOUT_SECONDS", "8"))
        self._search_limit = int(os.getenv("WIKIDATA_SEARCH_LIMIT", "8"))
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "graphiti-project/0.1 (wikidata-mapper)",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _normalize(value: str) -> str:
        text = (value or "").strip().lower()
        text = text.replace("_", "-")
        text = re.sub(r"\s+", "", text)
        return text

    @staticmethod
    def _has_cjk(value: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", value or ""))

    @staticmethod
    def _extract_base_and_version(value: str) -> tuple[str, Optional[str]]:
        text = (value or "").strip()
        # Generic trailing version extraction:
        # qwen3 / qwen3.5 / qwen-3 / qwen v3.5 / ChineseName3 / ChineseName 3.5
        m = re.match(
            r"^(?P<base>.*?)(?:[\s\-_]*v?(?P<ver>\d+(?:\.\d+)*))$",
            text,
            flags=re.IGNORECASE,
        )
        if not m:
            return text, None

        base = (m.group("base") or "").strip(" -_")
        version = (m.group("ver") or "").strip()
        if not base or not version:
            return text, None
        return base, version

    @staticmethod
    def _extract_label(item: dict[str, Any]) -> Optional[str]:
        label = item.get("label")
        if label:
            return str(label)
        display = item.get("display") or {}
        label_obj = display.get("label") or {}
        value = label_obj.get("value")
        return str(value) if value else None

    @staticmethod
    def _extract_description(item: dict[str, Any]) -> Optional[str]:
        description = item.get("description")
        if description:
            return str(description)
        display = item.get("display") or {}
        description_obj = display.get("description") or {}
        value = description_obj.get("value")
        return str(value) if value else None

    @staticmethod
    def _extract_match_text(item: dict[str, Any]) -> Optional[str]:
        match = item.get("match") or {}
        text = match.get("text")
        return str(text) if text else None

    @staticmethod
    def _extract_match_type(item: dict[str, Any]) -> Optional[str]:
        match = item.get("match") or {}
        match_type = match.get("type")
        return str(match_type) if match_type else None

    def _query_wikidata(self, search_term: str, language: str) -> list[dict[str, Any]]:
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": language,
            "uselang": language,
            "type": "item",
            "limit": self._search_limit,
            "search": search_term,
        }
        response = self._session.get(self._api_url, params=params, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        return payload.get("search", [])

    def _score_candidate(
        self,
        *,
        raw_name: str,
        base_name: str,
        search_term: str,
        language: str,
        rank: int,
        label: str,
        match_text: Optional[str],
        match_type: Optional[str],
    ) -> float:
        raw_norm = self._normalize(raw_name)
        base_norm = self._normalize(base_name)
        label_norm = self._normalize(label)
        match_norm = self._normalize(match_text or "")

        score = 100.0 - (rank * 5.0)
        if self._normalize(search_term) == raw_norm:
            score += 12.0
        if base_norm and base_norm != raw_norm and self._normalize(search_term) == base_norm:
            score += 8.0
        if raw_norm and raw_norm in label_norm:
            score += 10.0
        if base_norm and base_norm in label_norm:
            score += 8.0
        if match_norm and (match_norm in raw_norm or raw_norm in match_norm):
            score += 6.0
        if match_type == "label":
            score += 6.0
        elif match_type == "alias":
            score += 4.0
        if language == "zh" and self._has_cjk(raw_name):
            score += 3.0
        if language == "en" and not self._has_cjk(raw_name):
            score += 2.0
        return score

    def map_product(self, value: str) -> dict:
        raw_name = (value or "").strip()
        if not raw_name:
            return {
                "matched": False,
                "input_name": raw_name,
                "canonical_name": None,
                "wikidata_qid": None,
                "product_line": None,
                "version": None,
                "normalized_name": self._normalize(raw_name),
                "base_name": None,
                "selected_candidate": None,
                "candidates": [],
                "source": "wikidata_wbsearchentities",
                "error": "empty_input",
            }

        base_name, version = self._extract_base_and_version(raw_name)
        search_terms = [raw_name]
        if base_name and self._normalize(base_name) != self._normalize(raw_name):
            search_terms.append(base_name)
        search_terms = list(dict.fromkeys(search_terms))
        languages = ["zh", "en"] if self._has_cjk(raw_name) else ["en", "zh"]

        aggregated: dict[str, dict[str, Any]] = {}
        failures: list[str] = []

        for search_term in search_terms:
            for language in languages:
                try:
                    items = self._query_wikidata(search_term=search_term, language=language)
                except requests.RequestException as exc:
                    failures.append(f"{language}:{search_term}:{str(exc)}")
                    continue

                for idx, item in enumerate(items):
                    qid = item.get("id")
                    if not qid:
                        continue
                    label = self._extract_label(item) or ""
                    description = self._extract_description(item)
                    match_text = self._extract_match_text(item)
                    match_type = self._extract_match_type(item)
                    score = self._score_candidate(
                        raw_name=raw_name,
                        base_name=base_name,
                        search_term=search_term,
                        language=language,
                        rank=idx,
                        label=label,
                        match_text=match_text,
                        match_type=match_type,
                    )

                    existing = aggregated.get(qid)
                    candidate_payload = {
                        "wikidata_qid": qid,
                        "label": label or None,
                        "description": description,
                        "language": language,
                        "matched_text": match_text,
                        "match_type": match_type,
                        "search_term": search_term,
                        "score": round(score, 3),
                        "url": f"https://www.wikidata.org/wiki/{qid}",
                    }
                    if existing is None or score > float(existing.get("score", 0)):
                        aggregated[qid] = candidate_payload

        candidates = sorted(
            aggregated.values(),
            key=lambda x: float(x.get("score", 0)),
            reverse=True,
        )

        selected = candidates[0] if candidates else None
        product_line = selected.get("label") if selected else None
        canonical_name = None
        if product_line:
            canonical_name = f"{product_line} {version}" if version else product_line

        response: dict[str, Any] = {
            "matched": bool(selected),
            "input_name": raw_name,
            "canonical_name": canonical_name,
            "wikidata_qid": selected.get("wikidata_qid") if selected else None,
            "product_line": product_line,
            "version": version,
            "normalized_name": self._normalize(raw_name),
            "base_name": base_name,
            "selected_candidate": selected,
            "candidates": candidates,
            "source": "wikidata_wbsearchentities",
        }
        if failures and not selected:
            response["error"] = "; ".join(failures[:2])
        return response

    def map_products(self, names: list[str]) -> dict:
        results = [self.map_product(name) for name in names]
        relations: list[dict[str, Any]] = []

        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                left = results[i]
                right = results[j]
                left_qid = left.get("wikidata_qid")
                right_qid = right.get("wikidata_qid")
                if not left_qid or not right_qid:
                    continue

                left_version = left.get("version")
                right_version = right.get("version")

                relation: Optional[str]
                if left_qid == right_qid:
                    if left_version and right_version and left_version != right_version:
                        relation = "same_wikidata_entity_different_version"
                    elif left_version and right_version and left_version == right_version:
                        relation = "same_wikidata_entity_same_version_alias"
                    else:
                        relation = "same_wikidata_entity_alias_or_variant"
                else:
                    left_line = self._normalize(left.get("product_line") or "")
                    right_line = self._normalize(right.get("product_line") or "")
                    if left_line and right_line and left_line == right_line:
                        relation = "same_label_possible_same_line"
                    else:
                        relation = None

                if not relation:
                    continue

                relations.append(
                    {
                        "left": left.get("input_name"),
                        "right": right.get("input_name"),
                        "left_qid": left_qid,
                        "right_qid": right_qid,
                        "relation": relation,
                        "left_version": left_version,
                        "right_version": right_version,
                    }
                )

        return {
            "count": len(results),
            "results": results,
            "relations": relations,
            "source": "wikidata_wbsearchentities",
        }


wikidata_mapping_service = WikidataMappingService()
