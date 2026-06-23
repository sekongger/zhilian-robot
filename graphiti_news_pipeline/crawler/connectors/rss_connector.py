from __future__ import annotations

import logging

import feedparser

from crawler.connectors.base import BaseConnector
from crawler.domain.enums import ArticleStatus
from crawler.domain.models import ArticleRecord, SourceConfig
from crawler.services.canonical_url_service import canonicalize_url
from crawler.utils.hash_utils import build_article_id
from crawler.utils.text_utils import normalize_text
from crawler.utils.time_utils import is_within_hours, parse_datetime_to_utc, utc_now

logger = logging.getLogger(__name__)


class RSSConnector(BaseConnector):
    def fetch(self, source: SourceConfig, since_hours: int, max_items: int) -> list[ArticleRecord]:
        parsed = feedparser.parse(source.url)
        if parsed.bozo:
            logger.warning("RSS parse warning: source=%s error=%s", source.source_id, parsed.get("bozo_exception"))

        records: list[ArticleRecord] = []
        for entry in parsed.entries[:max_items]:
            title = normalize_text(getattr(entry, "title", "") or "")
            if not title:
                continue

            raw_link = getattr(entry, "link", "") or ""
            canonical_url = canonicalize_url(raw_link)
            if not canonical_url:
                logger.warning("RSS item skipped because original article url is missing: source=%s title=%s", source.source_id, title)
                continue

            content_raw = ""
            if getattr(entry, "summary", None):
                content_raw = str(entry.summary)
            elif getattr(entry, "description", None):
                content_raw = str(entry.description)
            elif getattr(entry, "content", None):
                try:
                    content_raw = str(entry.content[0].value)
                except Exception:
                    content_raw = str(entry.content)
            content_raw = normalize_text(content_raw)
            if not content_raw:
                content_raw = title

            publish_candidate = (
                getattr(entry, "published_parsed", None)
                or getattr(entry, "updated_parsed", None)
                or getattr(entry, "published", None)
                or getattr(entry, "updated", None)
            )
            publish_time = parse_datetime_to_utc(publish_candidate)
            if not is_within_hours(publish_time, since_hours):
                continue

            publish_key = publish_time.isoformat() if publish_time else ""
            article_id = build_article_id(source.source_id, canonical_url, title, publish_key)
            records.append(
                ArticleRecord(
                    article_id=article_id,
                    source_id=source.source_id,
                    source_name=source.name,
                    source_url=source.url,
                    title=title,
                    content_raw=content_raw,
                    publish_time_utc=publish_time,
                    canonical_url=canonical_url,
                    crawled_at_utc=utc_now(),
                    status=ArticleStatus.FETCHED,
                )
            )
        return records
