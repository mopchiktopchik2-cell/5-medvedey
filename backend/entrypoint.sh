#!/bin/sh
set -e

# Миграции применяются до старта приложения: на пустой базе они создают схему,
# на базе, созданной старым `create_all`, — только доводят её до актуального вида.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
