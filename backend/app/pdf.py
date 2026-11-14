"""Генерация коммерческого предложения в PDF (fpdf2 + PT Sans)."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

from app.branding import logo_path
from app.models import Estimate, Settings
from app.timeutil import to_local

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_REGULAR = FONT_DIR / "PT_Sans-Regular.ttf"
FONT_BOLD = FONT_DIR / "PT_Sans-Bold.ttf"

PAGE_MARGIN = 15
CONTENT_WIDTH = 180

ACCENT = (31, 78, 121)
MUTED = (110, 118, 130)
LIGHT = (240, 244, 249)


def fmt_money(value: Decimal | float | int) -> str:
    dec = Decimal(str(value)).quantize(Decimal("0.01"))
    text = f"{dec:,.2f}".replace(",", " ").replace(".", ",")
    return f"{text} руб."


def fmt_number(value: Decimal | float | int, digits: int = 2) -> str:
    quant = Decimal(1).scaleb(-digits)
    dec = Decimal(str(value)).quantize(quant)
    text = f"{dec:,.{digits}f}".replace(",", " ").replace(".", ",")
    return text


def fmt_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def fmt_hardware_qty(unit: str, qty: Decimal) -> str:
    if unit == "per_item":
        return "на изделие"
    return f"{fmt_number(qty, 2)} шт/изд."


class _KP(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(PAGE_MARGIN, 14, PAGE_MARGIN)
        self.add_font("PTSans", "", str(FONT_REGULAR))
        self.add_font("PTSans", "B", str(FONT_BOLD))
        self.alias_nb_pages()

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("PTSans", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Стр. {self.page_no()} из {{nb}}", align="C")


def _section_title(pdf: _KP, text: str) -> None:
    pdf.set_font("PTSans", "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _info_row(pdf: _KP, label: str, value: str) -> None:
    pdf.set_font("PTSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(42, 6, label)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(CONTENT_WIDTH - 42, 6, value, new_x="LMARGIN", new_y="NEXT")


def _table_header(pdf: _KP, columns: list[tuple[str, int]], aligns: list[str]) -> None:
    pdf.set_font("PTSans", "B", 8.5)
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    for (title, width), align in zip(columns, aligns, strict=True):
        pdf.cell(width, 7, title, border=0, align=align, fill=True)
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)


def _table_row(
    pdf: _KP,
    values: list[str],
    widths: list[int],
    aligns: list[str],
    *,
    bold: bool = False,
    fill: bool = False,
) -> None:
    pdf.set_font("PTSans", "B" if bold else "", 9)
    if fill:
        pdf.set_fill_color(*LIGHT)
    for value, width, align in zip(values, widths, aligns, strict=True):
        pdf.cell(width, 7, value, border="B", align=align, fill=fill)
    pdf.ln(7)


def build_estimate_pdf(estimate: Estimate, settings_row: Settings) -> bytes:
    pdf = _KP()
    pdf.add_page()

    # --- шапка ---
    logo = logo_path()
    header_width = CONTENT_WIDTH
    if logo is not None:
        header_width = CONTENT_WIDTH - 30
        pdf.image(str(logo), x=PAGE_MARGIN + CONTENT_WIDTH - 26, y=15, w=26)

    pdf.set_font("PTSans", "B", 14)
    pdf.multi_cell(header_width, 7, settings_row.company_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("PTSans", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        header_width, 4.5, settings_row.company_requisites, new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(PAGE_MARGIN, pdf.get_y(), PAGE_MARGIN + CONTENT_WIDTH, pdf.get_y())
    pdf.ln(6)

    # --- заголовок документа ---
    pdf.set_font("PTSans", "B", 16)
    pdf.cell(0, 10, f"Коммерческое предложение № {estimate.number}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("PTSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, f"от {fmt_date(to_local(estimate.created_at))}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # --- параметры заказа ---
    _section_title(pdf, "Параметры заказа")
    _info_row(pdf, "Заказчик", estimate.contractor_name or "—")
    _info_row(
        pdf,
        "Изделие",
        f"{estimate.product_type_name} · тираж {estimate.quantity} шт. · сложность "
        f"«{estimate.complexity_name}»",
    )
    extras = [
        label
        for flag, label in (
            (estimate.has_lining, "подкладка"),
            (estimate.has_hood, "капюшон"),
            (estimate.has_pockets, "карманы"),
        )
        if flag
    ]
    if extras:
        _info_row(pdf, "Дополнительно", ", ".join(extras))
    _info_row(
        pdf,
        "Ткань",
        f"{estimate.fabric_name} · рулон {fmt_number(estimate.fabric_width_cm, 1)} см · "
        f"отходы {fmt_number(Decimal(estimate.waste_coefficient) * 100, 0)}%",
    )
    _info_row(pdf, "Срок изготовления", f"до {estimate.lead_time_days} рабочих дней")
    pdf.ln(3)

    # --- таблица расчёта ---
    _section_title(pdf, "Расчёт себестоимости")
    widths = [96, 30, 26, 28]
    aligns = ["L", "R", "R", "R"]
    _table_header(
        pdf,
        [
            ("Наименование", widths[0]),
            ("Кол-во", widths[1]),
            ("Цена", widths[2]),
            ("Сумма", widths[3]),
        ],
        aligns,
    )

    material = estimate.material_cost
    _table_row(
        pdf,
        [
            f"Материал: {estimate.fabric_name}",
            f"{fmt_number(estimate.material_length_m, 3)} м",
            f"{fmt_money(estimate.fabric_price_per_m)}/м",
            fmt_money(material),
        ],
        widths,
        aligns,
    )
    _table_row(
        pdf,
        [
            "Раскрой (работа раскройщика)",
            f"{fmt_number(estimate.cutting_hours, 2)} ч",
            f"{fmt_money(estimate.cutting_normohour)}/ч",
            fmt_money(estimate.cutting_cost),
        ],
        widths,
        aligns,
        fill=True,
    )
    _table_row(
        pdf,
        [
            "Пошив (работа швеи)",
            f"{fmt_number(estimate.sewing_hours, 2)} ч",
            f"{fmt_money(estimate.sewing_normohour)}/ч",
            fmt_money(estimate.sewing_cost),
        ],
        widths,
        aligns,
    )

    for item in estimate.hardware_items:
        _table_row(
            pdf,
            [
                f"Фурнитура: {item.name}",
                fmt_hardware_qty(item.unit, Decimal(item.qty)),
                fmt_money(item.price),
                fmt_money(item.total),
            ],
            widths,
            aligns,
            fill=True,
        )

    for item in estimate.branding_items:
        _table_row(
            pdf,
            [
                f"Брендирование: {item.name}",
                f"{item.positions} поз.",
                fmt_money(item.price),
                fmt_money(item.total),
            ],
            widths,
            aligns,
        )

    pdf.ln(1)
    pdf.set_font("PTSans", "B", 10)
    pdf.cell(
        0,
        8,
        f"ИТОГО за тираж: {fmt_money(estimate.total_cost)}",
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("PTSans", "", 9)
    pdf.cell(
        0,
        7,
        f"Себестоимость единицы: {fmt_money(estimate.unit_cost)}",
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    if estimate.notes:
        _section_title(pdf, "Комментарий")
        pdf.set_font("PTSans", "", 9)
        pdf.multi_cell(CONTENT_WIDTH, 5, estimate.notes, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    pdf.set_font("PTSans", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_WIDTH,
        4.5,
        (
            "Расчёт носит предварительный характер и является офертой не по всем позициям. "
            "Итоговая стоимость подтверждается после согласования образца и макета брендирования."
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("PTSans", "", 9)
    pdf.cell(70, 6, "Ответственный: " + (estimate.author.full_name if estimate.author else "—"))
    pdf.cell(0, 6, "Подпись: ____________________", align="R", new_x="LMARGIN", new_y="NEXT")

    generated = to_local(datetime.now(UTC)).strftime("%d.%m.%Y %H:%M")
    pdf.set_font("PTSans", "", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, f"Документ сформирован {generated}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
