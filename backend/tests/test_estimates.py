from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Estimate


def _dictionaries(client: TestClient) -> dict:
    response = client.get("/api/dictionaries")
    assert response.status_code == 200
    return response.json()


def _payload(client: TestClient, **overrides) -> dict:
    data = _dictionaries(client)
    fabric = next(item for item in data["fabrics"] if item["name"].startswith("Кулирка"))
    product = next(item for item in data["product_types"] if item["name"] == "Футболка")
    complexity = next(item for item in data["complexity_levels"] if item["code"] == "base")

    payload = {
        "product_type_id": product["id"],
        "complexity_id": complexity["id"],
        "quantity": 100,
        "fabric_id": fabric["id"],
        "parts": [
            {"name": "Перед", "length_cm": 70, "width_cm": 50, "count_per_unit": 1},
            {"name": "Спинка", "length_cm": 70, "width_cm": 50, "count_per_unit": 1},
            {"name": "Рукав", "length_cm": 60, "width_cm": 25, "count_per_unit": 2},
        ],
        "contractor_name": "ООО «Тестовый заказчик»",
    }
    payload.update(overrides)
    return payload


def test_preview_matches_expected_numbers(client: TestClient) -> None:
    response = client.post("/api/estimates/preview", json=_payload(client))

    assert response.status_code == 200, response.text
    preview = response.json()

    assert preview["material"]["length_with_waste_m"] == 82.246
    assert preview["totals"]["material_cost"] == 39478.08
    assert preview["totals"]["sewing_cost"] == 51000.0
    assert preview["totals"]["cutting_cost"] == 4666.67
    assert preview["totals"]["total_cost"] == 95144.75
    assert preview["totals"]["unit_cost"] == 951.45
    assert preview["lead_time_days"] == 4
    assert preview["cutting"]["pieces_total"] == 400


def test_preview_applies_complexity_and_extras(client: TestClient) -> None:
    data = _dictionaries(client)
    hard = next(item for item in data["complexity_levels"] if item["code"] == "hard")

    response = client.post(
        "/api/estimates/preview",
        json=_payload(client, complexity_id=hard["id"], has_pockets=True),
    )

    assert response.status_code == 200
    sewing = response.json()["sewing"]
    assert sewing["modifier"] == 1.08
    assert sewing["hours"] == 97.2  # 0.6 * 1.5 * 100 * 1.08


def test_waste_outside_range_adds_warning(client: TestClient) -> None:
    response = client.post("/api/estimates/preview", json=_payload(client, waste_coefficient=0.5))

    assert response.status_code == 200
    assert response.json()["warnings"]


def test_part_wider_than_roll_returns_400(client: TestClient) -> None:
    payload = _payload(
        client,
        parts=[{"name": "Широкая", "length_cm": 50, "width_cm": 400, "count_per_unit": 1}],
    )

    response = client.post("/api/estimates/preview", json=payload)

    assert response.status_code == 400
    assert "шире рулона" in response.json()["detail"]


def test_duplicate_part_names_return_400(client: TestClient) -> None:
    payload = _payload(
        client,
        parts=[
            {"name": "Перед", "length_cm": 70, "width_cm": 50, "count_per_unit": 1},
            {"name": " перед ", "length_cm": 70, "width_cm": 50, "count_per_unit": 1},
        ],
    )

    preview = client.post("/api/estimates/preview", json=payload)
    assert preview.status_code == 400
    assert "повторяются" in preview.json()["detail"]

    created = client.post("/api/estimates", json=payload)
    assert created.status_code == 400
    assert "перед" in created.json()["detail"].casefold()

    assert client.get("/api/estimates").json()["total"] == 0


def test_create_estimate_and_read_it(client: TestClient) -> None:
    created = client.post("/api/estimates", json=_payload(client))

    assert created.status_code == 201, created.text
    estimate = created.json()
    assert estimate["number"].startswith("КП-")
    assert estimate["author_name"]
    assert len(estimate["parts"]) == 3

    detail = client.get(f"/api/estimates/{estimate['id']}")
    assert detail.status_code == 200
    assert detail.json()["total_cost"] == 95144.75


def test_history_search_and_filter(client: TestClient) -> None:
    client.post("/api/estimates", json=_payload(client, contractor_name="ИП Поиск"))
    client.post("/api/estimates", json=_payload(client, contractor_name="ООО Другой"))

    found = client.get("/api/estimates", params={"q": "Поиск"}).json()
    assert found["total"] == 1
    assert found["items"][0]["contractor_name"] == "ИП Поиск"

    everything = client.get("/api/estimates").json()
    assert everything["total"] == 2


def test_history_date_filter_uses_local_day(
    client: TestClient, session_factory: sessionmaker
) -> None:
    estimate = client.post("/api/estimates", json=_payload(client)).json()
    # 19:30 UTC — это уже 00:30 следующего дня в Сургуте (UTC+5).
    with session_factory() as session:
        row = session.get(Estimate, estimate["id"])
        assert row is not None
        row.created_at = datetime(2026, 3, 4, 19, 30)
        session.commit()

    def ids(day: str) -> list[int]:
        response = client.get("/api/estimates", params={"date_from": day, "date_to": day})
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert estimate["id"] not in ids("2026-03-04")
    assert estimate["id"] in ids("2026-03-05")


def test_search_is_case_insensitive_for_cyrillic(client: TestClient) -> None:
    client.post("/api/estimates", json=_payload(client, contractor_name="ООО «Ромашка»"))

    found = client.get("/api/estimates", params={"q": "ромашка"}).json()

    assert found["total"] == 1
    assert found["items"][0]["contractor_name"] == "ООО «Ромашка»"


def test_manager_does_not_see_foreign_estimate(
    client: TestClient, technologist_client: TestClient
) -> None:
    foreign = technologist_client.post("/api/estimates", json=_payload(technologist_client)).json()

    assert client.get(f"/api/estimates/{foreign['id']}").status_code == 403


def test_pdf_is_generated(client: TestClient) -> None:
    estimate = client.post("/api/estimates", json=_payload(client)).json()

    response = client.get(f"/api/estimates/{estimate['id']}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 5000
    assert b"/Subtype /Image" not in response.content


def test_pdf_includes_uploaded_logo(
    client: TestClient, technologist_client: TestClient, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path / "uploads"))
    logo = BytesIO()
    Image.new("RGB", (120, 40), (31, 78, 121)).save(logo, format="PNG")
    upload = technologist_client.post(
        "/api/dictionaries/logo",
        files={"file": ("logo.png", logo.getvalue(), "image/png")},
    )
    assert upload.status_code == 200, upload.text

    estimate = client.post("/api/estimates", json=_payload(client)).json()
    response = client.get(f"/api/estimates/{estimate['id']}/pdf")

    assert response.status_code == 200
    assert b"/Subtype /Image" in response.content


def test_share_link_is_public(client: TestClient, anon_client: TestClient) -> None:
    estimate = client.post("/api/estimates", json=_payload(client)).json()

    share = client.post(f"/api/estimates/{estimate['id']}/share")
    assert share.status_code == 200
    token = share.json()["token"]

    shared = anon_client.get(f"/api/public/estimates/{token}")
    assert shared.status_code == 200
    assert shared.json()["number"] == estimate["number"]


def test_delete_estimate(client: TestClient) -> None:
    estimate = client.post("/api/estimates", json=_payload(client)).json()

    assert client.delete(f"/api/estimates/{estimate['id']}").status_code == 204
    assert client.get(f"/api/estimates/{estimate['id']}").status_code == 404


def test_email_falls_back_to_outbox(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "outbox_dir", str(tmp_path))
    estimate = client.post("/api/estimates", json=_payload(client)).json()

    response = client.post(
        f"/api/estimates/{estimate['id']}/send-email",
        json={"to": "client@example.com", "message": "Проверка отправки"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "outbox"
    assert "SMTP" in payload["detail"]

    files = list(tmp_path.glob("*.eml"))
    assert len(files) == 1
    raw = files[0].read_bytes()
    assert b"application/pdf" in raw
    assert b"client@example.com" in raw
    assert len(raw) > 10_000


def test_email_rejects_invalid_address(client: TestClient) -> None:
    estimate = client.post("/api/estimates", json=_payload(client)).json()

    response = client.post(
        f"/api/estimates/{estimate['id']}/send-email",
        json={"to": "not-an-email"},
    )

    assert response.status_code == 422


def test_cannot_email_foreign_estimate(client: TestClient, technologist_client: TestClient) -> None:
    foreign = technologist_client.post("/api/estimates", json=_payload(technologist_client)).json()

    response = client.post(
        f"/api/estimates/{foreign['id']}/send-email",
        json={"to": "client@example.com"},
    )

    assert response.status_code == 403


def test_csv_export_contains_estimate(client: TestClient) -> None:
    estimate = client.post(
        "/api/estimates", json=_payload(client, contractor_name="ИП Экспорт")
    ).json()

    response = client.get("/api/estimates/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.content.decode("utf-8-sig")
    assert text.startswith("Номер;Дата;")
    assert "ИП Экспорт" in text
    assert estimate["number"] in text
    assert "Итого;За единицу" in text


def test_csv_export_respects_manager_scope(
    client: TestClient, technologist_client: TestClient
) -> None:
    foreign = technologist_client.post("/api/estimates", json=_payload(technologist_client)).json()

    text = client.get("/api/estimates/export.csv").content.decode("utf-8-sig")

    assert foreign["number"] not in text


def test_estimate_exposes_contractor_email(client: TestClient) -> None:
    contractor = next(
        item for item in _dictionaries(client)["contractors"] if item["contact_email"]
    )

    estimate = client.post(
        "/api/estimates",
        json=_payload(client, contractor_id=contractor["id"], contractor_name=None),
    ).json()

    assert estimate["contractor_email"] == contractor["contact_email"]


def test_new_contractor_name_creates_profile(client: TestClient) -> None:
    name = "ООО «Профиль из расчёта»"

    client.post("/api/estimates", json=_payload(client, contractor_name=name))

    profiles = _dictionaries(client)["contractors"]
    assert any(item["name"] == name for item in profiles)


def test_contractor_name_is_reused_case_insensitively(client: TestClient) -> None:
    name = "ООО «Регистр подрядчика»"

    client.post("/api/estimates", json=_payload(client, contractor_name=name))
    client.post("/api/estimates", json=_payload(client, contractor_name="ооо «регистр подрядчика»"))

    profiles = _dictionaries(client)["contractors"]
    matches = [item for item in profiles if item["name"].casefold() == name.casefold()]
    assert len(matches) == 1


def test_technologist_can_update_settings(technologist_client: TestClient) -> None:
    response = technologist_client.patch(
        "/api/dictionaries/settings",
        json={"sewing_normohour": 900},
    )

    assert response.status_code == 200
    assert response.json()["sewing_normohour"] == 900.0

    dictionaries = technologist_client.get("/api/dictionaries").json()
    assert dictionaries["settings"]["sewing_normohour"] == 900.0
