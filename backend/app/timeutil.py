"""Перевод времени из UTC в местное время цеха.

В базе все моменты времени хранятся в UTC, но SQLite отдаёт их без зоны.
Поэтому naive-datetime трактуем как UTC, а затем сдвигаем на смещение из
настройки ``UTC_OFFSET_HOURS`` — оно же используется в фильтрах истории,
PDF, письмах и CSV.
"""

from datetime import UTC, date, datetime, time, timedelta, timezone

from app.config import settings


def _offset() -> timedelta:
    return timedelta(hours=settings.utc_offset_hours)


def to_local(value: datetime) -> datetime:
    """UTC-время из базы → местное время цеха (с явной зоной)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone(_offset()))


def day_start_utc(value: date) -> datetime:
    """Полночь местного дня в UTC (с явной зоной — для SQLite и PostgreSQL)."""
    return (datetime.combine(value, time.min) - _offset()).replace(tzinfo=UTC)


def next_day_start_utc(value: date) -> datetime:
    """Начало следующего местного дня в UTC."""
    return (datetime.combine(value + timedelta(days=1), time.min) - _offset()).replace(tzinfo=UTC)
