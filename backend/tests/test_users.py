from fastapi.testclient import TestClient

NEW_USER = {
    "email": "new.manager@mir.ru",
    "full_name": "Новый Менеджер",
    "role": "manager",
    "password": "super-secret-1",
}


def test_technologist_lists_users(technologist_client: TestClient) -> None:
    response = technologist_client.get("/api/users")

    assert response.status_code == 200
    emails = {item["email"] for item in response.json()}
    assert {"manager@mir.ru", "technologist@mir.ru"} <= emails


def test_manager_cannot_manage_users(client: TestClient) -> None:
    assert client.get("/api/users").status_code == 403
    assert client.post("/api/users", json=NEW_USER).status_code == 403


def test_created_user_can_login(technologist_client: TestClient, anon_client: TestClient) -> None:
    created = technologist_client.post("/api/users", json=NEW_USER)

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "manager"
    assert body["is_active"] is True
    # хеш пароля наружу не отдаём
    assert "password" not in body
    assert "password_hash" not in body

    login = anon_client.post(
        "/api/auth/login",
        json={"email": NEW_USER["email"], "password": NEW_USER["password"]},
    )
    assert login.status_code == 200
    assert login.json()["email"] == NEW_USER["email"]


def test_duplicate_email_is_rejected(technologist_client: TestClient) -> None:
    payload = {**NEW_USER, "email": "manager@mir.ru"}

    assert technologist_client.post("/api/users", json=payload).status_code == 409


def test_user_can_change_own_password(client: TestClient, anon_client: TestClient) -> None:
    wrong = client.post(
        "/api/auth/change-password",
        json={"current_password": "nope", "new_password": "brand-new-pass"},
    )
    assert wrong.status_code == 400

    ok = client.post(
        "/api/auth/change-password",
        json={"current_password": "manager123", "new_password": "brand-new-pass"},
    )
    assert ok.status_code == 204
    # сессия закрыта, старый пароль больше не действует
    assert client.get("/api/auth/me").status_code == 401
    assert (
        anon_client.post(
            "/api/auth/login",
            json={"email": "manager@mir.ru", "password": "manager123"},
        ).status_code
        == 401
    )
    assert (
        anon_client.post(
            "/api/auth/login",
            json={"email": "manager@mir.ru", "password": "brand-new-pass"},
        ).status_code
        == 200
    )


def test_technologist_can_reset_user_password(technologist_client: TestClient) -> None:
    users = technologist_client.get("/api/users").json()
    manager = next(item for item in users if item["email"] == "manager@mir.ru")

    response = technologist_client.patch(
        f"/api/users/{manager['id']}", json={"password": "reset-by-technologist"}
    )

    assert response.status_code == 200


def test_saving_unchanged_profile_keeps_session(technologist_client: TestClient) -> None:
    """Сохранение ФИО без смены роли не должно разлогинивать сотрудника."""
    users = technologist_client.get("/api/users").json()
    me = next(item for item in users if item["email"] == "technologist@mir.ru")

    response = technologist_client.patch(
        f"/api/users/{me['id']}",
        json={
            "full_name": me["full_name"],
            "role": me["role"],
            "is_active": me["is_active"],
        },
    )

    assert response.status_code == 200
    assert technologist_client.get("/api/auth/me").status_code == 200


def test_role_change_revokes_employee_session(
    technologist_client: TestClient, anon_client: TestClient
) -> None:
    created = technologist_client.post(
        "/api/users", json={**NEW_USER, "email": "promo@mir.ru"}
    ).json()
    login = anon_client.post(
        "/api/auth/login",
        json={"email": "promo@mir.ru", "password": NEW_USER["password"]},
    )
    assert login.status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 200

    patched = technologist_client.patch(
        f"/api/users/{created['id']}", json={"role": "technologist"}
    )

    assert patched.status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 401


def test_cannot_deactivate_self(technologist_client: TestClient) -> None:
    users = technologist_client.get("/api/users").json()
    me = next(item for item in users if item["email"] == "technologist@mir.ru")

    response = technologist_client.patch(f"/api/users/{me['id']}", json={"is_active": False})

    assert response.status_code == 400


def test_cannot_demote_last_technologist(technologist_client: TestClient) -> None:
    users = technologist_client.get("/api/users").json()
    technologist = next(item for item in users if item["role"] == "technologist")

    response = technologist_client.patch(
        f"/api/users/{technologist['id']}", json={"role": "manager"}
    )

    assert response.status_code == 400


def test_deactivated_user_cannot_login(
    technologist_client: TestClient, anon_client: TestClient
) -> None:
    created = technologist_client.post(
        "/api/users", json={**NEW_USER, "email": "temp@mir.ru"}
    ).json()

    patched = technologist_client.patch(f"/api/users/{created['id']}", json={"is_active": False})
    assert patched.status_code == 200

    login = anon_client.post(
        "/api/auth/login",
        json={"email": "temp@mir.ru", "password": NEW_USER["password"]},
    )
    assert login.status_code == 403
