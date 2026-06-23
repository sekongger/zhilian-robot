from datetime import datetime, timedelta, timezone

from app.openspg_demo.headlines_service import build_headlines_from_news


def test_group_same_event_news_into_one_headline():
    now = datetime.now(timezone.utc)
    news = [
        {
            "title": "智链机器人与某车企达成战略合作",
            "content": "双方将在智能制造产线部署机器人系统。",
            "source_name": "rss_36kr",
            "url": "https://example.com/1",
            "publish_time": now.isoformat(),
        },
        {
            "title": "某车企携手智链机器人推进产线自动化",
            "content": "双方合作聚焦焊装与装配环节。",
            "source_name": "rss_ifanr",
            "url": "https://example.com/2",
            "publish_time": (now - timedelta(minutes=15)).isoformat(),
        },
    ]

    result = build_headlines_from_news(news, top_n=10, hours=24)

    assert result["stats"]["news_count"] == 2
    assert result["stats"]["event_count"] == 1
    assert len(result["headlines"]) == 1
    assert result["headlines"][0]["source_count"] == 2
    assert result["headlines"][0]["event_type"] == "cooperation"


def test_filters_old_news_outside_time_window():
    now = datetime.now(timezone.utc)
    news = [
        {
            "title": "某公司发布新款协作机器人",
            "content": "新品面向3C行业。",
            "source_name": "rss_ithome",
            "url": "https://example.com/3",
            "publish_time": (now - timedelta(hours=30)).isoformat(),
        }
    ]

    result = build_headlines_from_news(news, top_n=10, hours=24)

    assert result["stats"]["news_count"] == 1
    assert result["stats"]["event_count"] == 0
    assert result["headlines"] == []

