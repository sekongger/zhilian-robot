"""Orchestration layer for the separated news graph pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.news_graph_pipeline.anchor_exporter import CommonSenseAnchorExporter
from app.news_graph_pipeline.dto import NewsGraphRunReportDTO
from app.news_graph_pipeline.entity_linker import EntityLinker


class NewsGraphPipelineRunner:
    """Run anchor sync and entity linking against Graphiti without merging into common graph."""

    def __init__(
        self,
        *,
        anchor_exporter: Optional[CommonSenseAnchorExporter] = None,
        entity_linker: Optional[EntityLinker] = None,
    ) -> None:
        self.anchor_exporter = anchor_exporter or CommonSenseAnchorExporter()
        self.entity_linker = entity_linker or EntityLinker()

    def run(
        self,
        *,
        group_id: str | None,
        sync_anchors: bool,
        link_entities: bool,
        clear_news_group: bool = False,
        anchor_limit: int = 5000,
        entity_limit: int = 1000,
        output_dir: str | Path,
        crawler_summary: dict[str, Any] | None = None,
        mcp_smoke_test: bool = False,
    ) -> dict[str, Any]:
        run_id = datetime.now(timezone.utc).strftime("news_graph_%Y%m%d%H%M%S")
        output_path = Path(output_dir).expanduser().resolve()
        stages: dict[str, Any] = {}
        warnings: list[str] = []

        if clear_news_group:
            if not group_id:
                raise RuntimeError("group_id is required for clear_news_group")
            stages["clear_news_group"] = self.entity_linker.graphiti.clear_news_group(group_id=group_id)

        anchors = []
        if sync_anchors or link_entities:
            anchors = self.anchor_exporter.load_anchors(limit=anchor_limit)
            stages["anchor_export"] = {"loaded": len(anchors)}

        if sync_anchors and not link_entities:
            stages["anchor_sync"] = self.entity_linker.graphiti.sync_anchors(anchors)

        if link_entities:
            if not group_id:
                raise RuntimeError("group_id is required for --link-entities unless --run-crawler derives one")
            link_result = self.entity_linker.link_group(group_id=group_id, anchors=anchors, limit=entity_limit)
            stages["anchor_sync"] = link_result["anchor_sync"]
            stages["entity_link"] = {
                **link_result["write_stats"],
                "entity_count": link_result["entity_count"],
                "decision_count": len(link_result["decisions"]),
            }
            self._write_decisions(output_path / "link_decisions.json", link_result["decisions"])

        smoke_payload = None
        if mcp_smoke_test:
            smoke_payload = self._run_mcp_smoke_test()
            stages["mcp_smoke_test"] = smoke_payload

        report = NewsGraphRunReportDTO(
            run_id=run_id,
            group_id=group_id,
            stages=stages,
            output_dir=str(output_path),
            warnings=warnings,
            crawler_summary=crawler_summary,
            mcp_smoke_test=smoke_payload,
        )
        return self._model_dump(report)

    def _write_decisions(self, path: Path, decisions: list[Any]) -> None:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._model_dump(item) for item in decisions]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    def _run_mcp_smoke_test(self) -> dict[str, Any]:
        try:
            from app.news_graph_mcp.service import NewsGraphQueryService

            payload = NewsGraphQueryService().query_recommended_news_candidates(since_hours=24, limit=3)
            return {
                "status": "success",
                "query": payload.get("query"),
                "item_count": len(payload.get("items") or []),
                "warnings": payload.get("warnings") or [],
            }
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    @staticmethod
    def _model_dump(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        return value
