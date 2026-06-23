from pathlib import Path

from app.wiki_industry_pipeline.candidate_filter import WikiEntityCandidateFilter
from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO
from app.wiki_industry_pipeline.type_whitelist import WikidataTypeWhitelist


WHITELIST_PATH = Path("configs/industry_wiki/wikidata_type_whitelist.yaml")


def test_wikidata_type_whitelist_loads_all_industry_profile():
    whitelist = WikidataTypeWhitelist.load(WHITELIST_PATH, profile="all_industry")

    assert whitelist.type_qid_to_category["Q4830453"] == "Enterprise"
    assert whitelist.type_qid_to_category["Q783794"] == "Enterprise"
    assert whitelist.type_qid_to_category["Q2424752"] == "ProductModel"
    assert whitelist.property_to_category["P176"] == "ProductModel"
    assert "Q847017" in whitelist.excluded_type_qids


def test_all_industry_candidate_filter_uses_type_whitelist():
    candidate_filter = WikiEntityCandidateFilter.all_industry(WHITELIST_PATH)
    record = WikiDumpRecordDTO(
        entity_id="QPRODUCT",
        raw={
            "id": "QPRODUCT",
            "labels": {"en": {"language": "en", "value": "Example Product"}},
            "claims": {
                "P31": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "entity-type": "item",
                                    "numeric-id": 2424752,
                                    "id": "Q2424752",
                                },
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ]
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is not None
    assert candidate.candidate_categories == ["ProductModel"]
    assert candidate.matched_reasons == ["type:Q2424752"]


def test_all_industry_candidate_filter_rejects_blacklisted_types():
    candidate_filter = WikiEntityCandidateFilter.all_industry(WHITELIST_PATH)
    record = WikiDumpRecordDTO(
        entity_id="QSPORTSCLUB",
        raw={
            "id": "QSPORTSCLUB",
            "labels": {"en": {"language": "en", "value": "Example Sports Club"}},
            "claims": {
                "P31": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "entity-type": "item",
                                    "numeric-id": 847017,
                                    "id": "Q847017",
                                },
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ],
                "P176": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "entity-type": "item",
                                    "numeric-id": 1,
                                    "id": "Q1",
                                },
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ],
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None
