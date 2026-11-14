from datetime import datetime

from fastapi.testclient import TestClient


def test_create_keeps_cyrillic(client: TestClient) -> None:
    response = client.post("/api/notes", json={"title": "Медведь", "body": "Ёж"})

    assert response.status_code == 201
    assert response.json()["title"] == "Медведь"
    assert response.json()["body"] == "Ёж"


def test_created_at_is_utc_iso(client: TestClient) -> None:
    created_at = client.post("/api/notes", json={"title": "Время"}).json()["created_at"]

    parsed = datetime.fromisoformat(created_at)
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_get_missing_note_returns_404(client: TestClient) -> None:
    assert client.get("/api/notes/999").status_code == 404
