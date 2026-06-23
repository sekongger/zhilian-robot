from pathlib import Path

from app.wiki_industry_pipeline.candidate_filter import WikiEntityCandidateFilter
from app.wiki_industry_pipeline.claim_extractor import WikiClaimExtractor
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records


FIXTURE = Path("backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl")


def test_claim_extractor_handles_entity_and_time_values():
    record = next(iter_wikidata_records(FIXTURE))
    candidate = WikiEntityCandidateFilter.default().filter_record(record)

    claims = WikiClaimExtractor().extract(candidate)
    claims_by_property = {claim.property_id: claim for claim in claims}

    assert claims_by_property["P1056"].value_id == "Q2001"
    assert claims_by_property["P571"].value_literal == "+2010-01-01T00:00:00Z"
    assert claims_by_property["P571"].value_datatype == "time"


def test_claim_extractor_skips_claims_without_datavalue():
    candidate = WikiEntityCandidateFilter.default().filter_record(next(iter_wikidata_records(FIXTURE)))
    candidate.claims["P999"] = [{"mainsnak": {}}]

    claims = WikiClaimExtractor().extract(candidate)

    assert all(claim.property_id != "P999" for claim in claims)
