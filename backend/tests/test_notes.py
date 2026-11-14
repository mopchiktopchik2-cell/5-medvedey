from fastapi.testclient import TestClient


def test_create_and_list_notes(client: TestClient) -> None:
    created = client.post("/api/notes", json={"title": "Первая", "body": "текст"})
    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "Первая"

    listed = client.get("/api/notes")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [note["id"]]


def test_update_note(client: TestClient) -> None:
    note_id = client.post("/api/notes", json={"title": "Черновик"}).json()["id"]

    updated = client.patch(f"/api/notes/{note_id}", json={"title": "Готово"})

    assert updated.status_code == 200
    assert updated.json()["title"] == "Готово"
    assert updated.json()["body"] == ""


def test_delete_note(client: TestClient) -> None:
    note_id = client.post("/api/notes", json={"title": "Удалить"}).json()["id"]

    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.get(f"/api/notes/{note_id}").status_code == 404


def test_create_validation_error(client: TestClient) -> None:
    assert client.post("/api/notes", json={"title": ""}).status_code == 422
