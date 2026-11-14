"""Импорт справочников из CSV: кодировки, заголовки, ошибки и права."""

from fastapi.testclient import TestClient


def _upload(client: TestClient, kind: str, content: bytes, name: str = "data.csv"):
    return client.post(
        f"/api/dictionaries/import/{kind}",
        files={"file": (name, content, "text/csv")},
    )


def test_import_fabrics_with_russian_headers(technologist_client: TestClient) -> None:
    content = ("Название;Ширина;Цена;Состав\n" "Кулирка тест;175;500,50;хлопок 100%\n").encode(
        "utf-8-sig"
    )

    response = _upload(technologist_client, "fabrics", content, "fabrics.csv")

    assert response.status_code == 200, response.text
    assert response.json() == {"created": 1, "updated": 0, "errors": []}

    fabrics = technologist_client.get("/api/dictionaries").json()["fabrics"]
    fabric = next(item for item in fabrics if item["name"] == "Кулирка тест")
    assert fabric["width_cm"] == 175.0
    assert fabric["price_per_m"] == 500.5


def test_reimport_updates_existing_row(technologist_client: TestClient) -> None:
    first = "name;width_cm;price_per_m\nТкань тест;180;100\n".encode()
    second = "name;width_cm;price_per_m\nТкань тест;190;120\n".encode()

    assert _upload(technologist_client, "fabrics", first).json()["created"] == 1

    response = _upload(technologist_client, "fabrics", second)
    assert response.json() == {"created": 0, "updated": 1, "errors": []}

    fabrics = technologist_client.get("/api/dictionaries").json()["fabrics"]
    fabric = next(item for item in fabrics if item["name"] == "Ткань тест")
    assert fabric["width_cm"] == 190.0
    assert fabric["price_per_m"] == 120.0


def test_import_reads_cp1251_and_semicolon(technologist_client: TestClient) -> None:
    content = "name;price\nНитки тест;50\n".encode("cp1251")

    response = _upload(technologist_client, "hardware", content)

    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    hardware = technologist_client.get("/api/dictionaries").json()["hardware"]
    item = next(row for row in hardware if row["name"] == "Нитки тест")
    assert item["unit"] == "piece"
    assert item["price"] == 50.0


def test_bad_rows_are_reported_but_good_rows_imported(
    technologist_client: TestClient,
) -> None:
    content = "name;price\nХорошая;100\nПлохая;abc\n".encode()

    response = _upload(technologist_client, "branding", content)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["errors"] and "Строка 3" in body["errors"][0]


def test_file_without_valid_rows_is_rejected(technologist_client: TestClient) -> None:
    response = _upload(technologist_client, "branding", "name;price\nПлохая;abc\n".encode())

    assert response.status_code == 400
    assert "Строка 2" in response.json()["detail"]


def test_missing_required_column_is_rejected(technologist_client: TestClient) -> None:
    response = _upload(technologist_client, "fabrics", "name;price\nТкань;100\n".encode())

    assert response.status_code == 400
    assert "width_cm" in response.json()["detail"]


def test_manager_cannot_import(client: TestClient) -> None:
    response = _upload(client, "branding", "name;price\nЛоготип;100\n".encode())

    assert response.status_code == 403


def test_unknown_dictionary_returns_404(technologist_client: TestClient) -> None:
    assert _upload(technologist_client, "unknown", b"name\n").status_code == 404


def test_complexity_import_uses_code(technologist_client: TestClient) -> None:
    content = "code;name;factor\nsimple;Простая;1.10\n".encode()

    response = _upload(technologist_client, "complexity", content)

    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    levels = technologist_client.get("/api/dictionaries").json()["complexity_levels"]
    assert any(level["code"] == "simple" and level["factor"] == 1.1 for level in levels)


def test_template_is_csv_with_headers(technologist_client: TestClient) -> None:
    response = technologist_client.get("/api/dictionaries/import/fabrics/template.csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "name;width_cm;price_per_m" in response.text
