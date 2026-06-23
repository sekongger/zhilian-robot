from app.wiki_industry_pipeline.dto import (
    RoutedClaimDTO,
    WikiEntityCandidateDTO,
    WikiGraphBuildBatchDTO,
)
from app.wiki_industry_pipeline.graph_mapper import WikiIndustryGraphMapper


def test_graph_mapper_writes_intrinsic_properties_relations_and_stub_nodes():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-test",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q1001",
                label="Acme Robotics",
                candidate_categories=["Enterprise"],
            )
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q1001",
                subject_label="Acme Robotics",
                subject_category="Enterprise",
                property_id="P571",
                route="intrinsic",
                module="basic_profile",
                property_name="inception",
                value_literal="+2010-01-01T00:00:00Z",
            ),
            RoutedClaimDTO(
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
            ),
        ],
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)

    company = graph_batch.entity_nodes[0]
    product_stub = graph_batch.entity_nodes[1]
    edge = graph_batch.edges[0]

    assert company.type_name == "Enterprise"
    assert company.graph_id == "Enterprise:wiki:Q1001"
    assert company.properties["inception"] == "2010-01-01"
    assert "externalId" not in company.properties
    assert product_stub.type_name == "ProductModel"
    assert product_stub.properties["_semanticType"] == "stub"
    assert edge.subject_graph_id == "ProductModel:wiki:Q2001"
    assert edge.predicate == "manufacturer"
    assert edge.object_graph_id == "Enterprise:wiki:Q1001"


def test_graph_mapper_maps_candidate_and_claims_to_incore_v2_style_fields():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-schema-map",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q1001",
                label="艾克米机器人",
                labels={"zh": "艾克米机器人", "en": "Acme Robotics"},
                aliases=["Acme", "艾克米"],
                description="工业机器人制造企业",
                candidate_categories=["Enterprise"],
            ),
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q2001",
                label="工业机器人手臂",
                labels={"zh": "工业机器人手臂", "en": "Industrial robot arm"},
                aliases=["robot arm"],
                description="工业机器人产品型号",
                candidate_categories=["ProductModel"],
            ),
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q1001",
                subject_label="艾克米机器人",
                subject_category="Enterprise",
                property_id="P1448",
                route="intrinsic",
                module="basic_profile",
                property_name="officialName",
                value_literal="Acme Robotics Co., Ltd.",
            ),
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q1001",
                subject_label="艾克米机器人",
                subject_category="Enterprise",
                property_id="P856",
                route="intrinsic",
                module="basic_profile",
                property_name="officialWebsite",
                value_literal="https://acme.example",
            ),
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q2001",
                subject_label="工业机器人手臂",
                subject_category="ProductModel",
                property_id="P179",
                route="intrinsic",
                module="product_description",
                property_name="series",
                value_literal="Acme Arm Series",
            ),
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q2001",
                subject_label="工业机器人手臂",
                subject_category="ProductModel",
                property_id="P577",
                route="intrinsic",
                module="product_description",
                property_name="publishDate",
                value_literal="+2024-01-01T00:00:00Z",
            ),
        ],
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
    enterprise = next(node for node in graph_batch.entity_nodes if node.graph_id == "Enterprise:wiki:Q1001")
    product_model = next(node for node in graph_batch.entity_nodes if node.graph_id == "ProductModel:wiki:Q2001")

    assert enterprise.properties["name"] == "艾克米机器人"
    assert enterprise.properties["officialName"] == "Acme Robotics Co., Ltd."
    assert enterprise.properties["nameEn"] == ["Acme Robotics"]
    assert enterprise.properties["officialWebsite"] == ["https://acme.example"]
    assert enterprise.properties["alias"] == ["Acme", "艾克米"]
    assert enterprise.properties["mainBusiness"] == "工业机器人制造企业"
    assert enterprise.properties["businessScope"] == "工业机器人制造企业"
    assert product_model.properties["nameEn"] == ["Industrial robot arm"]
    assert product_model.properties["series"] == "Acme Arm Series"
    assert product_model.properties["publishDate"] == "2024-01-01"
    assert product_model.properties["productLifecycleStatus"] == "launched"


def test_graph_mapper_maps_enterprise_status_from_dissolved_claim():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-status-map",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q3002",
                label="停业企业",
                labels={"zh": "停业企业", "en": "Inactive Company"},
                description="已经终止运营的企业",
                candidate_categories=["Enterprise"],
            )
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q3002",
                subject_label="停业企业",
                subject_category="Enterprise",
                property_id="P576",
                route="intrinsic",
                module="basic_profile",
                property_name="status",
                value_literal="+2025-01-01T00:00:00Z",
            ),
        ],
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
    enterprise = next(node for node in graph_batch.entity_nodes if node.graph_id == "Enterprise:wiki:Q3002")

    assert enterprise.properties["status"] == "inactive"


def test_graph_mapper_maps_product_hierarchy_relation():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-product-hierarchy",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q5001",
                label="机器人手臂",
                labels={"zh": "机器人手臂", "en": "robot arm"},
                candidate_categories=["Product"],
            )
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q5001",
                subject_label="机器人手臂",
                subject_category="Product",
                property_id="P279",
                route="relational",
                module="hierarchy",
                target_type="IncCore.Product",
                edge_type="subclassOf",
                value_id="Q5000",
                value_label="robot equipment",
            ),
        ],
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
    product = next(node for node in graph_batch.entity_nodes if node.graph_id == "Product:wiki:Q5001")
    product_parent = next(node for node in graph_batch.entity_nodes if node.graph_id == "Product:wiki:Q5000")
    edge = graph_batch.edges[0]

    assert product.type_name == "Product"
    assert product_parent.type_name == "Product"
    assert edge.subject_graph_id == "Product:wiki:Q5001"
    assert edge.predicate == "subclassOf"
    assert edge.object_graph_id == "Product:wiki:Q5000"


def test_graph_mapper_uses_entity_context_for_stub_node_labels():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-stub-context",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q1001",
                label="艾克米机器人",
                labels={"zh": "艾克米机器人", "en": "Acme Robotics"},
                candidate_categories=["Enterprise"],
            )
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q1001",
                subject_label="艾克米机器人",
                subject_category="Enterprise",
                property_id="P159",
                route="relational",
                module="region_presence",
                target_type="IncCore.Region",
                edge_type="region",
                value_id="Q3001",
            ),
        ],
        entity_contexts={
            "Q3001": {
                "label": "深圳",
                "labels": {"zh": "深圳", "en": "Shenzhen"},
                "aliases": ["鹏城"],
                "description": "中国广东省城市",
            }
        },
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
    region = next(node for node in graph_batch.entity_nodes if node.graph_id == "Region:wiki:Q3001")

    assert region.name == "深圳"
    assert region.properties["name"] == "深圳"
    assert region.properties["nameEn"] == ["Shenzhen"]
    assert region.properties["alias"] == ["鹏城"]
    assert region.properties["description"] == "中国广东省城市"


def test_graph_mapper_uses_claim_derived_context_for_product_stub_fields():
    batch = WikiGraphBuildBatchDTO(
        source_batch_id="wiki-product-stub-context",
        entities=[
            WikiEntityCandidateDTO(
                source="wikidata",
                entity_id="Q2001",
                label="工业机器人手臂",
                labels={"zh": "工业机器人手臂", "en": "industrial robot arm"},
                candidate_categories=["ProductModel"],
            )
        ],
        routed_claims=[
            RoutedClaimDTO(
                source="wikidata",
                subject_id="Q2001",
                subject_label="工业机器人手臂",
                subject_category="ProductModel",
                property_id="P31",
                route="relational",
                module="standard_product",
                target_type="IncCore.Product",
                edge_type="belongsToProduct",
                value_id="Q2424752",
            ),
        ],
        entity_contexts={
            "Q2424752": {
                "label": "工业机器人",
                "labels": {"zh": "工业机器人", "en": "Industrial robot"},
                "aliases": ["robotics equipment"],
                "description": "用于工业自动化的标准机器人产品",
                "officialName": "Industrial Robot",
                "shortName": "IR",
            }
        },
    )

    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
    product = next(node for node in graph_batch.entity_nodes if node.graph_id == "Product:wiki:Q2424752")

    assert product.name == "工业机器人"
    assert product.properties["name"] == "工业机器人"
    assert product.properties["officialName"] == "Industrial Robot"
    assert product.properties["shortName"] == "IR"
    assert product.properties["nameEn"] == ["Industrial robot"]
    assert product.properties["alias"] == ["robotics equipment"]
    assert product.properties["description"] == "用于工业自动化的标准机器人产品"
