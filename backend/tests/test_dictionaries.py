"""Справочники: защита от дублей и понятные ошибки вместо 500."""

from fastapi.testclient import TestClient

FABRIC = {
    "name": "Ткань-уникум",
    "width_cm": 180,
    "price_per_m": 500,
    "density": "хлопок 100%",
}


def test_duplicate_fabric_name_is_rejected(technologist_client: TestClient) -> None:
    created = technologist_client.post("/api/dictionaries/fabrics", json=FABRIC)
    assert created.status_code == 201, created.text

    duplicate = technologist_client.post(
        "/api/dictionaries/fabrics", json={**FABRIC, "name": "ткань-уникум"}
    )

    assert duplicate.status_code == 409
    assert "уже есть" in duplicate.json()["detail"]


def test_rename_to_existing_fabric_is_rejected(technologist_client: TestClient) -> None:
    first = technologist_client.post("/api/dictionaries/fabrics", json=FABRIC).json()
    second = technologist_client.post(
        "/api/dictionaries/fabrics", json={**FABRIC, "name": "Ткань-вторая"}
    ).json()

    response = technologist_client.patch(
        f"/api/dictionaries/fabrics/{second['id']}",
        json={**FABRIC, "name": first["name"]},
    )

    assert response.status_code == 409
    assert "уже есть" in response.json()["detail"]


def test_duplicate_complexity_code_is_rejected(technologist_client: TestClient) -> None:
    payload = {"code": "uniq", "name": "Уникальная", "factor": 1.2}
    assert technologist_client.post("/api/dictionaries/complexity", json=payload).status_code == 201

    duplicate = technologist_client.post(
        "/api/dictionaries/complexity", json={**payload, "code": "UNIQ"}
    )

    assert duplicate.status_code == 409
    assert "уже есть" in duplicate.json()["detail"]


def test_contractor_rename_to_existing_is_rejected(technologist_client: TestClient) -> None:
    first = technologist_client.post("/api/contractors", json={"name": "Подрядчик-один"}).json()
    second = technologist_client.post("/api/contractors", json={"name": "Подрядчик-два"}).json()

    response = technologist_client.patch(
        f"/api/contractors/{second['id']}", json={"name": "подрядчик-один"}
    )

    assert response.status_code == 409
    assert "уже есть" in response.json()["detail"]
    assert first["id"] != second["id"]
