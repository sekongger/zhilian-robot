"""产业头条规则聚合服务（演示版）。"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


EVENT_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "cooperation": ("合作", "签约", "携手", "联合", "战略合作"),
    "financing": ("融资", "获投", "投资", "A轮", "B轮", "Pre-A", "天使轮"),
    "product_release": ("发布", "推出", "新品", "新款", "上新"),
    "order": ("订单", "中标", "采购", "签单", "交付"),
    "capacity_expansion": ("扩产", "产能", "投产", "开工", "基地"),
    "policy": ("政策", "通知", "意见", "规划", "标准", "指南"),
}

EVENT_WEIGHTS = {
    "cooperation": 1.0,
    "financing": 1.2,
    "product_release": 1.0,
    "order": 1.1,
    "capacity_expansion": 1.0,
    "policy": 1.3,
    "other": 0.6,
}

EVENT_LABELS_ZH = {
    "cooperation": "合作",
    "financing": "融资",
    "product_release": "发布",
    "order": "订单",
    "capacity_expansion": "扩产",
    "policy": "政策",
    "other": "动态",
}

COMPANY_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9·]{2,24}(?:机器人|车企|科技|智能|集团|股份|公司|厂))"
)


@dataclass
class _NormalizedNews:
    id: str
    title: str
    content: str
    source_name: str
    url: str
    publish_time: datetime
    raw: Dict[str, Any]


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif value in (None, ""):
        dt = datetime.now(timezone.utc)
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_news_item(item: Dict[str, Any], index: int) -> _NormalizedNews:
    title = str(item.get("title") or "未命名资讯").strip()
    content = str(item.get("content") or item.get("summary") or "").strip()
    source_name = str(item.get("source_name") or item.get("source") or "unknown").strip()
    url = str(item.get("source_url") or item.get("url") or "").strip()
    publish_time = _parse_time(item.get("publish_time") or item.get("published_at"))
    item_id = str(item.get("id") or item.get("_id") or f"news_{index}")
    return _NormalizedNews(
        id=item_id,
        title=title,
        content=content,
        source_name=source_name,
        url=url,
        publish_time=publish_time,
        raw=item,
    )


def _detect_event_type(text: str) -> str:
    for event_type, words in EVENT_KEYWORDS.items():
        if any(word in text for word in words):
            return event_type
    return "other"


def _extract_companies(title: str, content: str) -> List[str]:
    # 优先在标题中抽取，避免正文里“机器人系统/产线”等泛化词影响事件聚合
    segments = [
        seg
        for seg in re.split(r"(?:与|和|携手|联合|合作|签约|达成)", title)
        if seg and seg.strip()
    ]
    if not segments:
        segments = [title]

    candidates: List[str] = []
    for seg in segments:
        for match in COMPANY_PATTERN.findall(seg):
            name = match.strip("，。；：、()（）[]【】 ")
            if len(name) < 2:
                continue
            if name in {"机器人", "某公司"}:
                continue
            if name not in candidates:
                candidates.append(name)
    return candidates[:5]


def _event_key(event_type: str, companies: List[str], day_bucket: str, title: str) -> str:
    keys = sorted(companies[:2])
    raw = f"{event_type}|{','.join(keys)}|{day_bucket}"
    if not keys:
        raw += "|" + re.sub(r"\s+", "", title)[:32]
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"evt_{digest}"


def _headline_score(event_type: str, source_count: int, newest_time: datetime, now: datetime) -> float:
    age_hours = max((now - newest_time).total_seconds() / 3600.0, 0.0)
    freshness = max(0.1, 1.0 - min(age_hours / 24.0, 0.9))
    source_bonus = 1.0 + min(max(source_count - 1, 0) * 0.15, 0.6)
    return round(EVENT_WEIGHTS.get(event_type, 0.8) * freshness * source_bonus, 4)


def _build_event_title(event_type: str, companies: List[str]) -> str:
    label = EVENT_LABELS_ZH.get(event_type, "动态")
    if len(companies) >= 2:
        return f"{companies[0]}与{companies[1]}{label}事件"
    if len(companies) == 1:
        return f"{companies[0]}{label}事件"
    return f"机器人产业{label}事件"


def _aggregate_events(items: Iterable[_NormalizedNews], hours: int, top_n: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    groups: Dict[str, Dict[str, Any]] = {}

    items_list = list(items)
    for item in items_list:
        if item.publish_time < cutoff:
            continue

        event_type = _detect_event_type(f"{item.title} {item.content}")
        if event_type == "other":
            continue

        companies = _extract_companies(item.title, item.content)
        day_bucket = item.publish_time.strftime("%Y%m%d")
        event_id = _event_key(event_type, companies, day_bucket, item.title)
        group = groups.setdefault(
            event_id,
            {
                "event_id": event_id,
                "event_type": event_type,
                "event_type_zh": EVENT_LABELS_ZH.get(event_type, "动态"),
                "companies": [],
                "evidence_news": [],
                "sources": set(),
                "newest_time": item.publish_time,
                "oldest_time": item.publish_time,
            },
        )

        for company in companies:
            if company not in group["companies"]:
                group["companies"].append(company)

        group["sources"].add(item.source_name or "unknown")
        group["newest_time"] = max(group["newest_time"], item.publish_time)
        group["oldest_time"] = min(group["oldest_time"], item.publish_time)
        group["evidence_news"].append(
            {
                "news_id": item.id,
                "title": item.title,
                "source_name": item.source_name,
                "url": item.url,
                "publish_time": item.publish_time.isoformat(),
                "snippet": item.content[:180],
            }
        )

    events: List[Dict[str, Any]] = []
    for event_id, group in groups.items():
        source_count = len(group["sources"])
        score = _headline_score(group["event_type"], source_count, group["newest_time"], now)
        event = {
            "event_id": event_id,
            "event_type": group["event_type"],
            "event_type_zh": group["event_type_zh"],
            "event_title": _build_event_title(group["event_type"], group["companies"]),
            "headline_title": _build_event_title(group["event_type"], group["companies"]),
            "headline_score": score,
            "source_count": source_count,
            "companies": group["companies"][:8],
            "latest_publish_time": group["newest_time"].isoformat(),
            "first_publish_time": group["oldest_time"].isoformat(),
            "evidence_news": sorted(
                group["evidence_news"],
                key=lambda x: x["publish_time"],
                reverse=True,
            ),
        }
        events.append(event)

    events.sort(key=lambda e: (e["headline_score"], e["source_count"], e["latest_publish_time"]), reverse=True)
    headlines = [
        {
            "event_id": e["event_id"],
            "event_type": e["event_type"],
            "event_type_zh": e["event_type_zh"],
            "headline_title": e["headline_title"],
            "headline_score": e["headline_score"],
            "source_count": e["source_count"],
            "companies": e["companies"],
            "latest_publish_time": e["latest_publish_time"],
            "evidence_count": len(e["evidence_news"]),
        }
        for e in events[:top_n]
    ]

    return {
        "headlines": headlines,
        "events": events,
        "stats": {
            "news_count": len(items_list),
            "event_count": len(events),
            "multi_source_events_count": sum(1 for e in events if e["source_count"] >= 2),
            "window_hours": hours,
        },
    }


def build_headlines_from_news(news_rows: List[Dict[str, Any]], top_n: int = 20, hours: int = 24) -> Dict[str, Any]:
    normalized = [_normalize_news_item(item, idx) for idx, item in enumerate(news_rows)]
    return _aggregate_events(normalized, hours=hours, top_n=top_n)


def get_event_detail_from_news(news_rows: List[Dict[str, Any]], event_id: str, hours: int = 24) -> Optional[Dict[str, Any]]:
    data = build_headlines_from_news(news_rows, top_n=200, hours=hours)
    for event in data["events"]:
        if event["event_id"] == event_id:
            return event
    return None


def get_demo_news_samples() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "demo-1",
            "doc_id": "DEMO_DOC_ZLR_PARTNER",
            "title": "智链机器人联合宇树科技推进具身智能产线落地",
            "content": "双方将围绕具身智能、机器视觉和自动化产线协同优化柔性制造。",
            "source_name": "rss_36kr",
            "url": "https://example.com/demo-1",
            "publish_time": now.isoformat(),
        },
        {
            "id": "demo-2",
            "doc_id": "DEMO_DOC_ZLR_PRODUCT",
            "title": "智链机器人发布 FlexArm 协作机械臂，升级 3C 装配效率",
            "content": "FlexArm 协作机械臂集成机器视觉与控制器，可用于 3C 装配与柔性制造场景。",
            "source_name": "rss_ifanr",
            "url": "https://example.com/demo-2",
            "publish_time": (now - timedelta(minutes=18)).isoformat(),
        },
        {
            "id": "demo-3",
            "doc_id": "DEMO_DOC_ZLR_PLATFORM",
            "title": "智链机器人携手先导智能发布 RoboOS 控制平台",
            "content": "RoboOS 控制平台进一步强化路径规划、控制器和机器视觉能力，面向机器人产线调度。",
            "source_name": "crawler_sina",
            "url": "https://example.com/demo-3",
            "publish_time": (now - timedelta(hours=3)).isoformat(),
        },
        {
            "id": "demo-4",
            "doc_id": "DEMO_DOC_ZLR_COOP",
            "title": "智链机器人与宇树科技达成合作，联合拓展协作机器人方案",
            "content": "合作方案将把协作机器人、具身智能和机器视觉能力整合到智能制造产线。",
            "source_name": "rss_ithome",
            "url": "https://example.com/demo-4",
            "publish_time": (now - timedelta(hours=5)).isoformat(),
        },
    ]
