import bz2
import io
from pathlib import Path

from app.wiki_industry_pipeline.candidate_filter import WikiEntityCandidateFilter
from app.wiki_industry_pipeline import wikidata_reader
from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records


FIXTURE = Path("backend/tests/fixtures/wiki_industry/sample_wikidata_robotics.jsonl")


def test_wikidata_reader_streams_jsonl_records_with_limit():
    records = list(iter_wikidata_records(FIXTURE, limit=2))

    assert [record.entity_id for record in records] == ["Q1001", "Q2001"]
    assert records[0].source == "wikidata"
    assert records[0].raw["labels"]["en"]["value"] == "Acme Robotics"


def test_wikidata_reader_streams_remote_bz2_without_local_dump(monkeypatch):
    compressed = bz2.compress(
        b'[\n{"id":"QREMOTE1","labels":{"en":{"value":"Remote Enterprise"}}},\n'
        b'{"id":"QREMOTE2","labels":{"en":{"value":"Remote Product"}}}\n]\n'
    )

    def fake_urlopen(url, timeout):
        assert url == "https://example.test/latest-all.json.bz2"
        assert timeout == 60
        return io.BytesIO(compressed)

    monkeypatch.setattr(wikidata_reader.urllib.request, "urlopen", fake_urlopen)

    records = list(iter_wikidata_records("https://example.test/latest-all.json.bz2"))

    assert [record.entity_id for record in records] == ["QREMOTE1", "QREMOTE2"]
    assert records[0].raw["labels"]["en"]["value"] == "Remote Enterprise"


def test_wikidata_reader_remote_bz2_can_resume_from_cursor(monkeypatch):
    compressed = bz2.compress(
        b'[\n{"id":"QREMOTE1","labels":{"en":{"value":"Remote Enterprise"}}},\n'
        b'{"id":"QREMOTE2","labels":{"en":{"value":"Remote Product"}}}\n]\n'
    )

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()
            return False

    def fake_urlopen(request, timeout):
        assert timeout == 60
        if hasattr(request, "headers"):
            url = request.full_url
            range_header = request.headers.get("Range")
        else:
            url = request
            range_header = None
        assert url == "https://example.test/latest-all.json.bz2"
        if not range_header:
            return FakeResponse(compressed)
        prefix = "bytes="
        assert range_header.startswith(prefix)
        start_text, _, end_text = range_header[len(prefix) :].partition("-")
        start = int(start_text)
        end = int(end_text) if end_text else len(compressed) - 1
        return FakeResponse(compressed[start : end + 1])

    monkeypatch.setattr(wikidata_reader.urllib.request, "urlopen", fake_urlopen)

    cursor_holder = {}

    def capture_cursor(count, cursor):
        if count == 1:
            cursor_holder["value"] = cursor

    first = list(
        iter_wikidata_records(
            "https://example.test/latest-all.json.bz2",
            limit=1,
            cursor_callback=capture_cursor,
            cursor_interval=1,
        )
    )
    resumed = list(
        iter_wikidata_records(
            "https://example.test/latest-all.json.bz2",
            resume_cursor=cursor_holder["value"],
        )
    )

    assert [record.entity_id for record in first] == ["QREMOTE1"]
    assert [record.entity_id for record in resumed] == ["QREMOTE2"]


def test_candidate_filter_selects_robotics_company_by_property_and_keyword():
    records = list(iter_wikidata_records(FIXTURE))
    candidate_filter = WikiEntityCandidateFilter.default()

    candidate = candidate_filter.filter_record(records[0])

    assert candidate is not None
    assert candidate.entity_id == "Q1001"
    assert candidate.label == "艾克米机器人"
    assert candidate.labels["zh"] == "艾克米机器人"
    assert candidate.labels["en"] == "Acme Robotics"
    assert "Enterprise" in candidate.candidate_categories
    assert "property:P452" in candidate.matched_reasons
    assert "keyword:robotics" in candidate.matched_reasons


def test_candidate_filter_does_not_select_region_as_primary_candidate():
    records = list(iter_wikidata_records(FIXTURE))
    candidate_filter = WikiEntityCandidateFilter.default()

    candidate = candidate_filter.filter_record(records[2])

    assert candidate is None


def test_candidate_filter_does_not_select_enterprise_by_inception_only():
    candidate_filter = WikiEntityCandidateFilter.default()
    record = WikiDumpRecordDTO(
        entity_id="QONLY571",
        raw={
            "id": "QONLY571",
            "labels": {"en": {"language": "en", "value": "General concept"}},
            "descriptions": {"en": {"language": "en", "value": "abstract thing with a start date"}},
            "claims": {
                "P571": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"time": "+2000-01-01T00:00:00Z"},
                                "type": "time",
                            }
                        }
                    }
                ]
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None


def test_candidate_filter_does_not_select_enterprise_by_product_claim_only():
    candidate_filter = WikiEntityCandidateFilter.default()
    record = WikiDumpRecordDTO(
        entity_id="QONLY1056",
        raw={
            "id": "QONLY1056",
            "labels": {"en": {"language": "en", "value": "General publisher"}},
            "descriptions": {"en": {"language": "en", "value": "entity with a produced work"}},
            "claims": {
                "P1056": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"entity-type": "item", "numeric-id": 1, "id": "Q1"},
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ]
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None


def test_candidate_filter_does_not_select_enterprise_by_headquarters_only():
    candidate_filter = WikiEntityCandidateFilter.default()
    record = WikiDumpRecordDTO(
        entity_id="QONLY159",
        raw={
            "id": "QONLY159",
            "labels": {"en": {"language": "en", "value": "Administrative place"}},
            "descriptions": {"en": {"language": "en", "value": "place with a headquarters field"}},
            "claims": {
                "P159": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"entity-type": "item", "numeric-id": 2, "id": "Q2"},
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ]
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None


def test_candidate_filter_does_not_select_product_by_developer_only():
    candidate_filter = WikiEntityCandidateFilter.default()
    record = WikiDumpRecordDTO(
        entity_id="QONLY178",
        raw={
            "id": "QONLY178",
            "labels": {"en": {"language": "en", "value": "General dataset"}},
            "descriptions": {"en": {"language": "en", "value": "dataset maintained by an organization"}},
            "claims": {
                "P178": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"entity-type": "item", "numeric-id": 3, "id": "Q3"},
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ]
            },
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None


def test_all_industry_filter_does_not_use_robotics_keywords_as_candidate_gate():
    candidate_filter = WikiEntityCandidateFilter.all_industry()
    record = WikiDumpRecordDTO(
        entity_id="QKEYWORDONLY",
        raw={
            "id": "QKEYWORDONLY",
            "labels": {"en": {"language": "en", "value": "robotics overview"}},
            "descriptions": {"en": {"language": "en", "value": "article about automation"}},
            "claims": {},
        },
    )

    candidate = candidate_filter.filter_record(record)

    assert candidate is None


def test_all_industry_filter_selects_enterprise_by_business_type():
    candidate_filter = WikiEntityCandidateFilter.all_industry()
    record = WikiDumpRecordDTO(
        entity_id="QBUSINESS",
        raw={
            "id": "QBUSINESS",
            "labels": {"en": {"language": "en", "value": "Example Company"}},
            "descriptions": {"en": {"language": "en", "value": "manufacturing company"}},
            "claims": {
                "P31": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "entity-type": "item",
                                    "numeric-id": 4830453,
                                    "id": "Q4830453",
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
    assert candidate.candidate_categories == ["Enterprise"]
    assert candidate.matched_reasons == ["type:Q4830453"]


def test_filter_for_domain_uses_all_industry_profile():
    candidate_filter = WikiEntityCandidateFilter.for_domain("all_industry")

    assert candidate_filter.keywords == []


def test_candidate_filter_rejects_unrelated_entity():
    records = list(iter_wikidata_records(FIXTURE))
    candidate_filter = WikiEntityCandidateFilter.default()

    candidate = candidate_filter.filter_record(records[-1])

    assert candidate is None
