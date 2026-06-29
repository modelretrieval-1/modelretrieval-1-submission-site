from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_page_renders():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Sprint 0 foundation is running." in response.text
