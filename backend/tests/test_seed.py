"""Наполнение справочников: заказчик ждёт минимум из ТЗ."""

from sqlalchemy import func, select

from app.models import (
    Branding,
    ComplexityLevel,
    Contractor,
    Fabric,
    Hardware,
    ProductType,
    Settings,
)
from app.seed import seed


def test_seed_fills_minimum_dictionaries(session_factory) -> None:
    with session_factory() as session:
        assert session.get(Settings, 1) is not None
        assert session.scalar(select(func.count()).select_from(Fabric)) >= 10
        assert session.scalar(select(func.count()).select_from(Hardware)) >= 5
        assert session.scalar(select(func.count()).select_from(ProductType)) >= 4
        assert session.scalar(select(func.count()).select_from(ComplexityLevel)) >= 3
        assert session.scalar(select(func.count()).select_from(Branding)) >= 3
        assert session.scalar(select(func.count()).select_from(Contractor)) >= 1


def test_seed_is_idempotent(session_factory) -> None:
    with session_factory() as session:
        before = session.scalar(select(func.count()).select_from(Fabric))
        seed(session)
        after = session.scalar(select(func.count()).select_from(Fabric))

    assert before == after
