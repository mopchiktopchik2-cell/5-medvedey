from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User, UserRole

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.access_token_ttl_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется вход в систему",
    )
    if not token:
        raise credentials_error

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_technologist(user: CurrentUser) -> User:
    if user.role != UserRole.TECHNOLOGIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Действие доступно только технологу",
        )
    return user


Technologist = Annotated[User, Depends(require_technologist)]
