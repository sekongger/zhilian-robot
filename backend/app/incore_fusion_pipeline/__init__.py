"""IncCore 大图融合层 pipeline 包。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.incore_fusion_pipeline.runners.fusion_pipeline_runner import FusionPipelineRunner

__all__ = ["FusionPipelineRunner"]


def __getattr__(name: str):
    if name == "FusionPipelineRunner":
        from app.incore_fusion_pipeline.runners.fusion_pipeline_runner import FusionPipelineRunner

        return FusionPipelineRunner
    raise AttributeError(name)
