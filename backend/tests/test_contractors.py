from fastapi.testclient import TestClient


def test_technologist_manages_contractor_profiles(technologist_client: TestClient) -> None:
    created = technologist_client.post(
        "/api/contractors",
        json={
            "name": "ООО «Тестовый заказчик»",
            "contact_email": "zakaz@test.ru",
            "phone": "+7 (900) 000-00-00",
        },
    )

    assert created.status_code == 201, created.text
    contractor = created.json()
    assert contractor["name"] == "ООО «Тестовый заказчик»"
    assert contractor["contact_email"] == "zakaz@test.ru"

    updated = technologist_client.patch(
        f"/api/contractors/{contractor['id']}",
        json={
            "name": "ООО «Новое имя»",
            "contact_email": "new@test.ru",
            "phone": None,
        },
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "ООО «Новое имя»"
    assert updated.json()["contact_email"] == "new@test.ru"
    assert updated.json()["phone"] is None

    profiles = technologist_client.get("/api/dictionaries").json()["contractors"]
    profile = next(item for item in profiles if item["id"] == contractor["id"])
    assert profile["contact_email"] == "new@test.ru"


def test_manager_cannot_manage_contractor_profiles(client: TestClient) -> None:
    profiles = client.get("/api/dictionaries").json()["contractors"]

    create = client.post("/api/contractors", json={"name": "ООО «Чужой профиль»"})
    update = client.patch(
        f"/api/contractors/{profiles[0]['id']}",
        json={"name": "ООО «Подмена»"},
    )

    assert create.status_code == 403
    assert update.status_code == 403
