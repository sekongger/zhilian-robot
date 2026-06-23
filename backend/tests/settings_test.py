import os
from config.settings import Settings


def test_settings_accept_external_mongo_env():
    os.environ["ODS_MONGODB_URI"] = "mongodb://user:pass@192.168.1.37:27017"
    os.environ["ODS_MONGODB_DATABASE"] = "ods_report"
    settings = Settings()
    assert settings.ODS_MONGODB_URI.startswith("mongodb://")
    assert settings.ODS_MONGODB_DATABASE == "ods_report"


def test_settings_accept_graphiti_env():
    os.environ["GRAPHITI_ENABLED"] = "false"
    os.environ["GRAPHITI_BASE_URL"] = "http://graphiti:8000"
    os.environ["GRAPHITI_TIMEOUT_SECONDS"] = "9"
    os.environ["GRAPHITI_GROUP_PREFIX"] = "zju-openks"

    settings = Settings()

    assert settings.GRAPHITI_ENABLED is False
    assert settings.GRAPHITI_BASE_URL == "http://graphiti:8000"
    assert settings.GRAPHITI_TIMEOUT_SECONDS == 9.0
    assert settings.GRAPHITI_GROUP_PREFIX == "zju-openks"
