from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings


@pytest.fixture()
def uploads(tmp_path, monkeypatch):
    path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "uploads_dir", str(path))
    return path


def _png(width: int = 120, height: int = 40) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (width, height), (31, 78, 121, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(client: TestClient, content: bytes, *, name: str = "logo.png", mime: str = "image/png"):
    return client.post("/api/dictionaries/logo", files={"file": (name, content, mime)})


def test_logo_meta_is_empty_by_default(anon_client: TestClient, uploads) -> None:
    response = anon_client.get("/api/public/logo/meta")

    assert response.status_code == 200
    assert response.json() == {"has_logo": False, "updated_at": None}
    assert anon_client.get("/api/public/logo").status_code == 404


def test_manager_cannot_upload_logo(client: TestClient, uploads) -> None:
    response = _upload(client, _png())

    assert response.status_code == 403


def test_technologist_uploads_and_removes_logo(
    technologist_client: TestClient, anon_client: TestClient, uploads
) -> None:
    response = _upload(technologist_client, _png())

    assert response.status_code == 200, response.text
    assert response.json()["has_logo"] is True
    assert (uploads / "logo.png").is_file()

    image = anon_client.get("/api/public/logo")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")

    meta = anon_client.get("/api/public/logo/meta").json()
    assert meta["has_logo"] is True
    assert meta["updated_at"]

    assert technologist_client.delete("/api/dictionaries/logo").status_code == 204
    assert anon_client.get("/api/public/logo").status_code == 404


def test_logo_rejects_wrong_content_type(technologist_client: TestClient, uploads) -> None:
    response = _upload(technologist_client, b"plain text", name="logo.txt", mime="text/plain")

    assert response.status_code == 415


def test_logo_rejects_broken_image(technologist_client: TestClient, uploads) -> None:
    response = _upload(technologist_client, b"not really a png")

    assert response.status_code == 400
    assert "изображение" in response.json()["detail"]


def test_logo_is_normalized_to_png(technologist_client: TestClient, uploads) -> None:
    buffer = BytesIO()
    Image.new("RGB", (1600, 900), (200, 30, 40)).save(buffer, format="JPEG")

    response = _upload(technologist_client, buffer.getvalue(), name="logo.jpg", mime="image/jpeg")

    assert response.status_code == 200
    with Image.open(uploads / "logo.png") as image:
        assert image.format == "PNG"
        assert max(image.size) <= 600
