from scripts.migrate_reports_from_ods import map_report_doc


def test_map_report_doc():
    src = {"title": "t", "content": "c", "url": "u", "source": "东方财富网"}
    doc = map_report_doc(src)
    assert doc["resource_type"] == "report"
    assert "extra_meta" in doc
