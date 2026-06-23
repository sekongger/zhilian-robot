from __future__ import annotations

from pathlib import Path

import yaml

from crawler.domain.errors import ConfigError
from crawler.domain.models import PipelineConfig, SourceConfig


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config file must be a mapping: {path}")
    return data


def load_sources(config_path: str | Path) -> list[SourceConfig]:
    raw = _read_yaml(Path(config_path))
    sources = raw.get("sources", [])
    if not isinstance(sources, list):
        raise ConfigError("sources must be a list")

    result: list[SourceConfig] = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("id", "")).strip()
        url = str(item.get("url", "")).strip()
        if not source_id or not url:
            continue
        result.append(
            SourceConfig(
                source_id=source_id,
                source_type=str(item.get("type", "rss")).strip() or "rss",
                name=str(item.get("name", source_id)).strip() or source_id,
                url=url,
                enabled=bool(item.get("enabled", True)),
                priority=int(item.get("priority", 100)),
                quality_score=float(item.get("quality_score", 0.5)),
                rate_limit_per_min=int(item.get("rate_limit_per_min", 20)),
                tags=[str(tag) for tag in item.get("tags", []) if str(tag).strip()],
                options=item.get("options", {}) if isinstance(item.get("options", {}), dict) else {},
            )
        )
    return sorted(result, key=lambda src: src.priority)


def load_pipeline_config(config_path: str | Path) -> PipelineConfig:
    raw = _read_yaml(Path(config_path))
    pipeline = raw.get("pipeline", {})
    if not isinstance(pipeline, dict):
        raise ConfigError("pipeline must be a mapping")

    return PipelineConfig(
        max_content_length=int(pipeline.get("max_content_length", 5000)),
        min_content_length=int(pipeline.get("min_content_length", 80)),
        dedup_similarity_threshold=float(pipeline.get("dedup_similarity_threshold", 0.9)),
        compress_max_chars=int(pipeline.get("compress_max_chars", 200)),
        ingest_retry_times=int(pipeline.get("ingest_retry_times", 2)),
        relevance_mode=str(pipeline.get("relevance_mode", "high_recall")),
        gray_mode=bool(pipeline.get("gray_mode", True)),
        schedule_hours=int(pipeline.get("schedule_hours", 4)),
    )
