"""Управление сотрудниками цеха: доступно только технологу."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, UserRole
from app.schemas import UserAdminRead, UserCreate, UserUpdate
from app.security import Technologist, hash_password

router = APIRouter(prefix="/users", tags=["users"])

SessionDep = Annotated[Session, Depends(get_session)]


def _active_technologists(session: Session) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.TECHNOLOGIST, User.is_active.is_(True))
        )
        or 0
    )


def _get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
    return user


@router.get("", response_model=list[UserAdminRead])
def list_users(session: SessionDep, _: Technologist) -> list[User]:
    return list(session.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserAdminRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: SessionDep, _: Technologist) -> User:
    email = str(payload.email).lower()
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Сотрудник с таким email уже существует")

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserAdminRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: SessionDep,
    current: Technologist,
) -> User:
    user = _get_user(session, user_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)

    # Сравниваем с текущими значениями: сохранение формы без изменений
    # не должно отзывать сессии сотрудника.
    role_changed = "role" in changes and changes["role"] != user.role
    active_changed = "is_active" in changes and changes["is_active"] != user.is_active
    password_changed = "password" in changes
    demoting = (role_changed and changes["role"] == UserRole.MANAGER) or (
        active_changed and changes["is_active"] is False
    )
    if user.id == current.id and demoting:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Нельзя отключить или понизить собственную учётную запись",
        )
    if (
        demoting
        and user.role == UserRole.TECHNOLOGIST
        and user.is_active
        and _active_technologists(session) <= 1
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "В системе должен остаться хотя бы один активный технолог",
        )

    if "full_name" in changes:
        user.full_name = changes["full_name"].strip()
    if role_changed:
        user.role = changes["role"]
    if active_changed:
        user.is_active = changes["is_active"]
    if password_changed:
        user.password_hash = hash_password(changes["password"])
    if role_changed or active_changed or password_changed:
        # Роль и пароль вшиты в токен: старые сессии должны закончиться.
        user.token_version += 1

    session.commit()
    session.refresh(user)
    return user
