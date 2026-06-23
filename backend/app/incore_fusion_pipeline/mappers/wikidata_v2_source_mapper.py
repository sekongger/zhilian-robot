"""Map Neo4j v2 nodes into layered fusion payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import MappedV2NodeDTO, V2SourceNodeDTO


class WikidataV2SourceMapper:
    """Translate v2 nodes into the layered fusion structure from the proposal."""

    ANALYTICS_FIELDS = {
        "momentum_score",
        "momentum_updated_at",
        "pageRank",
        "communityId",
        "created_at",
        "updated_at",
        "name_embedding",
    }
    FACT_FIELDS = {
        "summary",
        "description",
        "raw_text",
        "structured_facts_json",
    }
    MATCH_FIELDS = {
        "name",
        "officialName",
        "shortName",
        "alias",
        "aliases",
        "nameEn",
        "officialWebsite",
        "brand",
        "series",
        "model",
        "belongsToProduct",
    }
    CANONICAL_FIELDS = {
        "officialName",
        "shortName",
        "alias",
        "aliases",
        "nameEn",
        "officialWebsite",
        "mainBusiness",
        "businessScope",
        "status",
        "brand",
        "series",
        "model",
        "belongsToProduct",
        "subclassOf",
        "region",
        "inception",
        "publishDate",
    }

    def map_node(self, *, source_label: str, raw: Dict[str, Any]) -> MappedV2NodeDTO:
        """Map a raw node payload exported from Neo4j v2."""

        source_system = str(raw.get("source_system") or raw.get("sourceSystem") or "neo4j_v2")
        profile_key = self._profile_key(source_system)
        source_uuid = str(raw.get("uuid") or raw.get("source_uuid") or raw.get("id") or "")
        payload = self._merged_properties(raw)
        normalized_type = self._normalize_type(source_label=source_label, payload=payload)
        name = self._first_non_empty(payload.get("name"), raw.get("name"))

        match_keys = self._build_match_keys(name=name, payload=payload)
        canonical_candidates = self._build_canonical_candidates(name=name, normalized_type=normalized_type, payload=payload)
        source_profiles = self._build_source_profiles(profile_key=profile_key, payload=payload)
        analytics = self._build_analytics(profile_key=profile_key, payload=payload)
        fact_payload = self._build_fact_payload(payload=payload)

        return MappedV2NodeDTO(
            source_system=source_system,
            source_uuid=source_uuid,
            original_type=source_label,
            normalized_type=normalized_type,
            name=name,
            match_keys=match_keys,
            canonical_candidates=canonical_candidates,
            source_profiles=source_profiles,
            analytics=analytics,
            fact_payload=fact_payload,
            raw_properties=payload,
        )

    def map_source_node(self, node: V2SourceNodeDTO) -> MappedV2NodeDTO:
        """Map a typed DTO node into the layered fusion structure."""

        raw = dict(node.properties or {})
        raw["uuid"] = node.source_uuid
        raw["name"] = node.name
        if node.summary is not None:
            raw["summary"] = node.summary
        raw["source_system"] = node.source_system
        return self.map_node(source_label=node.source_label, raw=raw)

    def _merged_properties(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(raw)
        nested = payload.pop("properties", None)
        if isinstance(nested, dict):
            merged = dict(nested)
            merged.update({key: value for key, value in payload.items() if value is not None})
            return merged
        return payload

    def _normalize_type(self, *, source_label: str, payload: Dict[str, Any]) -> str:
        normalized = str(source_label or "").strip()
        if normalized == "Product":
            if any(payload.get(field) for field in ("brand", "series", "model")):
                return "ProductModel"
        return normalized or "Unknown"

    def _build_match_keys(self, *, name: str | None, payload: Dict[str, Any]) -> Dict[str, Any]:
        match_keys: Dict[str, Any] = {}
        if name:
            match_keys["name"] = name
        for field in self.MATCH_FIELDS:
            value = payload.get(field)
            if value in (None, "", []):
                continue
            match_keys[field] = value
        return match_keys

    def _build_canonical_candidates(
        self,
        *,
        name: str | None,
        normalized_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidates: Dict[str, Any] = {}
        if name:
            candidates["name"] = name
        if normalized_type in {"Enterprise", "Product", "ProductModel", "Technology", "Region", "Organization", "Person"}:
            for field in self.CANONICAL_FIELDS:
                value = payload.get(field)
                if value in (None, "", []):
                    continue
                target_field = "alias" if field == "aliases" else field
                candidates[target_field] = value
        return candidates

    def _build_source_profiles(self, *, profile_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        profile: Dict[str, Any] = {}
        attributes: Dict[str, Any] = {}
        for key, value in payload.items():
            if value in (None, "", []):
                continue
            if key in self.ANALYTICS_FIELDS or key in self.FACT_FIELDS:
                continue
            if key.startswith("attributes__"):
                attributes[key.removeprefix("attributes__")] = value
                continue
            profile[key] = value
        if attributes:
            profile["attributes"] = attributes
        return {profile_key: profile}

    def _build_analytics(self, *, profile_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        analytics = {
            key: value
            for key, value in payload.items()
            if key in self.ANALYTICS_FIELDS and value not in (None, "", [])
        }
        return {profile_key: analytics} if analytics else {}

    def _build_fact_payload(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        fact_payload: Dict[str, Any] = {}
        for field in self.FACT_FIELDS:
            value = payload.get(field)
            if value in (None, "", []):
                continue
            fact_payload[field] = value
        return fact_payload

    @staticmethod
    def _first_non_empty(*values: Iterable[Any] | Any) -> str | None:
        for value in values:
            if value in (None, "", []):
                continue
            return str(value)
        return None

    @staticmethod
    def _profile_key(source_system: str) -> str:
        if source_system == "neo4j_v2":
            return "v2"
        return source_system
