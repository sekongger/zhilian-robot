"""Canonical node matcher for the Wikidata fusion skeleton."""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import CanonicalNodeIndexDTO, MappedV2NodeDTO
from app.incore_fusion_pipeline.utils.normalization import normalize_company_core_name, normalize_text_key


class WikidataCanonicalMatcher:
    """Resolve a v2 node against an in-memory canonical node index."""

    def match(
        self,
        *,
        mapped_node: MappedV2NodeDTO,
        canonical_index: Iterable[CanonicalNodeIndexDTO],
    ) -> Tuple[Optional[CanonicalNodeIndexDTO], Optional[str], float]:
        for candidate in canonical_index:
            if candidate.type_name != mapped_node.normalized_type:
                continue
            if self._is_exact_name_match(mapped_node, candidate):
                return candidate, "exact_name", 1.0
            if self._is_alias_match(mapped_node, candidate):
                return candidate, "alias", 0.95
            if self._is_company_core_match(mapped_node, candidate):
                return candidate, "company_core", 0.9
        return None, None, 0.0

    def _is_exact_name_match(self, mapped_node: MappedV2NodeDTO, candidate: CanonicalNodeIndexDTO) -> bool:
        if not mapped_node.name:
            return False
        return normalize_text_key(mapped_node.name) == normalize_text_key(candidate.name)

    def _is_alias_match(self, mapped_node: MappedV2NodeDTO, candidate: CanonicalNodeIndexDTO) -> bool:
        values = []
        for key in ("name", "officialName", "shortName"):
            value = mapped_node.match_keys.get(key)
            if isinstance(value, list):
                values.extend(str(item) for item in value if item)
            elif value:
                values.append(str(value))
        for key in ("alias", "aliases", "nameEn"):
            value = mapped_node.match_keys.get(key)
            if isinstance(value, list):
                values.extend(str(item) for item in value if item)
            elif value:
                values.append(str(value))
        wanted = {normalize_text_key(item) for item in values if item}
        candidate_aliases = {normalize_text_key(candidate.name), *(normalize_text_key(item) for item in candidate.aliases)}
        official_name = candidate.properties.get("officialName")
        if official_name:
            candidate_aliases.add(normalize_text_key(str(official_name)))
        return bool(wanted & candidate_aliases)

    def _is_company_core_match(self, mapped_node: MappedV2NodeDTO, candidate: CanonicalNodeIndexDTO) -> bool:
        if mapped_node.normalized_type != "Enterprise" or not mapped_node.name:
            return False
        source_core = normalize_company_core_name(mapped_node.name)
        candidate_values = [candidate.name, *candidate.aliases]
        official_name = candidate.properties.get("officialName")
        if official_name:
            candidate_values.append(str(official_name))
        return any(source_core == normalize_company_core_name(value) for value in candidate_values if value)
