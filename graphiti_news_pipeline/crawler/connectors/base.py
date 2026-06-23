from __future__ import annotations

from abc import ABC, abstractmethod

from crawler.domain.models import ArticleRecord, SourceConfig


class BaseConnector(ABC):
    @abstractmethod
    def fetch(self, source: SourceConfig, since_hours: int, max_items: int) -> list[ArticleRecord]:
        """Fetch records from a source."""

