def test_backend_can_import_openks_package():
    import openks

    assert hasattr(openks, "get_engine_overview")
