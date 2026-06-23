import json
import re

from app.wiki_industry_pipeline.wikidata_fetcher import (
    WikidataOnlineFetcher,
    _keyword_regex,
    load_seed_config,
    write_records_jsonl,
)


def test_online_fetcher_searches_fetches_and_expands_linked_entities(tmp_path):
    client = _FakeWikidataClient()
    fetcher = WikidataOnlineFetcher(client=client)

    records = fetcher.fetch_records(
        keywords_by_lang={"en": ["robotics"]},
        seed_qids=["Q1001"],
        search_limit_per_term=1,
        max_entities=4,
        expand_depth=1,
        sparql_limit=1,
    )

    assert [record.entity_id for record in records] == ["Q1001", "Q2001"]
    assert records[0].raw["labels"]["en"]["value"] == "Acme Robotics"
    assert records[1].raw["labels"]["en"]["value"] == "industrial robot arm"
    assert client.calls[0][1]["format"] == "json"
    assert any(call[1].get("action") == "wbsearchentities" for call in client.calls)
    assert any(call[1].get("action") == "wbgetentities" for call in client.calls)


def test_seed_config_loader_and_jsonl_writer(tmp_path):
    seed_file = tmp_path / "seed.yaml"
    seed_file.write_text(
        """
domain: robotics
keywords:
  en:
    - robotics
  zh:
    - 机器人
seed_qids:
  Enterprise:
    - Q1001
""",
        encoding="utf-8",
    )

    seed_config = load_seed_config(seed_file)
    records = WikidataOnlineFetcher(client=_FakeWikidataClient()).fetch_records(
        keywords_by_lang=seed_config.keywords_by_lang,
        seed_qids=seed_config.seed_qids,
        search_limit_per_term=1,
        max_entities=2,
        expand_depth=0,
        sparql_limit=0,
    )
    output = tmp_path / "wikidata.jsonl"

    write_records_jsonl(records, output)
    payloads = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert seed_config.domain == "robotics"
    assert seed_config.seed_qids == ["Q1001"]
    assert payloads[0]["id"] == "Q1001"


def test_keyword_regex_uses_word_boundaries_for_ascii_terms():
    pattern = _keyword_regex(["lidar", "工业机器人"])

    assert re.search(pattern, "lidar sensor")
    assert re.search(pattern, "工业机器人")
    assert not re.search(pattern, "solidarity")


class _FakeWikidataClient:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, headers=None, timeout=None):
        self.calls.append((url, dict(params)))
        if "query" in params:
            return _FakeResponse(
                {
                    "results": {
                        "bindings": [
                            {"item": {"value": "http://www.wikidata.org/entity/Q1001"}},
                        ]
                    }
                }
            )
        if params["action"] == "wbsearchentities":
            return _FakeResponse({"search": [{"id": "Q1001", "label": "Acme Robotics"}]})
        ids = str(params["ids"]).split("|")
        return _FakeResponse({"entities": {qid: _entity(qid) for qid in ids if _entity(qid)}})


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _entity(qid):
    if qid == "Q1001":
        return {
            "id": "Q1001",
            "labels": {"en": {"language": "en", "value": "Acme Robotics"}},
            "aliases": {},
            "descriptions": {"en": {"language": "en", "value": "robotics company"}},
            "claims": {
                "P1056": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"entity-type": "item", "numeric-id": 2001, "id": "Q2001"},
                                "type": "wikibase-entityid",
                            }
                        }
                    }
                ]
            },
            "sitelinks": {},
        }
    if qid == "Q2001":
        return {
            "id": "Q2001",
            "labels": {"en": {"language": "en", "value": "industrial robot arm"}},
            "aliases": {},
            "descriptions": {"en": {"language": "en", "value": "robot product"}},
            "claims": {},
            "sitelinks": {},
        }
    return None
