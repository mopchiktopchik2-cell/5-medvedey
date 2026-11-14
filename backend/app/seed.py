"""Начальные справочники и демо-пользователи."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Branding,
    ComplexityLevel,
    Contractor,
    Fabric,
    Hardware,
    HardwareUnit,
    ProductType,
    Settings,
    User,
    UserRole,
)
from app.security import hash_password

FABRICS = [
    ("Кулирка хлопок 160 г/м²", "180", "480.00", "хлопок 100%"),
    ("Футер 2-нитка 240 г/м²", "180", "720.00", "хлопок 80% / пэ 20%"),
    ("Футер 3-нитка 320 г/м²", "180", "890.00", "хлопок 80% / пэ 20%"),
    ("Интерлок 190 г/м²", "180", "560.00", "хлопок 100%"),
    ("Рибана 220 г/м²", "180", "640.00", "хлопок 95% / эластан 5%"),
    ("Флис 240 г/м²", "180", "610.00", "полиэстер 100%"),
    ("Канвас 320 г/м²", "160", "950.00", "хлопок 100%"),
    ("Оксфорд 210D", "150", "320.00", "полиэстер 100%"),
    ("Полиэстер спортивный 130 г/м²", "150", "390.00", "полиэстер 100%"),
    ("Мешковина джут 240 г/м²", "150", "350.00", "джут 100%"),
]

HARDWARE = [
    ("Пуговица 18 мм", HardwareUnit.PIECE, "6.00"),
    ("Молния тракторная 60 см", HardwareUnit.PIECE, "95.00"),
    ("Нитки (комплект на изделие)", HardwareUnit.PER_ITEM, "45.00"),
    ("Люверс 12 мм", HardwareUnit.PIECE, "25.00"),
    ("Шнур с наконечниками, 1.5 м", HardwareUnit.PER_ITEM, "60.00"),
]

BRANDING = [
    ("Термотрансфер A4", "250.00"),
    ("Шелкография, 1 цвет", "180.00"),
    ("Вышивка до 10×10 см", "320.00"),
]

PRODUCT_TYPES = [
    ("Футболка", "0.60"),
    ("Худи", "1.40"),
    ("Шоппер", "0.50"),
    ("Бейсболка", "0.90"),
]

COMPLEXITY = [
    ("base", "Базовая", "1.00"),
    ("medium", "Средняя", "1.25"),
    ("hard", "Сложная", "1.50"),
]

CONTRACTORS = [
    ("ООО «Ромашка»", "zakaz@romashka.ru", "+7 (912) 000-11-22"),
    ("ИП Смирнов А. В.", "smirnov@mail.ru", "+7 (922) 333-44-55"),
    ("АО «СеверТрейд»", "merch@severtrade.ru", "+7 (3462) 55-66-77"),
]

DEMO_USERS = [
    ("technologist@mir.ru", "Технолог Рязанцева Н. Е.", "technolog123", UserRole.TECHNOLOGIST),
    ("manager@mir.ru", "Менеджер по подрядчикам", "manager123", UserRole.MANAGER),
]


def seed(session: Session) -> None:
    if session.get(Settings, 1) is None:
        session.add(Settings(id=1))

    if session.scalar(select(User).limit(1)) is None:
        for email, name, password, role in DEMO_USERS:
            session.add(
                User(
                    email=email,
                    full_name=name,
                    password_hash=hash_password(password),
                    role=role,
                )
            )

    if session.scalar(select(Fabric).limit(1)) is None:
        for name, width, price, density in FABRICS:
            session.add(
                Fabric(
                    name=name,
                    width_cm=Decimal(width),
                    price_per_m=Decimal(price),
                    density=density,
                )
            )

    if session.scalar(select(Hardware).limit(1)) is None:
        for name, unit, price in HARDWARE:
            session.add(Hardware(name=name, unit=unit, price=Decimal(price)))

    if session.scalar(select(Branding).limit(1)) is None:
        for name, price in BRANDING:
            session.add(Branding(name=name, price=Decimal(price)))

    if session.scalar(select(ProductType).limit(1)) is None:
        for name, hours in PRODUCT_TYPES:
            session.add(ProductType(name=name, base_sewing_hours=Decimal(hours)))

    if session.scalar(select(ComplexityLevel).limit(1)) is None:
        for code, name, factor in COMPLEXITY:
            session.add(ComplexityLevel(code=code, name=name, factor=Decimal(factor)))

    if session.scalar(select(Contractor).limit(1)) is None:
        for name, email, phone in CONTRACTORS:
            session.add(Contractor(name=name, contact_email=email, phone=phone))

    session.commit()
