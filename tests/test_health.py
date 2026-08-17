from fastapi.testclient import TestClient

from app.main import create_app


def test_root_returns_service_name() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "fastdocpy-oracle-api-v2"


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "fastdocpy-oracle-api-v2"}
