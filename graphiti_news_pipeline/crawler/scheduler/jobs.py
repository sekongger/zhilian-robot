from __future__ import annotations

from crawler.domain.models import PipelineConfig


def default_schedule_hours(config: PipelineConfig) -> int:
    return max(1, int(config.schedule_hours))

