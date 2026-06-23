from fastapi.testclient import TestClient


def _build_client() -> TestClient:
    from main import create_app

    app = create_app()
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    return TestClient(app)


def test_operator_workbench_allows_local_dev_origin():
    client = _build_client()

    response = client.options(
        "/api/v1/operator-workbench/overview",
        headers={
            "Origin": "http://localhost:13000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:13000"
