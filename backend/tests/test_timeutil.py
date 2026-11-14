"""Местное время цеха: смещение и границы дня для фильтров истории."""

from datetime import UTC, date, datetime

from app import timeutil
from app.config import settings


def test_to_local_applies_configured_offset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "utc_offset_hours", 5)

    local = timeutil.to_local(datetime(2026, 3, 4, 20, 30))

    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 3, 5, 1, 30)
    assert local.utcoffset().total_seconds() == 5 * 3600


def test_aware_utc_is_converted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "utc_offset_hours", 5)

    local = timeutil.to_local(datetime(2026, 3, 4, 20, 30, tzinfo=UTC))

    assert (local.hour, local.day) == (1, 5)


def test_day_bounds_are_shifted_to_local_midnight(monkeypatch) -> None:
    monkeypatch.setattr(settings, "utc_offset_hours", 5)

    assert timeutil.day_start_utc(date(2026, 3, 4)) == datetime(2026, 3, 3, 19, 0, tzinfo=UTC)
    assert timeutil.next_day_start_utc(date(2026, 3, 4)) == datetime(2026, 3, 4, 19, 0, tzinfo=UTC)
