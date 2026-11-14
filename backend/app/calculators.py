"""Чистые функции расчёта себестоимости.

Все вычисления — в Decimal, округление до копеек выполняется только
в конце (``quantize``), чтобы промежуточные погрешности не накапливались.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

MAX_PIECES = 20_000
MAX_ROWS_IN_RESPONSE = 120

MONEY = Decimal("0.01")
LENGTH = Decimal("0.001")
HOURS = Decimal("0.001")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY)


def _dec(value: Decimal | int | str | float) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class PartInput:
    """Деталь кроя: габариты прямоугольника в сантиметрах."""

    name: str
    length_cm: Decimal
    width_cm: Decimal
    count_per_unit: int = 1


@dataclass(frozen=True)
class LayoutRow:
    """Ряд раскладки: сколько деталей и какой высоты полоса ткани."""

    pieces: int
    height_cm: Decimal
    used_width_cm: Decimal


@dataclass(frozen=True)
class CuttingResult:
    pieces_total: int
    rows: list[LayoutRow] = field(default_factory=list)
    rows_total: int = 0
    length_cm: Decimal = Decimal("0")
    length_with_waste_m: Decimal = Decimal("0")
    area_cm2: Decimal = Decimal("0")
    approximate: bool = False

    @property
    def rows_truncated(self) -> bool:
        return self.rows_total > len(self.rows)


def _resize(part: PartInput, allowance_cm: Decimal) -> tuple[Decimal, Decimal]:
    """Габариты детали с припусками на швы с обеих сторон."""
    pad = allowance_cm * 2
    return part.length_cm + pad, part.width_cm + pad


def _pack(rects: Iterable[tuple[Decimal, Decimal]], roll_width: Decimal) -> list[LayoutRow]:
    """Раскладка «полками» (next-fit decreasing height) с поворотом деталей.

    Детали сортируются по убыванию высоты и укладываются в полосы по ширине
    рулона. Деталь можно повернуть на 90°, если так она влезает в остаток
    полосы или в рулон целиком.
    """
    rows: list[LayoutRow] = []
    current_width = Decimal("0")
    current_height = Decimal("0")
    current_pieces = 0

    for height, width in sorted(rects, key=lambda rect: rect[0], reverse=True):
        if height > width and height > roll_width:
            height, width = width, height

        if width > roll_width:
            raise ValueError("Деталь шире рулона — уменьшите размер или возьмите ткань шире")

        fits = current_width + width <= roll_width
        if not fits and height <= roll_width and current_width + height <= roll_width:
            # поворот помогает вписать деталь в текущую полосу
            height, width = width, height
            fits = True

        if fits:
            current_width += width
            current_height = max(current_height, height)
            current_pieces += 1
        else:
            if current_pieces:
                rows.append(LayoutRow(current_pieces, current_height, current_width))
            current_width = width
            current_height = height
            current_pieces = 1

    if current_pieces:
        rows.append(LayoutRow(current_pieces, current_height, current_width))

    return rows


def calculate_cutting(
    parts: list[PartInput],
    quantity: int,
    roll_width_cm: Decimal,
    waste_coefficient: Decimal,
    seam_allowance_cm: Decimal,
) -> CuttingResult:
    if quantity <= 0:
        raise ValueError("Тираж должен быть больше нуля")
    if roll_width_cm <= 0:
        raise ValueError("Ширина рулона должна быть больше нуля")
    if not parts:
        raise ValueError("Добавьте хотя бы одну деталь кроя")

    pieces_per_unit = sum(part.count_per_unit for part in parts)
    pieces_total = pieces_per_unit * quantity

    # Очень крупные тиражи считаем партиями и масштабируем длину — раскладка
    # деталей периодична, поэтому относительная погрешность мала.
    units_per_batch = max(1, MAX_PIECES // max(pieces_per_unit, 1))
    units_in_batch = min(quantity, units_per_batch)
    approximate = units_in_batch < quantity

    rects: list[tuple[Decimal, Decimal]] = []
    area_cm2 = Decimal("0")
    for part in parts:
        height, width = _resize(part, seam_allowance_cm)
        area_cm2 += height * width * part.count_per_unit * units_in_batch
        rects.extend([(height, width)] * (part.count_per_unit * units_in_batch))

    rows = _pack(rects, roll_width_cm)
    length_batch_cm = sum((row.height_cm for row in rows), Decimal("0"))

    scale = Decimal(quantity) / Decimal(units_in_batch)
    length_cm = length_batch_cm * scale
    length_with_waste_m = (length_cm / Decimal(100)) * (Decimal(1) + waste_coefficient)

    return CuttingResult(
        pieces_total=pieces_total,
        rows=rows[:MAX_ROWS_IN_RESPONSE],
        rows_total=len(rows),
        length_cm=length_cm.quantize(Decimal("0.1")),
        length_with_waste_m=length_with_waste_m.quantize(LENGTH),
        area_cm2=(area_cm2 * scale).quantize(Decimal("0.1")),
        approximate=approximate,
    )


def sewing_modifier(
    has_lining: bool,
    has_hood: bool,
    has_pockets: bool,
    lining_factor: Decimal,
    hood_factor: Decimal,
    pockets_factor: Decimal,
) -> Decimal:
    factor = Decimal(1)
    if has_lining:
        factor *= lining_factor
    if has_hood:
        factor *= hood_factor
    if has_pockets:
        factor *= pockets_factor
    return factor


def calculate_sewing(
    base_hours_per_unit: Decimal,
    complexity_factor: Decimal,
    quantity: int,
    normohour: Decimal,
    modifier: Decimal = Decimal(1),
) -> tuple[Decimal, Decimal]:
    """Возвращает (трудоёмкость в часах, стоимость пошива)."""
    if quantity <= 0:
        raise ValueError("Тираж должен быть больше нуля")
    hours = base_hours_per_unit * complexity_factor * Decimal(quantity) * modifier
    return hours.quantize(HOURS), money(hours * normohour)


def calculate_cutting_work(
    pieces_total: int,
    rate_parts_per_hour: int,
    normohour: Decimal,
) -> tuple[Decimal, Decimal]:
    if rate_parts_per_hour <= 0:
        raise ValueError("Норма выработки раскройщика должна быть больше нуля")
    hours = Decimal(pieces_total) / Decimal(rate_parts_per_hour)
    return hours.quantize(HOURS), money(hours * normohour)


def calculate_hardware_total(
    items: Iterable[tuple[Decimal, Decimal, int, int]],
) -> Decimal:
    """items: (цена, количество на изделие, тираж, is_per_item).

    is_per_item=1 — фиксированная сумма на изделие, 0 — за штуку.
    """
    total = Decimal("0")
    for price, qty_per_unit, quantity, is_per_item in items:
        if is_per_item:
            total += price * Decimal(quantity)
        else:
            total += price * qty_per_unit * Decimal(quantity)
    return money(total)


def calculate_branding_total(
    items: Iterable[tuple[Decimal, int, int]],
) -> Decimal:
    """items: (цена за позицию, позиций на изделие, тираж)."""
    total = Decimal("0")
    for price, positions, quantity in items:
        total += price * Decimal(positions) * Decimal(quantity)
    return money(total)


def lead_time_days(quantity: int, daily_capacity: int, buffer_days: int) -> int:
    if daily_capacity <= 0:
        daily_capacity = 1
    days = -(-quantity // daily_capacity)  # округление вверх
    return days + buffer_days


@dataclass(frozen=True)
class EstimateTotals:
    material_cost: Decimal
    cutting_cost: Decimal
    sewing_cost: Decimal
    hardware_cost: Decimal
    branding_cost: Decimal
    total_cost: Decimal
    unit_cost: Decimal


def summarize(
    material_cost: Decimal,
    cutting_cost: Decimal,
    sewing_cost: Decimal,
    hardware_cost: Decimal,
    branding_cost: Decimal,
    quantity: int,
) -> EstimateTotals:
    if quantity <= 0:
        raise ValueError("Тираж должен быть больше нуля")
    total = material_cost + cutting_cost + sewing_cost + hardware_cost + branding_cost
    return EstimateTotals(
        material_cost=money(material_cost),
        cutting_cost=money(cutting_cost),
        sewing_cost=money(sewing_cost),
        hardware_cost=money(hardware_cost),
        branding_cost=money(branding_cost),
        total_cost=money(total),
        unit_cost=money(total / Decimal(quantity)),
    )
