"""实时 RSS 拉取并写入 zhilian-robot Mongo。"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _record_fingerprint(article: Dict[str, Any]) -> str:
    title = _safe_text(article.get("title"))
    source = _safe_text(article.get("source") or article.get("source_name"))
    url = _safe_text(article.get("url") or article.get("source_url"))
    published_at = _safe_text(article.get("published_at") or article.get("publish_time"))
    raw = "|".join([title, source, url, published_at])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": _safe_text(article.get("title")) or "未命名资讯",
        "content": _safe_text(article.get("content") or article.get("summary")),
        "source": _safe_text(article.get("source") or article.get("source_name") or "rss_unknown"),
        "url": _safe_text(article.get("url") or article.get("source_url")),
        "published_at": article.get("published_at"),
        "publish_time": article.get("published_at") or article.get("publish_time"),
        "crawled_at": article.get("crawled_at") or datetime.utcnow(),
        "processed_at": datetime.utcnow(),
        "processed": False,
        "ingest_source": "openspg_demo_rss",
    }


def _pull_articles(max_entries_per_feed: int, hours_ago: int) -> Tuple[List[Dict[str, Any]], str]:
    try:
        from app.crawler.rss_parser import rss_parser

        return (
            rss_parser.parse_all_feeds(
                max_entries_per_feed=max_entries_per_feed,
                hours_ago=hours_ago,
            ),
            "rss_parser",
        )
    except Exception:
        # 本地精简环境缺少 feedparser 时，回退到已有新闻爬虫实现。
        from app.crawler.news_crawler import news_crawler

        keywords = ["机器人", "工业机器人", "协作机器人"]
        per_keyword = max(1, max_entries_per_feed // max(len(keywords), 1))
        rows: List[Dict[str, Any]] = []
        for keyword in keywords:
            for item in news_crawler.crawl_all_sources(keyword)[:per_keyword]:
                item.setdefault("published_at", item.get("crawled_at"))
                rows.append(item)
        return rows, "news_crawler"


def pull_rss_articles_to_mongo(max_entries_per_feed: int = 5, hours_ago: int = 24) -> Dict[str, Any]:
    """拉取 RSS 并写入 crawled_articles；按 URL/指纹去重。"""
    from app.database.mongodb import mongodb_conn

    articles, pull_mode = _pull_articles(
        max_entries_per_feed=max_entries_per_feed,
        hours_ago=hours_ago,
    )

    collection = mongodb_conn.get_collection("crawled_articles")
    inserted_count = 0
    duplicate_count = 0
    sample_titles: List[str] = []

    for article in articles:
        normalized = _normalize_article(article)
        url = _safe_text(normalized.get("url"))
        if url:
            existing = collection.find_one({"url": url}, {"_id": 1})
        else:
            fingerprint = _record_fingerprint(normalized)
            existing = collection.find_one({"rss_fingerprint": fingerprint}, {"_id": 1})
            normalized["rss_fingerprint"] = fingerprint

        if existing:
            duplicate_count += 1
            continue

        collection.insert_one(normalized)
        inserted_count += 1
        if len(sample_titles) < 5:
            sample_titles.append(normalized["title"])

    return {
        "status": "success",
        "pull_mode": pull_mode,
        "fetched_count": len(articles),
        "inserted_count": inserted_count,
        "duplicate_count": duplicate_count,
        "sample_titles": sample_titles,
        "hours_ago": hours_ago,
        "max_entries_per_feed": max_entries_per_feed,
    }
