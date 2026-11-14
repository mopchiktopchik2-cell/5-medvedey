import sqlite3
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _register_sqlite_functions(dbapi_connection, _connection_record) -> None:
    """SQLite не умеет lower() для кириллицы — добавляем питоновский вариант."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function(
            "py_lower",
            1,
            lambda value: value.lower() if isinstance(value, str) else value,
            deterministic=True,
        )


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
