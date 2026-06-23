from pathlib import Path


def test_materialize_bridge_batch_writes_company_document_product(monkeypatch, tmp_path):
    from app.openspg_demo import graph_materializer

    batch_file = tmp_path / "batch.jsonl"
    batch_file.write_text(
        "\n".join(
            [
                (
                    '{"doc_id":"doc_1","title":"神东煤炭成功应用自行走全场景大件焊接机器人",'
                    '"summary":"焊接机器人效率提升","content":"神东煤炭设备维修中心应用焊接机器人，'
                    '并与宇树科技合作推进具身智能。","source_name":"rss","source_url":"https://example.com/1",'
                    '"publish_time":"2026-03-09T13:00:00+00:00","crawl_time":"2026-03-09T13:10:00+00:00"}'
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    captured = {"vertices": [], "edges": []}

    async def fake_get_project_namespace(*, project_id: int, openspg_base_url: str):
        return "zhilian"

    async def fake_upsert_vertices(*, project_id: int, openspg_base_url: str, vertices):
        captured["vertices"].extend(vertices)
        return {"success": True}

    async def fake_upsert_edges(*, project_id: int, openspg_base_url: str, edges):
        captured["edges"].extend(edges)
        return {"success": True}

    monkeypatch.setattr(graph_materializer, "_get_project_namespace", fake_get_project_namespace)
    monkeypatch.setattr(graph_materializer, "_upsert_vertices", fake_upsert_vertices)
    monkeypatch.setattr(graph_materializer, "_upsert_edges", fake_upsert_edges)

    result = graph_materializer.materialize_bridge_batch(
        batch_file_path=str(batch_file),
        project_id=1,
    )

    assert result["status"] == "success"
    vertex_types = {(item["type"], item["id"]) for item in captured["vertices"]}
    assert ("zhilian.Document", "doc_1") in vertex_types
    assert any(item["type"] == "zhilian.Company" for item in captured["vertices"])
    assert any(item["type"] == "zhilian.Product" for item in captured["vertices"])
    assert any(item["label"] == "mentionsCompany" for item in captured["edges"])
    assert any(item["label"] == "mentionsProduct" for item in captured["edges"])


def test_extract_entities_normalizes_company_and_product_names():
    from app.openspg_demo.graph_materializer import _extract_companies, _extract_products

    title = "中电信量子严正声明，称与量子通信手机样品 REED ONE GK5 无任何关联"
    content = "网传中国电信联合国盾量子发布了 REED ONE GK5 量子通信手机，中电信量子表示该信息不实。"

    companies = _extract_companies(title, content)
    products = _extract_products(title, content)

    assert "中国电信" in companies or "中电信量子" in companies or "中电信量子集团" in companies
    assert not any("的手机产品与" in item for item in companies)
    assert any("REED ONE GK5" in item for item in products)


def test_extract_companies_filters_generic_company_aliases():
    from app.openspg_demo.graph_materializer import _extract_companies

    title = "获近亿元融资，一家AI公司的两周转型小龙虾实战故事"
    content = "NoDesk AI 创始人宋健和他的创业公司在两周内完成转型，控股公司同步推进新产品发布。"

    companies = _extract_companies(title, content)

    assert "一家AI公司" not in companies
    assert "他的创业公司" not in companies
    assert "控股公司" not in companies


def test_extract_entities_from_stable_demo_sample():
    from app.openspg_demo.graph_materializer import _extract_companies, _extract_products, _extract_techs

    title = "智链机器人联合宇树科技发布 FlexArm 协作机械臂，升级具身智能产线"
    content = "智链机器人将与宇树科技共同推进具身智能、机器视觉和协作机械臂在柔性制造中的落地。"

    companies = _extract_companies(title, content)
    products = _extract_products(title, content)
    techs = _extract_techs(title, content)

    assert "智链机器人" in companies
    assert "宇树科技" in companies
    assert any("FlexArm 协作机械臂" in item or "协作机械臂" in item for item in products)
    assert "具身智能" in techs
    assert "机器视觉" in techs


def test_extract_entities_from_stable_demo_sample_filters_action_phrases():
    from app.openspg_demo.graph_materializer import _extract_companies, _extract_products

    title = "智链机器人携手先导智能发布 RoboOS 控制平台"
    content = "RoboOS 控制平台进一步强化路径规划、控制器和机器视觉能力，面向机器人产线调度。"

    companies = _extract_companies(title, content)
    products = _extract_products(title, content)

    assert "智链机器人" in companies
    assert "先导智能" in companies
    assert "智链机器人携手先导智能" not in companies
    assert "面向机器人" not in companies
    assert any("RoboOS" in item for item in products)
    assert "智链机器人" not in products
