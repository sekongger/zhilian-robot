class CrawlerError(Exception):
    """Base crawler error."""


class ConfigError(CrawlerError):
    """Configuration load/validation error."""


class CompressionError(CrawlerError):
    """Compression call failed."""


class IngestError(CrawlerError):
    """Graphiti ingest failed."""

