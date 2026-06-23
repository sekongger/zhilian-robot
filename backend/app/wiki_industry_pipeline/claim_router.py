"""Route wiki claims into intrinsic/relational/unclaimed graph actions."""

from __future__ import annotations

from app.wiki_industry_pipeline.dto import RoutedClaimDTO, WikiClaimDTO
from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema


class WikiClaimRouter:
    def __init__(self, schema: IndustryWikiRoutingSchema):
        self.schema = schema

    def route(self, claim: WikiClaimDTO, *, subject_category: str) -> RoutedClaimDTO:
        rule = self.schema.route(subject_category, claim.property_id)
        route_reason = "matched routing schema" if rule.route != "unclaimed" else "no routing rule matched"
        return RoutedClaimDTO(
            source=claim.source,
            subject_id=claim.subject_id,
            subject_label=claim.subject_label,
            subject_category=subject_category,
            property_id=claim.property_id,
            route=rule.route,
            module=rule.module,
            property_name=rule.property_name,
            target_type=rule.target_type,
            edge_type=rule.edge_type,
            direction=rule.direction,
            value_id=claim.value_id,
            value_label=claim.value_label,
            value_literal=claim.value_literal,
            value_datatype=claim.value_datatype,
            route_reason=route_reason,
        )
