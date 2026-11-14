from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    MANAGER = "manager"
    TECHNOLOGIST = "technologist"


class HardwareUnit(StrEnum):
    PIECE = "piece"  # цена за штуку, количество на одно изделие
    PER_ITEM = "per_item"  # фиксированная сумма на изделие


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.MANAGER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    estimates: Mapped[list["Estimate"]] = relationship(back_populates="author")


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    contact_email: Mapped[str | None] = mapped_column(String(120), default=None)
    phone: Mapped[str | None] = mapped_column(String(40), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    estimates: Mapped[list["Estimate"]] = relationship(back_populates="contractor")


class Fabric(Base):
    __tablename__ = "fabrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    width_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    price_per_m: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    density: Mapped[str | None] = mapped_column(String(60), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Hardware(Base):
    __tablename__ = "hardware"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    unit: Mapped[str] = mapped_column(String(20), default=HardwareUnit.PIECE)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Branding(Base):
    __tablename__ = "branding"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProductType(Base):
    __tablename__ = "product_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    base_sewing_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ComplexityLevel(Base):
    __tablename__ = "complexity_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    factor: Mapped[Decimal] = mapped_column(Numeric(5, 2))


class Settings(Base):
    """Единственная строка (id=1) с настройками технолога."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    sewing_normohour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("850.00"))
    cutting_normohour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("700.00"))
    waste_coefficient: Mapped[Decimal] = mapped_column(Numeric(5, 3), default=Decimal("0.18"))
    cutting_rate_parts_per_hour: Mapped[int] = mapped_column(Integer, default=60)
    seam_allowance_cm: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("1.5"))
    lining_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.15"))
    hood_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.10"))
    pockets_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.08"))
    daily_capacity_units: Mapped[int] = mapped_column(Integer, default=80)
    lead_time_buffer_days: Mapped[int] = mapped_column(Integer, default=2)
    company_name: Mapped[str] = mapped_column(String(160), default="Швейный цех «М.и.Р.»")
    company_requisites: Mapped[str] = mapped_column(
        Text,
        default="г. Сургут, ул. Комплектовочная, 5 · +7 (922) 418-36-33 · Kolibriatelye@mail.ru",
    )


class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, default="")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"), default=None)
    contractor_name: Mapped[str | None] = mapped_column(String(160), default=None)

    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_types.id"))
    product_type_name: Mapped[str] = mapped_column(String(120))
    complexity_id: Mapped[int] = mapped_column(ForeignKey("complexity_levels.id"))
    complexity_name: Mapped[str] = mapped_column(String(80))
    complexity_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    quantity: Mapped[int] = mapped_column(Integer)
    has_lining: Mapped[bool] = mapped_column(Boolean, default=False)
    has_hood: Mapped[bool] = mapped_column(Boolean, default=False)
    has_pockets: Mapped[bool] = mapped_column(Boolean, default=False)

    fabric_id: Mapped[int | None] = mapped_column(ForeignKey("fabrics.id"), default=None)
    fabric_name: Mapped[str] = mapped_column(String(120))
    fabric_width_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    fabric_price_per_m: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    waste_coefficient: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    seam_allowance_cm: Mapped[Decimal] = mapped_column(Numeric(4, 1))

    sewing_hours: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    sewing_normohour: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sewing_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cutting_hours: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    cutting_normohour: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cutting_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    material_length_m: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    material_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    hardware_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    branding_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=1)

    notes: Mapped[str | None] = mapped_column(Text, default=None)
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    share_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def author_name(self) -> str | None:
        return self.author.full_name if self.author else None

    @property
    def contractor_email(self) -> str | None:
        return self.contractor.contact_email if self.contractor else None

    author: Mapped[User] = relationship(back_populates="estimates")
    contractor: Mapped[Contractor | None] = relationship(back_populates="estimates")
    parts: Mapped[list["EstimatePart"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan"
    )
    hardware_items: Mapped[list["EstimateHardware"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan"
    )
    branding_items: Mapped[list["EstimateBranding"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan"
    )


class EstimatePart(Base):
    __tablename__ = "estimate_parts"
    __table_args__ = (UniqueConstraint("estimate_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("estimates.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    length_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    width_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    count_per_unit: Mapped[int] = mapped_column(Integer, default=1)

    estimate: Mapped[Estimate] = relationship(back_populates="parts")


class EstimateHardware(Base):
    __tablename__ = "estimate_hardware"

    id: Mapped[int] = mapped_column(primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("estimates.id"), index=True)
    hardware_id: Mapped[int | None] = mapped_column(ForeignKey("hardware.id"), default=None)
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    @property
    def qty_per_unit(self) -> Decimal:
        return self.qty

    estimate: Mapped[Estimate] = relationship(back_populates="hardware_items")


class EstimateBranding(Base):
    __tablename__ = "estimate_branding"

    id: Mapped[int] = mapped_column(primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("estimates.id"), index=True)
    branding_id: Mapped[int | None] = mapped_column(ForeignKey("branding.id"), default=None)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    positions: Mapped[int] = mapped_column(Integer, default=1)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    estimate: Mapped[Estimate] = relationship(back_populates="branding_items")
