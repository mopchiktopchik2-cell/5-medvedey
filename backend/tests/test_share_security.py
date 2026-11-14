from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models import Estimate
from tests.test_estimates import _payload


def _create_estimate(client: TestClient) -> dict:
    return client.post("/api/estimates", json=_payload(client)).json()


def test_share_returns_expiry_date(client: TestClient) -> None:
    estimate = _create_estimate(client)

    share = client.post(f"/api/estimates/{estimate['id']}/share")

    assert share.status_code == 200
    body = share.json()
    assert body["token"]
    assert body["expires_at"]


def test_share_is_reused_while_valid(client: TestClient) -> None:
    estimate = _create_estimate(client)

    first = client.post(f"/api/estimates/{estimate['id']}/share").json()
    second = client.post(f"/api/estimates/{estimate['id']}/share").json()

    assert first["token"] == second["token"]


def test_expired_share_link_is_rejected(
    client: TestClient, anon_client: TestClient, session_factory
) -> None:
    estimate = _create_estimate(client)
    token = client.post(f"/api/estimates/{estimate['id']}/share").json()["token"]

    with session_factory() as session:
        row = session.get(Estimate, estimate["id"])
        row.share_expires_at = datetime.now(UTC) - timedelta(days=1)
        session.commit()

    assert anon_client.get(f"/api/public/estimates/{token}").status_code == 404
    assert anon_client.get(f"/api/public/estimates/{token}/pdf").status_code == 404


def test_revoked_share_link_is_rejected(client: TestClient, anon_client: TestClient) -> None:
    estimate = _create_estimate(client)
    token = client.post(f"/api/estimates/{estimate['id']}/share").json()["token"]

    assert client.delete(f"/api/estimates/{estimate['id']}/share").status_code == 204
    assert anon_client.get(f"/api/public/estimates/{token}").status_code == 404


def test_public_estimate_hides_internal_fields(client: TestClient, anon_client: TestClient) -> None:
    estimate = _create_estimate(client)
    token = client.post(f"/api/estimates/{estimate['id']}/share").json()["token"]

    body = anon_client.get(f"/api/public/estimates/{token}").json()

    for hidden in (
        "contractor_email",
        "author_id",
        "author_name",
        "share_token",
        "share_expires_at",
        "sewing_normohour",
        "cutting_normohour",
        "fabric_price_per_m",
        "notes",
    ):
        assert hidden not in body
    # то, что нужно для показа КП, остаётся на месте
    assert body["number"] == estimate["number"]
    assert body["total_cost"] == estimate["total_cost"]
