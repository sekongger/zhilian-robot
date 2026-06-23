from app.news_graph_pipeline.runner import NewsGraphPipelineRunner


class FakeAnchorExporter:
    def load_anchors(self, *, limit):
        return []


class FakeGraphiti:
    def sync_anchors(self, anchors):
        return {"synced": len(anchors), "skipped": 0}


class FakeEntityLinker:
    def __init__(self):
        self.graphiti = FakeGraphiti()


def test_runner_records_mcp_smoke_test_result(monkeypatch, tmp_path):
    class FakeService:
        def query_recommended_news_candidates(self, *, since_hours, limit):
            return {"query": "recommended_news_candidates", "items": [{"title": "资讯"}], "warnings": []}

    monkeypatch.setattr("app.news_graph_mcp.service.NewsGraphQueryService", lambda: FakeService())
    runner = NewsGraphPipelineRunner(anchor_exporter=FakeAnchorExporter(), entity_linker=FakeEntityLinker())

    report = runner.run(
        group_id=None,
        sync_anchors=False,
        link_entities=False,
        output_dir=tmp_path,
        mcp_smoke_test=True,
    )

    assert report["mcp_smoke_test"]["status"] == "success"
    assert report["mcp_smoke_test"]["item_count"] == 1
    assert report["stages"]["mcp_smoke_test"]["query"] == "recommended_news_candidates"

