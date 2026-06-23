"""Runners for the IncCore fusion pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.incore_fusion_pipeline.runners.fusion_pipeline_runner import FusionPipelineRunner
    from app.incore_fusion_pipeline.runners.graphiti_news_fusion_runner import GraphitiNewsFusionRunner
    from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner

__all__ = ["FusionPipelineRunner", "GraphitiNewsFusionRunner", "WikidataV2FusionRunner"]


def __getattr__(name: str):
    if name == "FusionPipelineRunner":
        from app.incore_fusion_pipeline.runners.fusion_pipeline_runner import FusionPipelineRunner

        return FusionPipelineRunner
    if name == "GraphitiNewsFusionRunner":
        from app.incore_fusion_pipeline.runners.graphiti_news_fusion_runner import GraphitiNewsFusionRunner

        return GraphitiNewsFusionRunner
    if name == "WikidataV2FusionRunner":
        from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner

        return WikidataV2FusionRunner
    raise AttributeError(name)
