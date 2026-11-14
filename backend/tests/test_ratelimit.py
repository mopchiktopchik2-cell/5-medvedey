from fastapi.testclient import TestClient

MANAGER_LOGIN = {"email": "manager@mir.ru", "password": "manager123"}
WRONG_LOGIN = {"email": "manager@mir.ru", "password": "definitely-wrong"}


def test_login_is_blocked_after_repeated_failures(anon_client: TestClient) -> None:
    for _ in range(5):
        response = anon_client.post("/api/auth/login", json=WRONG_LOGIN)
        assert response.status_code == 401

    blocked = anon_client.post("/api/auth/login", json=MANAGER_LOGIN)

    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After")


def test_successful_login_resets_failures(anon_client: TestClient) -> None:
    for _ in range(3):
        anon_client.post("/api/auth/login", json=WRONG_LOGIN)

    assert anon_client.post("/api/auth/login", json=MANAGER_LOGIN).status_code == 200

    # счётчик сброшен: ещё три ошибки не блокируют вход
    for _ in range(3):
        anon_client.post("/api/auth/login", json=WRONG_LOGIN)

    assert anon_client.post("/api/auth/login", json=MANAGER_LOGIN).status_code == 200
