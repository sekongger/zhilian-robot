"""Property merge strategy for the Wikidata fusion skeleton."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import CanonicalNodeIndexDTO, MappedV2NodeDTO


class FusionPropertyMerger:
    """Merge mapped v2 payloads into canonical node properties."""

    def merge(
        self,
        *,
        mapped_node: MappedV2NodeDTO,
        canonical_node: Optional[CanonicalNodeIndexDTO] = None,
    ) -> Dict[str, Any]:
        properties: Dict[str, Any] = dict(canonical_node.properties or {}) if canonical_node else {}

        for key, value in mapped_node.canonical_candidates.items():
            if value in (None, "", []):
                continue
            if key not in properties or properties[key] in (None, "", []):
                properties[key] = value

        if mapped_node.source_profiles:
            properties["sourceProfiles"] = self._merge_nested(
                properties.get("sourceProfiles"),
                mapped_node.source_profiles,
            )
        if mapped_node.analytics:
            properties["analytics"] = self._merge_nested(properties.get("analytics"), mapped_node.analytics)
        if mapped_node.fact_payload:
            properties["factPayload"] = self._merge_nested(properties.get("factPayload"), mapped_node.fact_payload)
        return properties

    @staticmethod
    def _merge_nested(existing: Any, incoming: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(existing or {})
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                nested = dict(result[key])
                nested.update(value)
                result[key] = nested
            else:
                result[key] = value
        return result
