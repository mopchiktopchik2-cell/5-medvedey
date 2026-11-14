"""Смена пароля или роли завершает все ранее выданные сессии сотрудника."""

from fastapi.testclient import TestClient

from app.main import app

MANAGER = {"email": "manager@mir.ru", "password": "manager123"}


def _login(client: TestClient, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": MANAGER["email"], "password": password},
    )
    assert response.status_code == 200, response.text


def _manager_id(technologist_client: TestClient) -> int:
    users = technologist_client.get("/api/users").json()
    return next(item["id"] for item in users if item["email"] == MANAGER["email"])


def test_password_change_revokes_other_sessions(client: TestClient) -> None:
    other = TestClient(app)
    _login(other, MANAGER["password"])
    assert other.get("/api/auth/me").status_code == 200

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": MANAGER["password"], "new_password": "manager-new-1"},
    )
    assert changed.status_code == 204

    # Обе сессии — текущая и параллельная — больше не действуют.
    assert other.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me").status_code == 401

    _login(other, "manager-new-1")


def test_admin_password_reset_revokes_sessions(
    client: TestClient, technologist_client: TestClient
) -> None:
    other = TestClient(app)
    _login(other, MANAGER["password"])

    response = technologist_client.patch(
        f"/api/users/{_manager_id(technologist_client)}",
        json={"password": "reset-pass-123"},
    )
    assert response.status_code == 200, response.text

    assert other.get("/api/auth/me").status_code == 401
    _login(other, "reset-pass-123")


def test_role_change_revokes_sessions(client: TestClient, technologist_client: TestClient) -> None:
    other = TestClient(app)
    _login(other, MANAGER["password"])

    response = technologist_client.patch(
        f"/api/users/{_manager_id(technologist_client)}",
        json={"role": "technologist"},
    )
    assert response.status_code == 200, response.text

    # Старый токен содержал роль manager — после смены роли он недействителен.
    assert other.get("/api/auth/me").status_code == 401
    _login(other, MANAGER["password"])
    assert other.get("/api/auth/me").json()["role"] == "technologist"
