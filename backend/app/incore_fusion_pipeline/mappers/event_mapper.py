"""Utilities for event mapping and enrichment."""

from __future__ import annotations

from typing import Dict

from app.incore_fusion_pipeline.dto.normalized_dto import MatchReferenceDTO, NormalizedEventDTO


class EventMapper:
    """Apply light enrichment to normalized events."""

    DEFAULT_EVENT_CATEGORY: Dict[str, str] = {
        "GovernmentPublishPolicyEvent": "政策发布",
        "CompanyCooperationEvent": "企业合作",
        "CompanyFinancingEvent": "企业融资",
        "Event": "泛化事件",
    }

    def enrich(self, event: NormalizedEventDTO) -> NormalizedEventDTO:
        """Fill minimal defaults so downstream stages see consistent events."""

        if event.category_ref is None:
            category_name = self.DEFAULT_EVENT_CATEGORY.get(event.event_type, "泛化事件")
            event.category_ref = MatchReferenceDTO(type="EventCategory", match_key=category_name)
        if event.location_ref is None and event.properties.get("location"):
            event.location_ref = MatchReferenceDTO(type="Region", match_key=str(event.properties["location"]))
        if event.event_type == "CompanyFinancingEvent" and event.object_ref is not None:
            event.object_ref.type = "Organization"
        if event.event_type == "CompanyCooperationEvent" and event.object_ref is not None:
            event.object_ref.type = "IndustryActor"
        if event.event_type == "GovernmentPublishPolicyEvent":
            if event.subject_ref is not None:
                event.subject_ref.type = "Organization"
            if event.object_ref is not None:
                event.properties["object"] = event.object_ref.match_key
        if not event.summary:
            event.summary = event.name
        return event
