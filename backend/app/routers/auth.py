from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.schemas import LoginRequest, UserRead
from app.security import (
    CurrentUser,
    clear_auth_cookie,
    create_access_token,
    set_auth_cookie,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, response: Response, session: SessionDep) -> User:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись отключена")

    set_auth_cookie(response, create_access_token(user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
