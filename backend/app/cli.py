"""Служебные команды для первого запуска и восстановления доступа.

Примеры:
    python -m app.cli create-user --email boss@example.ru --name "Иванов И. И."
    python -m app.cli reset-password --email manager@mir.ru

Пароль спрашивается интерактивно, если не передан через ``--password``.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import User, UserRole
from app.security import hash_password

MIN_PASSWORD = 8


def _read_password(raw: str | None) -> str:
    password = raw if raw is not None else getpass.getpass("Пароль: ")
    if len(password) < MIN_PASSWORD:
        print(
            f"Пароль должен быть не короче {MIN_PASSWORD} символов",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return password


def create_user(args: argparse.Namespace) -> int:
    email = args.email.strip().lower()
    password = _read_password(args.password)
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == email)) is not None:
            print(f"Сотрудник {email} уже существует", file=sys.stderr)
            return 1
        session.add(
            User(
                email=email,
                full_name=(args.name or email).strip(),
                password_hash=hash_password(password),
                role=args.role,
            )
        )
        session.commit()
    print(f"Создан сотрудник {email} с ролью «{args.role}»")
    return 0


def reset_password(args: argparse.Namespace) -> int:
    email = args.email.strip().lower()
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"Сотрудник {email} не найден", file=sys.stderr)
            return 1
        user.password_hash = hash_password(_read_password(args.password))
        session.commit()
    print(f"Пароль для {email} обновлён")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.cli",
        description="Служебные команды калькулятора себестоимости",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-user", help="Создать сотрудника цеха")
    create.add_argument("--email", required=True)
    create.add_argument("--password", default=None, help="Если не указан — спросим интерактивно")
    create.add_argument("--name", default="", help="ФИО сотрудника")
    create.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.TECHNOLOGIST.value,
    )
    create.set_defaults(func=create_user)

    reset = subparsers.add_parser("reset-password", help="Сбросить пароль сотрудника")
    reset.add_argument("--email", required=True)
    reset.add_argument("--password", default=None, help="Если не указан — спросим интерактивно")
    reset.set_defaults(func=reset_password)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    init_db()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
