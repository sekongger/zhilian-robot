"""Link Graphiti news entities to common-sense anchors."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.news_graph_pipeline.dto import CommonSenseAnchorDTO, EntityLinkDecisionDTO
from app.news_graph_pipeline.graphiti_anchor_client import GraphitiAnchorClient


class EntityLinker:
    """Rule-based linker for the first usable news graph anchor stage."""

    def __init__(
        self,
        *,
        graphiti: Optional[Any] = None,
        high_threshold: float = 0.90,
        candidate_threshold: float = 0.60,
    ) -> None:
        self.graphiti = graphiti or GraphitiAnchorClient()
        self.high_threshold = high_threshold
        self.candidate_threshold = candidate_threshold

    def link_group(
        self,
        *,
        group_id: str,
        anchors: list[CommonSenseAnchorDTO],
        limit: int = 1000,
    ) -> dict[str, Any]:
        if not group_id:
            raise ValueError("group_id is required for entity linking")
        anchor_stats = self.graphiti.sync_anchors(anchors)
        entities = self.graphiti.load_news_entities(group_id=group_id, limit=limit)
        decisions = [self._decide(entity, anchors, group_id=group_id) for entity in entities]
        write_stats = self.graphiti.write_entity_links(decisions)
        return {
            "anchor_sync": anchor_stats,
            "entity_count": len(entities),
            "decisions": decisions,
            "write_stats": write_stats,
        }

    def _decide(
        self,
        entity: dict[str, Any],
        anchors: list[CommonSenseAnchorDTO],
        *,
        group_id: str,
    ) -> EntityLinkDecisionDTO:
        entity_id = str(entity.get("id") or entity.get("uuid") or "").strip()
        entity_name = str(entity.get("name") or entity.get("title") or "").strip()
        best_anchor: CommonSenseAnchorDTO | None = None
        best_score = 0.0
        best_method = "none"
        entity_type = str(entity.get("type") or entity.get("type_name") or "").strip()
        for anchor in anchors:
            if not self._type_compatible(entity_type, anchor.type_name):
                continue
            score, method = self._score(entity_name, anchor)
            if score > best_score:
                best_anchor = anchor
                best_score = score
                best_method = method

        if best_anchor is None or best_score < self.candidate_threshold:
            return EntityLinkDecisionDTO(
                news_entity_id=entity_id,
                news_entity_name=entity_name,
                match_score=round(best_score, 3),
                match_method=best_method,
                decision="unresolved",
                reason="no anchor above candidate threshold",
                group_id=group_id,
            )

        decision = "refersTo" if best_score >= self.high_threshold else "candidateRefersTo"
        return EntityLinkDecisionDTO(
            news_entity_id=entity_id,
            news_entity_name=entity_name,
            candidate_anchor_id=best_anchor.anchor_id,
            match_score=round(best_score, 3),
            match_method=best_method,
            decision=decision,
            reason=f"{best_method} score {best_score:.3f}",
            group_id=group_id,
        )

    def _score(self, entity_name: str, anchor: CommonSenseAnchorDTO) -> tuple[float, str]:
        entity_norm = self._normalize(entity_name)
        if not entity_norm:
            return 0.0, "empty_name"
        candidates = [(anchor.name, "exact_name"), *[(alias, "exact_alias") for alias in anchor.aliases]]
        for value, method in candidates:
            if entity_norm == self._normalize(value):
                return 1.0, method
        anchor_name_norm = self._normalize(anchor.name)
        if self._can_use_contains_match(entity_norm, anchor_name_norm) and (
            entity_norm.startswith(anchor_name_norm) or anchor_name_norm in entity_norm
        ):
            return 0.72, "prefix_or_contains"
        return 0.0, "no_match"

    @staticmethod
    def _normalize(value: str) -> str:
        text = str(value or "").lower().strip()
        text = text.replace("_", "")
        text = re.sub(r"[\s·・,，.。()（）\\[\\]【】\\-]+", "", text)
        return text

    def _type_compatible(self, entity_type: str, anchor_type: str) -> bool:
        entity = self._normalize_type(entity_type)
        anchor = self._normalize_type(anchor_type)
        if not entity or not anchor or entity == "unknown" or anchor == "unknown":
            return True
        compatible_groups = [
            {"enterprise", "organization"},
            {"product", "productmodel"},
            {"industry", "industrygroup", "economicsector"},
            {"technology"},
            {"region"},
            {"person"},
        ]
        for group in compatible_groups:
            if entity in group and anchor in group:
                return True
        return False

    @staticmethod
    def _normalize_type(value: str) -> str:
        text = str(value or "").strip()
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return re.sub(r"[^0-9A-Za-z]", "", text).lower()

    @staticmethod
    def _can_use_contains_match(container_norm: str, contained_norm: str) -> bool:
        if not container_norm or not contained_norm:
            return False
        if EntityLinker._is_ascii_token(contained_norm):
            return len(contained_norm) >= 6 and len(container_norm) >= 6
        return len(contained_norm) >= 2 and len(container_norm) >= 2

    @staticmethod
    def _is_ascii_token(value: str) -> bool:
        return bool(re.fullmatch(r"[a-z0-9]+", value or ""))
