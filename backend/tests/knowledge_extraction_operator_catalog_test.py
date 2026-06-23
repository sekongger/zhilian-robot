from app.knowledge_extraction_operators import get_operator, get_operator_catalog


def test_operator_catalog_exposes_core_executable_operators():
    catalog = get_operator_catalog()
    names = {spec.name for spec in catalog}

    assert {
        "source_record_map",
        "event_enrich",
        "entity_resolve",
        "event_resolve",
        "fusion_graph_build",
        "graph_import",
    }.issubset(names)


def test_operator_spec_contains_agent_facing_metadata():
    operator = get_operator("source_record_map")
    spec = operator.spec

    assert spec.name == "source_record_map"
    assert spec.stage == "normalize"
    assert spec.agent_callable is True
    assert spec.side_effect is False
    assert spec.input_type == "SourceRecordListDTO"
    assert spec.output_type == "NormalizedBatchDTO"
    assert "SourceMapper" in spec.implementation_ref
