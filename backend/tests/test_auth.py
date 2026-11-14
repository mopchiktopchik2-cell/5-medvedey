from fastapi.testclient import TestClient

from tests.conftest import MANAGER


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_required_auth(anon_client: TestClient) -> None:
    assert anon_client.get("/api/estimates").status_code == 401


def test_login_rejects_wrong_password(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/api/auth/login",
        json={"email": MANAGER["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_and_me(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["role"] == "manager"


def test_logout_clears_session(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_manager_cannot_edit_dictionaries(client: TestClient) -> None:
    response = client.post(
        "/api/dictionaries/fabrics",
        json={"name": "Тест", "width_cm": 150, "price_per_m": 100},
    )

    assert response.status_code == 403
