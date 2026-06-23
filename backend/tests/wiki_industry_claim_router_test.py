from app.wiki_industry_pipeline.claim_router import WikiClaimRouter
from app.wiki_industry_pipeline.dto import WikiClaimDTO
from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema


def _router():
    schema = IndustryWikiRoutingSchema.load("configs/industry_wiki/IncIndustryWiki.routing.schema.yaml")
    return WikiClaimRouter(schema)


def test_claim_router_routes_intrinsic_company_claim():
    routed = _router().route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P571",
            value_literal="+2010-01-01T00:00:00Z",
            value_datatype="time",
        ),
        subject_category="Enterprise",
    )

    assert routed.route == "intrinsic"
    assert routed.module == "basic_profile"
    assert routed.property_name == "inception"


def test_claim_router_routes_enterprise_schema_properties():
    router = _router()

    official_name = router.route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P1448",
            value_literal="Acme Robotics Co., Ltd.",
            value_datatype="monolingualtext",
        ),
        subject_category="Enterprise",
    )
    website = router.route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P856",
            value_literal="https://acme.example",
            value_datatype="string",
        ),
        subject_category="Enterprise",
    )

    assert official_name.route == "intrinsic"
    assert official_name.property_name == "officialName"
    assert website.route == "intrinsic"
    assert website.property_name == "officialWebsite"


def test_claim_router_routes_enterprise_status_from_dissolved_date():
    routed = _router().route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P576",
            value_literal="+2025-01-01T00:00:00Z",
            value_datatype="time",
        ),
        subject_category="Enterprise",
    )

    assert routed.route == "intrinsic"
    assert routed.property_name == "status"


def test_claim_router_routes_relational_company_claim():
    routed = _router().route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P1056",
            value_id="Q2001",
            value_label="industrial robot arm",
        ),
        subject_category="Enterprise",
    )

    assert routed.route == "relational"
    assert routed.edge_type == "manufacturer"
    assert routed.target_type == "IncCore.ProductModel"
    assert routed.direction == "reverse"


def test_claim_router_routes_product_model_schema_properties():
    router = _router()
    routed = router.route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q2001",
            subject_label="industrial robot arm",
            property_id="P577",
            value_literal="+2024-01-01T00:00:00Z",
            value_datatype="time",
        ),
        subject_category="ProductModel",
    )

    assert routed.route == "intrinsic"
    assert routed.property_name == "publishDate"

    series = router.route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q2001",
            subject_label="industrial robot arm",
            property_id="P179",
            value_literal="Acme Arm Series",
            value_datatype="string",
        ),
        subject_category="ProductModel",
    )

    assert series.route == "intrinsic"
    assert series.property_name == "series"


def test_claim_router_routes_product_hierarchy_relation():
    routed = _router().route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q5001",
            subject_label="robot arm",
            property_id="P279",
            value_id="Q5000",
            value_label="robot equipment",
        ),
        subject_category="Product",
    )

    assert routed.route == "relational"
    assert routed.edge_type == "subclassOf"
    assert routed.target_type == "IncCore.Product"


def test_claim_router_marks_unknown_property_as_unclaimed():
    routed = _router().route(
        WikiClaimDTO(
            source="wikidata",
            subject_id="Q1001",
            subject_label="Acme Robotics",
            property_id="P999999",
        ),
        subject_category="Enterprise",
    )

    assert routed.route == "unclaimed"
    assert routed.route_reason == "no routing rule matched"
