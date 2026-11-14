"""token_version: отзыв сессий при смене пароля или роли.

Revision ID: b7e2c9d41a10
Revises: fdf8b4b401ff
Create Date: 2026-11-14 20:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c9d41a10"
down_revision: str | None = "fdf8b4b401ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _user_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("users")}


def upgrade() -> None:
    # База могла быть создана приложением через create_all уже с колонкой.
    if "token_version" in _user_columns():
        return
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    if "token_version" in _user_columns():
        op.drop_column("users", "token_version")
