"""Расчёт сметы: чистые функции + сборка результата для API и БД."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import calculators
from app.calculators import PartInput
from app.models import (
    Branding,
    ComplexityLevel,
    Fabric,
    Hardware,
    HardwareUnit,
    ProductType,
    Settings,
)
from app.schemas import (
    BrandingLineRead,
    CuttingBreakdown,
    EstimatePreview,
    EstimateRequest,
    HardwareLineRead,
    LayoutRowRead,
    MaterialBreakdown,
    SewingBreakdown,
    TotalsRead,
)

DEFAULT_WASTE = Decimal("0.18")
WASTE_RANGE = (Decimal("0.15"), Decimal("0.20"))


class CalculationError(ValueError):
    """Ошибка входных данных расчёта — отдаётся клиенту как 400."""


@dataclass
class CalculatedEstimate:
    preview: EstimatePreview
    product_type: ProductType
    complexity: ComplexityLevel
    fabric: Fabric
    settings: Settings
    hardware_lines: list[tuple[Hardware, Decimal, Decimal]]
    branding_lines: list[tuple[Branding, int, Decimal]]
    parts: list[PartInput]
    roll_width_cm: Decimal
    price_per_m: Decimal
    waste_coefficient: Decimal
    seam_allowance_cm: Decimal
    modifier: Decimal


def get_settings_row(session: Session) -> Settings:
    row = session.get(Settings, 1)
    if row is None:
        row = Settings(id=1)
        session.add(row)
        session.flush()
    return row


def _resolve(session: Session, payload: EstimateRequest) -> tuple:
    product_type = session.get(ProductType, payload.product_type_id)
    if product_type is None or not product_type.is_active:
        raise CalculationError("Тип изделия не найден")

    complexity = session.get(ComplexityLevel, payload.complexity_id)
    if complexity is None:
        raise CalculationError("Коэффициент сложности не найден")

    fabric = session.get(Fabric, payload.fabric_id)
    if fabric is None or not fabric.is_active:
        raise CalculationError("Ткань не найдена")

    settings_row = get_settings_row(session)
    return product_type, complexity, fabric, settings_row


def calculate(session: Session, payload: EstimateRequest) -> CalculatedEstimate:
    product_type, complexity, fabric, settings_row = _resolve(session, payload)
    warnings: list[str] = []

    quantity = payload.quantity
    roll_width = payload.fabric_width_cm or fabric.width_cm
    price_per_m = (
        payload.fabric_price_per_m if payload.fabric_price_per_m is not None else fabric.price_per_m
    )
    waste = (
        payload.waste_coefficient
        if payload.waste_coefficient is not None
        else settings_row.waste_coefficient
    )
    seam = (
        payload.seam_allowance_cm
        if payload.seam_allowance_cm is not None
        else settings_row.seam_allowance_cm
    )

    if not (WASTE_RANGE[0] <= waste <= WASTE_RANGE[1]):
        warnings.append(f"Коэффициент отходов {waste * 100:.0f}% вне обычного диапазона 15–20%")

    modifier = calculators.sewing_modifier(
        payload.has_lining,
        payload.has_hood,
        payload.has_pockets,
        settings_row.lining_factor,
        settings_row.hood_factor,
        settings_row.pockets_factor,
    )

    parts = [
        PartInput(
            name=item.name,
            length_cm=Decimal(item.length_cm),
            width_cm=Decimal(item.width_cm),
            count_per_unit=item.count_per_unit,
        )
        for item in payload.parts
    ]

    try:
        sewing_hours, sewing_cost = calculators.calculate_sewing(
            base_hours_per_unit=Decimal(product_type.base_sewing_hours),
            complexity_factor=Decimal(complexity.factor),
            quantity=quantity,
            normohour=Decimal(settings_row.sewing_normohour),
            modifier=modifier,
        )
        cutting = calculators.calculate_cutting(
            parts=parts,
            quantity=quantity,
            roll_width_cm=Decimal(roll_width),
            waste_coefficient=Decimal(waste),
            seam_allowance_cm=Decimal(seam),
        )
        cutting_hours, cutting_cost = calculators.calculate_cutting_work(
            pieces_total=cutting.pieces_total,
            rate_parts_per_hour=settings_row.cutting_rate_parts_per_hour,
            normohour=Decimal(settings_row.cutting_normohour),
        )
    except ValueError as exc:
        raise CalculationError(str(exc)) from exc

    material_cost = calculators.money(cutting.length_with_waste_m * Decimal(price_per_m))

    hardware_lines: list[tuple[Hardware, Decimal, Decimal]] = []
    for line in payload.hardware:
        item = session.get(Hardware, line.hardware_id)
        if item is None or not item.is_active:
            raise CalculationError("Позиция фурнитуры не найдена")
        if item.unit == HardwareUnit.PER_ITEM:
            total = calculators.money(Decimal(item.price) * quantity)
        else:
            total = calculators.money(Decimal(item.price) * Decimal(line.qty_per_unit) * quantity)
        hardware_lines.append((item, Decimal(line.qty_per_unit), total))

    branding_lines: list[tuple[Branding, int, Decimal]] = []
    for line in payload.branding:
        item = session.get(Branding, line.branding_id)
        if item is None or not item.is_active:
            raise CalculationError("Позиция брендирования не найдена")
        total = calculators.money(Decimal(item.price) * line.positions * quantity)
        branding_lines.append((item, line.positions, total))

    hardware_cost = calculators.money(sum((line[2] for line in hardware_lines), Decimal("0")))
    branding_cost = calculators.money(sum((line[2] for line in branding_lines), Decimal("0")))

    totals = calculators.summarize(
        material_cost=material_cost,
        cutting_cost=cutting_cost,
        sewing_cost=sewing_cost,
        hardware_cost=hardware_cost,
        branding_cost=branding_cost,
        quantity=quantity,
    )

    preview = EstimatePreview(
        sewing=SewingBreakdown(
            base_hours_per_unit=Decimal(product_type.base_sewing_hours),
            complexity_factor=Decimal(complexity.factor),
            modifier=modifier,
            hours=sewing_hours,
            normohour=Decimal(settings_row.sewing_normohour),
            cost=sewing_cost,
        ),
        cutting=CuttingBreakdown(
            pieces_total=cutting.pieces_total,
            rows=[
                LayoutRowRead(
                    pieces=row.pieces,
                    height_cm=row.height_cm,
                    used_width_cm=row.used_width_cm,
                )
                for row in cutting.rows
            ],
            rows_total=cutting.rows_total,
            rows_truncated=cutting.rows_truncated,
            length_cm=cutting.length_cm,
            length_with_waste_m=cutting.length_with_waste_m,
            approximate=cutting.approximate,
            hours=cutting_hours,
            normohour=Decimal(settings_row.cutting_normohour),
            cost=cutting_cost,
        ),
        material=MaterialBreakdown(
            fabric_name=fabric.name,
            roll_width_cm=Decimal(roll_width),
            length_with_waste_m=cutting.length_with_waste_m,
            price_per_m=Decimal(price_per_m),
            waste_coefficient=Decimal(waste),
            seam_allowance_cm=Decimal(seam),
            cost=material_cost,
        ),
        hardware=[
            HardwareLineRead(
                hardware_id=item.id,
                name=item.name,
                unit=item.unit,
                price=Decimal(item.price),
                qty_per_unit=qty,
                total=total,
            )
            for item, qty, total in hardware_lines
        ],
        branding=[
            BrandingLineRead(
                branding_id=item.id,
                name=item.name,
                price=Decimal(item.price),
                positions=positions,
                total=total,
            )
            for item, positions, total in branding_lines
        ],
        totals=TotalsRead(
            material_cost=totals.material_cost,
            cutting_cost=totals.cutting_cost,
            sewing_cost=totals.sewing_cost,
            hardware_cost=totals.hardware_cost,
            branding_cost=totals.branding_cost,
            total_cost=totals.total_cost,
            unit_cost=totals.unit_cost,
            quantity=quantity,
        ),
        lead_time_days=calculators.lead_time_days(
            quantity,
            settings_row.daily_capacity_units,
            settings_row.lead_time_buffer_days,
        ),
        warnings=warnings,
    )

    return CalculatedEstimate(
        preview=preview,
        product_type=product_type,
        complexity=complexity,
        fabric=fabric,
        settings=settings_row,
        hardware_lines=hardware_lines,
        branding_lines=branding_lines,
        parts=parts,
        roll_width_cm=Decimal(roll_width),
        price_per_m=Decimal(price_per_m),
        waste_coefficient=Decimal(waste),
        seam_allowance_cm=Decimal(seam),
        modifier=modifier,
    )


def active(session: Session, model: type) -> list:
    return list(session.scalars(select(model).order_by(model.id)))
