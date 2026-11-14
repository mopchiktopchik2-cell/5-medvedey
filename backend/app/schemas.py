from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

MoneyIn = Decimal
NumberOut = Annotated[
    Decimal, PlainSerializer(lambda value: float(value), return_type=float, when_used="json")
]
MoneyOut = Annotated[
    Decimal,
    PlainSerializer(lambda value: round(float(value), 2), return_type=float, when_used="json"),
]


# --- авторизация ---


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str


# --- справочники ---


class FabricBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    width_cm: MoneyIn = Field(gt=0, le=1000)
    price_per_m: MoneyIn = Field(ge=0)
    density: str | None = Field(default=None, max_length=60)
    is_active: bool = True


class FabricRead(FabricBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    width_cm: NumberOut
    price_per_m: MoneyOut


class HardwareBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit: Literal["piece", "per_item"] = "piece"
    price: MoneyIn = Field(ge=0)
    is_active: bool = True


class HardwareRead(HardwareBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: MoneyOut


class BrandingBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: MoneyIn = Field(ge=0)
    is_active: bool = True


class BrandingRead(BrandingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: MoneyOut


class ProductTypeBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_sewing_hours: MoneyIn = Field(gt=0)
    is_active: bool = True


class ProductTypeRead(ProductTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    base_sewing_hours: NumberOut


class ComplexityBase(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    factor: MoneyIn = Field(gt=0)


class ComplexityRead(ComplexityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    factor: NumberOut


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sewing_normohour: MoneyOut
    cutting_normohour: MoneyOut
    waste_coefficient: NumberOut
    cutting_rate_parts_per_hour: int
    seam_allowance_cm: NumberOut
    lining_factor: NumberOut
    hood_factor: NumberOut
    pockets_factor: NumberOut
    daily_capacity_units: int
    lead_time_buffer_days: int
    company_name: str
    company_requisites: str


class SettingsUpdate(BaseModel):
    sewing_normohour: Decimal | None = Field(default=None, gt=0)
    cutting_normohour: Decimal | None = Field(default=None, gt=0)
    waste_coefficient: Decimal | None = Field(default=None, ge=0, le=1)
    cutting_rate_parts_per_hour: int | None = Field(default=None, gt=0)
    seam_allowance_cm: Decimal | None = Field(default=None, ge=0, le=10)
    lining_factor: Decimal | None = Field(default=None, gt=0, le=3)
    hood_factor: Decimal | None = Field(default=None, gt=0, le=3)
    pockets_factor: Decimal | None = Field(default=None, gt=0, le=3)
    daily_capacity_units: int | None = Field(default=None, gt=0)
    lead_time_buffer_days: int | None = Field(default=None, ge=0, le=60)
    company_name: str | None = Field(default=None, min_length=1, max_length=160)
    company_requisites: str | None = Field(default=None, max_length=500)


class DictionariesRead(BaseModel):
    fabrics: list[FabricRead]
    hardware: list[HardwareRead]
    branding: list[BrandingRead]
    product_types: list[ProductTypeRead]
    complexity_levels: list[ComplexityRead]
    contractors: list["ContractorRead"]
    settings: SettingsRead


# --- подрядчики ---


class ContractorBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class ContractorRead(ContractorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- расчёт ---


class PartIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    length_cm: Decimal = Field(gt=0, le=500)
    width_cm: Decimal = Field(gt=0, le=500)
    count_per_unit: int = Field(ge=1, le=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class HardwareLineIn(BaseModel):
    hardware_id: int
    qty_per_unit: Decimal = Field(default=Decimal(1), ge=0, le=1000)


class BrandingLineIn(BaseModel):
    branding_id: int
    positions: int = Field(default=1, ge=0, le=20)


class EstimateRequest(BaseModel):
    product_type_id: int
    complexity_id: int
    quantity: int = Field(ge=1, le=100_000)

    has_lining: bool = False
    has_hood: bool = False
    has_pockets: bool = False

    fabric_id: int
    fabric_width_cm: Decimal | None = Field(default=None, gt=0, le=1000)
    fabric_price_per_m: Decimal | None = Field(default=None, ge=0)
    waste_coefficient: Decimal | None = Field(default=None, ge=0, le=1)
    seam_allowance_cm: Decimal | None = Field(default=None, ge=0, le=10)

    parts: list[PartIn] = Field(min_length=1, max_length=20)
    hardware: list[HardwareLineIn] = Field(default_factory=list, max_length=30)
    branding: list[BrandingLineIn] = Field(default_factory=list, max_length=20)

    contractor_id: int | None = None
    contractor_name: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)


class LayoutRowRead(BaseModel):
    pieces: int
    height_cm: NumberOut
    used_width_cm: NumberOut


class SewingBreakdown(BaseModel):
    base_hours_per_unit: NumberOut
    complexity_factor: NumberOut
    modifier: NumberOut
    hours: NumberOut
    normohour: MoneyOut
    cost: MoneyOut


class CuttingBreakdown(BaseModel):
    pieces_total: int
    rows: list[LayoutRowRead]
    rows_total: int
    rows_truncated: bool
    length_cm: NumberOut
    length_with_waste_m: NumberOut
    approximate: bool
    hours: NumberOut
    normohour: MoneyOut
    cost: MoneyOut


class MaterialBreakdown(BaseModel):
    fabric_name: str
    roll_width_cm: NumberOut
    length_with_waste_m: NumberOut
    price_per_m: MoneyOut
    waste_coefficient: NumberOut
    seam_allowance_cm: NumberOut
    cost: MoneyOut


class HardwareLineRead(BaseModel):
    hardware_id: int | None
    name: str
    unit: str
    price: MoneyOut
    qty_per_unit: NumberOut
    total: MoneyOut


class BrandingLineRead(BaseModel):
    branding_id: int | None
    name: str
    price: MoneyOut
    positions: int
    total: MoneyOut


class TotalsRead(BaseModel):
    material_cost: MoneyOut
    cutting_cost: MoneyOut
    sewing_cost: MoneyOut
    hardware_cost: MoneyOut
    branding_cost: MoneyOut
    total_cost: MoneyOut
    unit_cost: MoneyOut
    quantity: int


class EstimatePreview(BaseModel):
    sewing: SewingBreakdown
    cutting: CuttingBreakdown
    material: MaterialBreakdown
    hardware: list[HardwareLineRead]
    branding: list[BrandingLineRead]
    totals: TotalsRead
    lead_time_days: int
    warnings: list[str] = []


class EstimatePartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    length_cm: NumberOut
    width_cm: NumberOut
    count_per_unit: int


class EstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    created_at: datetime
    author_id: int
    author_name: str | None = None
    contractor_name: str | None
    product_type_name: str
    complexity_name: str
    complexity_factor: NumberOut
    quantity: int
    has_lining: bool
    has_hood: bool
    has_pockets: bool
    fabric_name: str
    fabric_width_cm: NumberOut
    fabric_price_per_m: MoneyOut
    waste_coefficient: NumberOut
    seam_allowance_cm: NumberOut
    sewing_hours: NumberOut
    sewing_normohour: MoneyOut
    sewing_cost: MoneyOut
    cutting_hours: NumberOut
    cutting_normohour: MoneyOut
    cutting_cost: MoneyOut
    material_length_m: NumberOut
    material_cost: MoneyOut
    hardware_cost: MoneyOut
    branding_cost: MoneyOut
    total_cost: MoneyOut
    unit_cost: MoneyOut
    lead_time_days: int
    notes: str | None
    share_token: str | None
    parts: list[EstimatePartRead]
    hardware_items: list[HardwareLineRead]
    branding_items: list[BrandingLineRead]


class EstimateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    created_at: datetime
    contractor_name: str | None
    product_type_name: str
    quantity: int
    total_cost: MoneyOut
    unit_cost: MoneyOut
    author_name: str | None = None


class EstimateListResponse(BaseModel):
    items: list[EstimateListItem]
    total: int


DictionariesRead.model_rebuild()
