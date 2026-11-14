from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir() -> None:
    if not settings.database_url.startswith("sqlite:///"):
        return
    path = settings.database_url.removeprefix("sqlite:///")
    if path and path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    from app import models  # noqa: F401  # регистрирует таблицы в metadata

    _ensure_sqlite_dir()
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
