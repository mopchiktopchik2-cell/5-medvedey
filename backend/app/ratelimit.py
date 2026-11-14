"""Защита от перебора пароля при входе.

Счётчик неудачных попыток ведётся в памяти процесса по паре
«адрес клиента + email». При нескольких воркерах лимит действует на каждый
процесс отдельно — для цеха этого достаточно, а внешний rate-limit можно
повесить на reverse proxy. Успешный вход сбрасывает счётчик.
"""

from __future__ import annotations

import time
from collections import deque

from app.config import settings

Window = deque[float]

_failures: dict[tuple[str, str], Window] = {}


def _key(ip: str, email: str) -> tuple[str, str]:
    return (ip, email.strip().lower())


def _window_seconds() -> float:
    return max(1, settings.login_lockout_minutes) * 60


def _prune(bucket: Window, now: float) -> None:
    window = _window_seconds()
    while bucket and now - bucket[0] > window:
        bucket.popleft()


def is_blocked(ip: str, email: str) -> bool:
    """True, если попытки исчерпаны и вход временно запрещён."""
    key = _key(ip, email)
    bucket = _failures.get(key)
    if not bucket:
        return False
    _prune(bucket, time.monotonic())
    if not bucket:
        _failures.pop(key, None)
        return False
    return len(bucket) >= max(1, settings.login_max_attempts)


def register_failure(ip: str, email: str) -> None:
    key = _key(ip, email)
    now = time.monotonic()
    bucket = _failures.setdefault(key, deque())
    _prune(bucket, now)
    bucket.append(now)


def reset(ip: str, email: str) -> None:
    """Забыть неудачные попытки — вызывается после успешного входа."""
    _failures.pop(_key(ip, email), None)


def reset_all() -> None:
    """Полный сброс счётчиков (используется в тестах)."""
    _failures.clear()
