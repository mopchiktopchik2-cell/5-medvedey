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

    demoting = changes.get("role") == UserRole.MANAGER or changes.get("is_active") is False
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
    if "role" in changes:
        user.role = changes["role"]
    if "is_active" in changes:
        user.is_active = changes["is_active"]
    if "password" in changes:
        user.password_hash = hash_password(changes["password"])
    if {"role", "is_active", "password"} & changes.keys():
        # Роль и пароль вшиты в токен: старые сессии должны закончиться.
        user.token_version += 1

    session.commit()
    session.refresh(user)
    return user
