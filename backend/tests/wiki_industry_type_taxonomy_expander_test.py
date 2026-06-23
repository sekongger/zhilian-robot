from pathlib import Path

import yaml

from app.wiki_industry_pipeline.type_taxonomy_expander import (
    WikidataSubclassDTO,
    expand_type_whitelist,
)


WHITELIST_PATH = Path("configs/industry_wiki/wikidata_type_whitelist.yaml")


def test_expand_type_whitelist_adds_p279_subclasses_and_preserves_metadata(tmp_path):
    output_path = tmp_path / "expanded_whitelist.yaml"
    client = _FakeSubclassClient(
        {
            "Q4830453": [
                WikidataSubclassDTO(
                    qid="Q1137109",
                    label_en="video game company",
                    description_en="company that develops or publishes video games",
                )
            ],
            "Q1137109": [
                WikidataSubclassDTO(
                    qid="Q210167",
                    label_en="video game publisher",
                    description_en="company that publishes video games",
                )
            ],
            "Q2424752": [
                WikidataSubclassDTO(
                    qid="Q15056995",
                    label_en="aircraft model",
                    description_en="specific model of aircraft",
                )
            ],
            "Q7397": [
                WikidataSubclassDTO(
                    qid="Q166142",
                    label_en="application",
                    description_en="computer software designed to perform tasks",
                )
            ],
        }
    )

    expanded = expand_type_whitelist(
        input_path=WHITELIST_PATH,
        output_path=output_path,
        profile="all_industry",
        max_depth=2,
        limit_per_seed=10,
        client=client,
    )

    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    enterprise_items = payload["profiles"]["all_industry"]["categories"]["Enterprise"]["include"]
    product_items = payload["profiles"]["all_industry"]["categories"]["ProductModel"]["include"]

    assert expanded.added_count >= 3
    assert _item_by_qid(enterprise_items, "Q1137109")["source"] == "wikidata_p279"
    assert _item_by_qid(enterprise_items, "Q210167")["depth"] == 2
    assert _item_by_qid(product_items, "Q15056995") is None
    assert _item_by_qid(product_items, "Q166142")["parent_qid"] == "Q7397"
    assert payload["profiles"]["all_industry"]["exclusions"]["Enterprise"]
    assert payload["profiles"]["all_industry"]["property_triggers"]["ProductModel"]


def test_expand_type_whitelist_skips_excluded_subclasses(tmp_path):
    output_path = tmp_path / "expanded_whitelist.yaml"
    client = _FakeSubclassClient(
        {
            "Q4830453": [
                WikidataSubclassDTO(
                    qid="Q847017",
                    label_en="sports club",
                    description_en="organization for sports",
                )
            ]
        }
    )

    expand_type_whitelist(
        input_path=WHITELIST_PATH,
        output_path=output_path,
        profile="all_industry",
        max_depth=1,
        client=client,
    )

    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    enterprise_items = payload["profiles"]["all_industry"]["categories"]["Enterprise"]["include"]

    assert _item_by_qid(enterprise_items, "Q847017") is None


def _item_by_qid(items, qid):
    return next((item for item in items if item["qid"] == qid), None)


class _FakeSubclassClient:
    def __init__(self, subclasses_by_parent):
        self.subclasses_by_parent = subclasses_by_parent

    def fetch_direct_subclasses(self, parent_qid, *, limit):
        return self.subclasses_by_parent.get(parent_qid, [])[:limit]
