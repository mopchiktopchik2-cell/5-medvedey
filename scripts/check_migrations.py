"""Проверка миграций: чистая база, «старая» база, повторный upgrade."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def run_alembic(db: Path, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db.as_posix()}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"alembic {' '.join(args)} упал:\n{result.stderr}\n{result.stdout}")


def query(db: Path, sql: str) -> list[tuple]:
    conn = sqlite3.connect(db)
    try:
        return list(conn.execute(sql))
    finally:
        conn.close()


def tables(db: Path) -> set[str]:
    return {row[0] for row in query(db, "SELECT name FROM sqlite_master WHERE type='table'")}


def main() -> int:
    work = BACKEND / "data"
    work.mkdir(exist_ok=True)

    # 1. Чистая база: миграция должна создать всё с нуля.
    fresh = work / "migration_fresh.db"
    fresh.unlink(missing_ok=True)
    run_alembic(fresh, "upgrade", "head")
    fresh_tables = tables(fresh)
    assert "users" in fresh_tables, fresh_tables
    assert "alembic_version" in fresh_tables, fresh_tables
    print("1. чистая база:", len(fresh_tables) - 1, "таблиц + alembic_version")

    # 2. Повторный upgrade ничего не ломает.
    run_alembic(fresh, "upgrade", "head")
    print("2. повторный upgrade: ок")

    # 3. База от create_all (до Alembic): миграция не падает.
    legacy = work / "migration_legacy.db"
    legacy.unlink(missing_ok=True)
    sys.path.insert(0, str(BACKEND))
    os.environ["DATABASE_URL"] = f"sqlite:///{legacy.as_posix()}"
    from app.db import engine, init_db  # noqa: PLC0415

    init_db()
    assert "alembic_version" not in tables(legacy)
    run_alembic(legacy, "upgrade", "head")
    assert "alembic_version" in tables(legacy)
    print("3. база от create_all: миграция проставила версию")

    # 4. Старая база без новой колонки: колонка должна добавиться.
    engine.dispose()
    legacy.unlink(missing_ok=True)
    init_db()
    engine.dispose()
    conn = sqlite3.connect(legacy)
    try:
        conn.execute("ALTER TABLE estimates DROP COLUMN share_expires_at")
        conn.commit()
    finally:
        conn.close()
    columns = {row[1] for row in query(legacy, "PRAGMA table_info(estimates)")}
    assert "share_expires_at" not in columns, columns
    run_alembic(legacy, "upgrade", "head")
    columns = {row[1] for row in query(legacy, "PRAGMA table_info(estimates)")}
    assert "share_expires_at" in columns, columns
    print("4. старая база: колонка share_expires_at добавлена")

    # 5. База без token_version: колонка добавляется миграцией.
    engine.dispose()
    conn = sqlite3.connect(legacy)
    try:
        conn.execute("DELETE FROM alembic_version")
        conn.execute("ALTER TABLE users DROP COLUMN token_version")
        conn.commit()
    finally:
        conn.close()
    columns = {row[1] for row in query(legacy, "PRAGMA table_info(users)")}
    assert "token_version" not in columns, columns
    run_alembic(legacy, "upgrade", "head")
    columns = {row[1] for row in query(legacy, "PRAGMA table_info(users)")}
    assert "token_version" in columns, columns
    print("5. старая база: колонка token_version добавлена")

    engine.dispose()
    for path in (fresh, legacy):
        path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
