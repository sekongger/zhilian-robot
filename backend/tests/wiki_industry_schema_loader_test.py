from pathlib import Path
import re
import yaml

from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema


SCHEMA_PATH = Path("configs/industry_wiki/IncIndustryWiki.routing.schema.yaml")
INCORE_SCHEMA_PATH = Path("IncCore_0422_最新.schema")


def test_schema_loader_routes_company_intrinsic_property():
    schema = IndustryWikiRoutingSchema.load(SCHEMA_PATH)

    rule = schema.route("Enterprise", "P571")

    assert rule.route == "intrinsic"
    assert rule.module == "basic_profile"
    assert rule.property_name == "inception"


def test_schema_loader_routes_company_product_relation():
    schema = IndustryWikiRoutingSchema.load(SCHEMA_PATH)

    rule = schema.route("Enterprise", "P1056")

    assert rule.route == "relational"
    assert rule.module == "product_portfolio"
    assert rule.edge_type == "manufacturer"
    assert rule.target_type == "IncCore.ProductModel"
    assert rule.direction == "reverse"


def test_schema_loader_returns_unclaimed_for_unknown_property():
    schema = IndustryWikiRoutingSchema.load(SCHEMA_PATH)

    rule = schema.route("Enterprise", "P999999")

    assert rule.route == "unclaimed"
    assert rule.module is None
    assert rule.edge_type is None


def test_routing_schema_targets_existing_incore_0422_types_and_relations():
    schema_text = INCORE_SCHEMA_PATH.read_text(encoding="utf-8")
    type_names = set(re.findall(r"^([A-Za-z][A-Za-z0-9_]*)\(.+\):\s+(?:EntityType|EventType|ConceptType|IndexType)", schema_text, re.M))
    relation_names = set(re.findall(r"^\s{4}([A-Za-z][A-Za-z0-9_]*)\(.+\):\s+[A-Za-z][A-Za-z0-9_]*", schema_text, re.M))
    payload = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))

    for category, category_payload in payload["categories"].items():
        assert category in type_names
        target_type = category_payload["target_type"].split(".")[-1]
        assert target_type in type_names
        for module_payload in category_payload["modules"].values():
            target = module_payload.get("target_type")
            if target:
                assert target.split(".")[-1] in type_names
            edge = module_payload.get("edge")
            if edge:
                assert edge in relation_names
            for configured_edge in (module_payload.get("edges") or {}).values():
                assert configured_edge in relation_names
