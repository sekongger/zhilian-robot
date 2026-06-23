from scripts.migrate_news_to_resource import map_news_doc


def test_map_news_doc():
    src = {"title": "t", "content": "c", "url": "u", "source": "baidu"}
    doc = map_news_doc(src)
    assert doc["resource_type"] == "news"
    assert doc["data_source"] == "baidu"
