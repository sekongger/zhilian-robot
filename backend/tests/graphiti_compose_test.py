from pathlib import Path


def test_docker_compose_defines_graphiti_services_and_backend_env():
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    text = compose_path.read_text(encoding="utf-8")

    assert "graphiti-neo4j:" in text
    assert "graphiti:" in text
    assert 'GRAPHITI_ENABLED=${GRAPHITI_ENABLED:-true}' in text
    assert 'GRAPHITI_BASE_URL=${GRAPHITI_BASE_URL:-http://graphiti:8000}' in text
    assert 'GRAPHITI_TIMEOUT_SECONDS=${GRAPHITI_TIMEOUT_SECONDS:-30}' in text
    assert 'GRAPHITI_GROUP_PREFIX=${GRAPHITI_GROUP_PREFIX:-openks}' in text
