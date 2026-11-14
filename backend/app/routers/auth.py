from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ratelimit
from app.config import settings
from app.db import get_session
from app.models import User
from app.schemas import LoginRequest, PasswordChangeRequest, UserRead
from app.security import (
    CurrentUser,
    clear_auth_cookie,
    create_access_token,
    hash_password,
    set_auth_cookie,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> User:
    client_ip = request.client.host if request.client else "unknown"
    if ratelimit.is_blocked(client_ip, payload.email):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Слишком много неудачных попыток входа. Попробуйте позже.",
            headers={"Retry-After": str(max(1, settings.login_lockout_minutes) * 60)},
        )

    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        ratelimit.register_failure(client_ip, payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись отключена")

    ratelimit.reset(client_ip, payload.email)
    set_auth_cookie(response, create_access_token(user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    user: CurrentUser,
    session: SessionDep,
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    if payload.current_password == payload.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Новый пароль совпадает с текущим")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    session.commit()
    # После смены пароля закрываются все сессии сотрудника — нужно войти заново.
    clear_auth_cookie(response)
