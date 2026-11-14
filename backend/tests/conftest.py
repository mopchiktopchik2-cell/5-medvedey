from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, get_session
from app.main import app
from app.seed import seed

MANAGER = {"email": "manager@mir.ru", "password": "manager123"}
TECHNOLOGIST = {"email": "technologist@mir.ru", "password": "technolog123"}


@pytest.fixture()
def session_factory(tmp_path) -> Iterator[sessionmaker]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        seed(session)
    yield factory


@pytest.fixture()
def anon_client(session_factory) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _login(client: TestClient, credentials: dict[str, str]) -> TestClient:
    response = client.post("/api/auth/login", json=credentials)
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def client(anon_client: TestClient) -> TestClient:
    return _login(anon_client, MANAGER)


@pytest.fixture()
def technologist_client(session_factory) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as tech:
        yield _login(tech, TECHNOLOGIST)
    app.dependency_overrides.clear()
