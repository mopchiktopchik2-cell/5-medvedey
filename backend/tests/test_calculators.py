from decimal import Decimal

from app.calculators import (
    PartInput,
    calculate_cutting,
    calculate_cutting_work,
    calculate_sewing,
    lead_time_days,
    sewing_modifier,
    summarize,
)


def test_layout_packs_order_across_roll() -> None:
    parts = [
        PartInput("Перед", Decimal(70), Decimal(50)),
        PartInput("Спинка", Decimal(70), Decimal(50)),
        PartInput("Рукав", Decimal(60), Decimal(25), 2),
    ]

    result = calculate_cutting(
        parts=parts,
        quantity=100,
        roll_width_cm=Decimal(180),
        waste_coefficient=Decimal("0.18"),
        seam_allowance_cm=Decimal("1.5"),
    )

    # детали всех 100 изделий укладываются в полосы по ширине рулона
    assert result.pieces_total == 400
    assert result.rows_total == 100
    assert result.length_cm == Decimal("6970.0")
    assert result.length_with_waste_m == Decimal("82.246")
    assert not result.approximate


def test_layout_adds_rows_when_roll_is_narrow() -> None:
    parts = [PartInput("Полочка", Decimal(80), Decimal(60), 4)]

    result = calculate_cutting(
        parts=parts,
        quantity=1,
        roll_width_cm=Decimal(100),
        waste_coefficient=Decimal("0"),
        seam_allowance_cm=Decimal("0"),
    )

    # ширина 60 + 60 = 120 > 100, значит каждая деталь в своей полосе
    assert result.rows_total == 4
    assert result.length_cm == Decimal("320.0")


def test_part_wider_than_roll_is_rejected() -> None:
    parts = [PartInput("Слишком широкая", Decimal(50), Decimal(200))]

    try:
        calculate_cutting(
            parts=parts,
            quantity=1,
            roll_width_cm=Decimal(150),
            waste_coefficient=Decimal("0"),
            seam_allowance_cm=Decimal("0"),
        )
    except ValueError as exc:
        assert "шире рулона" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("ожидалась ошибка")


def test_large_quantity_is_scaled_but_close_to_exact() -> None:
    parts = [PartInput("Перед", Decimal(70), Decimal(50))]

    result = calculate_cutting(
        parts=parts,
        quantity=30_000,
        roll_width_cm=Decimal(180),
        waste_coefficient=Decimal("0.18"),
        seam_allowance_cm=Decimal("1.5"),
    )

    # 30000 деталей 73×53 см при ширине рулона 180 см: партия 20 000 деталей,
    # затем длина масштабируется на весь тираж
    assert result.approximate
    assert result.length_with_waste_m == Decimal("8614.431")


def test_sewing_cost_uses_complexity_and_quantity() -> None:
    hours, cost = calculate_sewing(
        base_hours_per_unit=Decimal("0.60"),
        complexity_factor=Decimal("1.25"),
        quantity=200,
        normohour=Decimal("850"),
    )

    assert hours == Decimal("150.000")
    assert cost == Decimal("127500.00")


def test_sewing_modifiers_are_multiplicative() -> None:
    modifier = sewing_modifier(
        has_lining=True,
        has_hood=True,
        has_pockets=True,
        lining_factor=Decimal("1.15"),
        hood_factor=Decimal("1.10"),
        pockets_factor=Decimal("1.08"),
    )

    assert modifier.quantize(Decimal("0.0001")) == Decimal("1.3662")


def test_cutting_work_cost() -> None:
    hours, cost = calculate_cutting_work(400, 60, Decimal("700"))

    assert hours == Decimal("6.667")
    assert cost == Decimal("4666.67")


def test_lead_time_rounds_up_and_adds_buffer() -> None:
    assert lead_time_days(100, 80, 2) == 4
    assert lead_time_days(80, 80, 2) == 3
    assert lead_time_days(1, 80, 0) == 1


def test_summary_totals_and_unit_cost() -> None:
    totals = summarize(
        material_cost=Decimal("41347.20"),
        cutting_cost=Decimal("4666.67"),
        sewing_cost=Decimal("51000.00"),
        hardware_cost=Decimal("1200.00"),
        branding_cost=Decimal("25000.00"),
        quantity=100,
    )

    assert totals.total_cost == Decimal("123213.87")
    assert totals.unit_cost == Decimal("1232.14")
