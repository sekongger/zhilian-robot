from openks.common.registry import get_module_spec, list_kg_modules


def test_registry_exposes_core_openks_modules():
    modules = list_kg_modules()
    module_names = [item.name for item in modules]

    assert "base_kg" in module_names
    assert "news_kg" in module_names
    assert "report_kg" in module_names
    assert "industry_chain" in module_names
    assert "event_kg" in module_names
    assert "industry_network" in module_names


def test_registry_returns_owner_and_stage():
    spec = get_module_spec("news_kg")

    assert spec is not None
    assert spec.owner == "楼彦炜"
    assert spec.stage == "fact"


def test_registry_returns_updated_technology_foresight_owner_and_cognition_titles():
    foresight = get_module_spec("technology_foresight")
    industry_chain = get_module_spec("industry_chain")
    event_kg = get_module_spec("event_kg")
    industry_network = get_module_spec("industry_network")

    assert foresight is not None
    assert foresight.owner == "林辉、徐梓毓"
    assert industry_chain is not None
    assert industry_chain.title == "产业链图谱库"
    assert event_kg is not None
    assert event_kg.stage == "fact"
    assert industry_network is not None
    assert industry_network.stage == "fact"
