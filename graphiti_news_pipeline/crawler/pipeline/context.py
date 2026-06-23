from __future__ import annotations

from dataclasses import dataclass

from crawler.domain.models import PipelineConfig, SourceConfig
from crawler.services.compression_service import LLMCompressor
from crawler.services.ingest_service import GraphitiIngestClient
from crawler.storage.repositories import ArticleRepository


@dataclass(slots=True)
class PipelineContext:
    config: PipelineConfig
    sources: list[SourceConfig]
    repository: ArticleRepository
    compressor: LLMCompressor
    ingest_client: GraphitiIngestClient

