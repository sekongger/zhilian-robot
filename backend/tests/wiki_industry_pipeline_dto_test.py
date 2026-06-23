from pydantic import ValidationError

from app.wiki_industry_pipeline.dto import (
    RoutedClaimDTO,
    WikiClaimDTO,
    WikiEntityCandidateDTO,
    WikiGraphBuildBatchDTO,
)


def test_wiki_industry_dtos_have_stable_defaults():
    candidate = WikiEntityCandidateDTO(
        source="wikidata",
        entity_id="Q1001",
        label="Acme Robotics",
    )

    assert candidate.aliases == []
    assert candidate.claims == {}
    assert candidate.matched_reasons == []
    assert candidate.candidate_categories == []


def test_routed_claim_accepts_known_route_values():
    claim = RoutedClaimDTO(
        source="wikidata",
        subject_id="Q1001",
        subject_label="Acme Robotics",
        subject_category="Enterprise",
        property_id="P1056",
        route="relational",
        module="product_portfolio",
        target_type="IncCore.ProductModel",
        edge_type="manufacturer",
        direction="reverse",
        value_id="Q2001",
        value_label="industrial robot arm",
    )

    assert claim.route == "relational"
    assert claim.edge_type == "manufacturer"
    assert claim.direction == "reverse"


def test_routed_claim_rejects_unknown_route_values():
    try:
        RoutedClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            subject_category="Enterprise",
            property_id="P999",
            route="random",
        )
    except ValidationError:
        return

    raise AssertionError("RoutedClaimDTO should reject unsupported route values")


def test_graph_build_batch_groups_entities_claims_and_unclaimed():
    claim = WikiClaimDTO(
        source="wikidata",
        subject_id="Q1001",
        subject_label="Acme Robotics",
        property_id="P999",
    )
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="batch-001",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q1001",
                label="Acme Robotics",
            )
        ],
        claims=[claim],
        unclaimed=[claim],
    )

    assert len(batch.entities) == 1
    assert len(batch.claims) == 1
    assert len(batch.unclaimed) == 1
