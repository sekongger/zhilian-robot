"""Coverage reporting for wiki industry graph batches."""

from __future__ import annotations

from collections import Counter

from app.wiki_industry_pipeline.dto import WikiCoverageReportDTO, WikiGraphBuildBatchDTO


class WikiCoverageReporter:
    def report(self, batch: WikiGraphBuildBatchDTO, *, raw_record_count: int, stub_node_count: int = 0) -> WikiCoverageReportDTO:
        property_counts = Counter(claim.property_id for claim in batch.claims)
        unclaimed_counts = Counter(claim.property_id for claim in batch.unclaimed)
        intrinsic_count = sum(1 for claim in batch.routed_claims if claim.route == "intrinsic")
        relational_count = sum(1 for claim in batch.routed_claims if claim.route == "relational")
        unclaimed_count = len(batch.unclaimed)
        claim_count = len(batch.claims)
        routed_count = intrinsic_count + relational_count
        return WikiCoverageReportDTO(
            raw_record_count=raw_record_count,
            candidate_count=len(batch.entities),
            claim_count=claim_count,
            routed_claim_count=routed_count,
            intrinsic_claim_count=intrinsic_count,
            relational_claim_count=relational_count,
            unclaimed_count=unclaimed_count,
            stub_node_count=stub_node_count,
            claim_routing_rate=_ratio(routed_count, claim_count),
            intrinsic_claim_rate=_ratio(intrinsic_count, claim_count),
            relational_claim_rate=_ratio(relational_count, claim_count),
            unclaimed_rate=_ratio(unclaimed_count, claim_count),
            top_properties=[{"property_id": key, "count": value} for key, value in property_counts.most_common(20)],
            top_unclaimed_properties=[
                {"property_id": key, "count": value} for key, value in unclaimed_counts.most_common(20)
            ],
        )


def _ratio(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value / total, 4)
