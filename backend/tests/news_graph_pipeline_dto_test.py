from app.news_graph_pipeline.dto import (
    CommonSenseAnchorDTO,
    EntityLinkDecisionDTO,
    NewsGraphRunReportDTO,
)


def test_news_graph_pipeline_dtos_keep_anchor_link_and_report_contracts():
    anchor = CommonSenseAnchorDTO(
        anchor_id="Enterprise:wiki:Q20716",
        type_name="Enterprise",
        name="三星",
        aliases=["Samsung", "三星集团"],
        description="韩国综合性企业集团。",
        source_graph="incore_common_neo4j",
        source_version="wikidata_v2_202606",
        properties={"country": "韩国"},
    )
    decision = EntityLinkDecisionDTO(
        news_entity_id="entity-1",
        news_entity_name="三星集团",
        candidate_anchor_id=anchor.anchor_id,
        match_score=0.95,
        match_method="exact_alias",
        decision="refersTo",
        reason="alias exact match",
        group_id="crawl_202606210001",
    )
    report = NewsGraphRunReportDTO(
        run_id="news_graph_202606210001",
        group_id="crawl_202606210001",
        stages={
            "anchor_sync": {"synced": 1},
            "entity_link": {"refersTo": 1, "candidateRefersTo": 0, "unresolved": 0},
        },
        output_dir="/tmp/news_graph_202606210001",
        warnings=[],
    )

    assert anchor.anchor_id == "Enterprise:wiki:Q20716"
    assert anchor.aliases == ["Samsung", "三星集团"]
    assert decision.decision == "refersTo"
    assert decision.match_score == 0.95
    assert report.stages["entity_link"]["refersTo"] == 1

