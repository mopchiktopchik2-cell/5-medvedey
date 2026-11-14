"""Импорт справочников из CSV.

Формат: первая строка — заголовки, дальше данные. Разделитель определяется
автоматически (``;``, ``,`` или табуляция), кодировка — UTF-8 или Windows-1251,
чтобы файл из Excel открывался без ручного пересохранения.

Заголовки понимают и английские имена полей, и русские подписи из шаблона.
Строки с ошибками пропускаются, остальные импортируются; номера проблемных
строк возвращаются клиенту.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branding, ComplexityLevel, Fabric, Hardware, ProductType

MAX_BYTES = 1_000_000
MAX_ROWS = 1000

KINDS = ("fabrics", "hardware", "branding", "product-types", "complexity")


class ImportError(ValueError):
    """Файл целиком не подходит: пустой, без колонок или слишком большой."""


@dataclass(frozen=True)
class Column:
    key: str
    required: bool = True
    kind: str = "text"  # text | decimal
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    max_length: int = 160


@dataclass(frozen=True)
class Spec:
    columns: tuple[Column, ...]
    required_headers: tuple[str, ...]
    units: bool = False
    aliases: dict[str, str] = field(default_factory=dict)


SPECS: dict[str, Spec] = {
    "fabrics": Spec(
        columns=(
            Column("name", max_length=120),
            Column("width_cm", kind="decimal", minimum=Decimal("1"), maximum=Decimal("1000")),
            Column(
                "price_per_m", kind="decimal", minimum=Decimal("0"), maximum=Decimal("10000000")
            ),
            Column("density", required=False, max_length=60),
        ),
        required_headers=("name", "width_cm", "price_per_m"),
        aliases={
            "цена": "price_per_m",
            "цена_за_метр": "price_per_m",
            "ширина": "width_cm",
            "ширина_см": "width_cm",
            "ширина_рулона": "width_cm",
        },
    ),
    "hardware": Spec(
        columns=(
            Column("name", max_length=120),
            Column("unit", required=False),
            Column("price", kind="decimal", minimum=Decimal("0"), maximum=Decimal("10000000")),
        ),
        required_headers=("name", "price"),
        units=True,
        aliases={"цена": "price", "цена_за_шт": "price"},
    ),
    "branding": Spec(
        columns=(
            Column("name", max_length=120),
            Column("price", kind="decimal", minimum=Decimal("0"), maximum=Decimal("10000000")),
        ),
        required_headers=("name", "price"),
        aliases={"цена": "price", "цена_за_позицию": "price"},
    ),
    "product-types": Spec(
        columns=(
            Column("name", max_length=120),
            Column(
                "base_sewing_hours",
                kind="decimal",
                minimum=Decimal("0.01"),
                maximum=Decimal("1000"),
            ),
        ),
        required_headers=("name", "base_sewing_hours"),
        aliases={
            "часы": "base_sewing_hours",
            "базовые_часы": "base_sewing_hours",
            "время": "base_sewing_hours",
        },
    ),
    "complexity": Spec(
        columns=(
            Column("code", max_length=40),
            Column("name", max_length=80),
            Column("factor", kind="decimal", minimum=Decimal("0.1"), maximum=Decimal("10")),
        ),
        required_headers=("code", "name", "factor"),
        aliases={"коэффициент": "factor"},
    ),
}

COMMON_ALIASES = {
    "название": "name",
    "наименование": "name",
    "состав": "density",
    "плотность": "density",
    "единица": "unit",
    "ед_изм": "unit",
    "код": "code",
}

UNIT_ALIASES = {
    "piece": "piece",
    "per_item": "per_item",
    "шт": "piece",
    "штука": "piece",
    "за_штуку": "piece",
    "на_изделие": "per_item",
    "изделие": "per_item",
    "комплект": "per_item",
}

TEMPLATES: dict[str, tuple[str, ...]] = {
    "fabrics": (
        "name;width_cm;price_per_m;density",
        "Кулирка хлопок 160 г/м²;180;480.00;хлопок 100%",
        "Футер 2-нитка 240 г/м²;180;720.00;хлопок 80% / пэ 20%",
    ),
    "hardware": (
        "name;unit;price",
        "Пуговица 18 мм;piece;6.00",
        "Нитки (комплект на изделие);per_item;45.00",
    ),
    "branding": (
        "name;price",
        "Термотрансфер A4;250.00",
        "Вышивка до 10×10 см;320.00",
    ),
    "product-types": (
        "name;base_sewing_hours",
        "Футболка;0.60",
        "Худи;1.40",
    ),
    "complexity": (
        "code;name;factor",
        "base;Базовая;1.00",
        "medium;Средняя;1.25",
    ),
}


def template(kind: str) -> str:
    """Шаблон CSV с BOM: Excel откроет кириллицу без «кракозябр»."""
    return "\ufeff" + "\r\n".join(TEMPLATES[kind]) + "\r\n"


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportError("Не удалось прочитать файл: сохраните его как UTF-8 или Windows-1251")


def _sniff_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    counts = {delimiter: first_line.count(delimiter) for delimiter in (";", ",", "\t")}
    delimiter = max(counts, key=counts.get)
    return delimiter if counts[delimiter] else ";"


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _decimal(value: str) -> Decimal:
    normalized = value.replace(",", ".").replace("\u00a0", "").replace(" ", "")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ImportError(f"«{value}» — не число") from exc


def parse(kind: str, data: bytes) -> tuple[list[dict[str, str]], list[str]]:
    """Разбирает CSV и возвращает валидные строки и список ошибок по строкам."""
    if kind not in SPECS:
        raise ImportError(f"Неизвестный справочник: {kind}")
    if not data:
        raise ImportError("Файл пустой")
    if len(data) > MAX_BYTES:
        raise ImportError("Файл больше 1 МБ: разделите прайс на части")

    spec = SPECS[kind]
    text = _decode(data)
    reader = csv.reader(io.StringIO(text), delimiter=_sniff_delimiter(text))
    rows = list(reader)
    if not rows:
        raise ImportError("В файле нет ни одной строки")

    aliases = {**COMMON_ALIASES, **spec.aliases}
    header = [_normalize_header(cell) for cell in rows[0]]
    positions: dict[str, int] = {}
    for index, title in enumerate(header):
        key = aliases.get(title, title)
        if key in {column.key for column in spec.columns} and key not in positions:
            positions[key] = index

    missing = [name for name in spec.required_headers if name not in positions]
    if missing:
        raise ImportError("В файле нет обязательных колонок: " + ", ".join(missing))

    items: list[dict[str, str]] = []
    errors: list[str] = []
    for line_number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(items) >= MAX_ROWS:
            raise ImportError(f"Слишком много строк: максимум {MAX_ROWS}")

        item: dict[str, str] = {}
        problem: str | None = None
        for column in spec.columns:
            position = positions.get(column.key)
            raw = row[position].strip() if position is not None and position < len(row) else ""

            if not raw:
                if column.required:
                    problem = f"пустое поле «{column.key}»"
                    break
                item[column.key] = ""
                continue

            if len(raw) > column.max_length:
                problem = f"поле «{column.key}» длиннее {column.max_length} символов"
                break

            if column.kind == "decimal":
                try:
                    value = _decimal(raw)
                except ImportError:
                    problem = f"поле «{column.key}» — не число: {raw}"
                    break
                if column.minimum is not None and value < column.minimum:
                    problem = f"поле «{column.key}» меньше {column.minimum}"
                    break
                if column.maximum is not None and value > column.maximum:
                    problem = f"поле «{column.key}» больше {column.maximum}"
                    break
                item[column.key] = str(value)
            else:
                item[column.key] = raw

        if problem:
            errors.append(f"Строка {line_number}: {problem}")
            continue

        if spec.units:
            unit = item.get("unit", "") or "piece"
            unit = UNIT_ALIASES.get(unit.strip().lower(), unit.strip().lower())
            if unit not in ("piece", "per_item"):
                errors.append(
                    f"Строка {line_number}: единица «{item.get('unit', '')}» — "
                    "укажите piece или per_item"
                )
                continue
            item["unit"] = unit

        items.append(item)

    return items, errors


def apply_rows(session: Session, kind: str, items: list[dict[str, str]]) -> tuple[int, int]:
    """Создаёт и обновляет записи; возвращает (создано, обновлено)."""
    created = 0
    updated = 0
    existing_levels = (
        {level.code.casefold(): level for level in session.scalars(select(ComplexityLevel))}
        if kind == "complexity"
        else {}
    )
    model: type | None = None
    existing_by_name: dict[str, object] = {}
    if kind != "complexity":
        model = {
            "fabrics": Fabric,
            "hardware": Hardware,
            "branding": Branding,
            "product-types": ProductType,
        }[kind]
        # SQLite не умеет lower() для кириллицы, поэтому сравниваем в Python.
        existing_by_name = {row.name.casefold(): row for row in session.scalars(select(model))}

    for item in items:
        if kind == "complexity":
            entity = existing_levels.get(item["code"].casefold())
            if entity is None:
                entity = ComplexityLevel(
                    code=item["code"],
                    name=item["name"],
                    factor=Decimal(item["factor"]),
                )
                session.add(entity)
                created += 1
            else:
                entity.name = item["name"]
                entity.factor = Decimal(item["factor"])
                updated += 1
            continue

        assert model is not None
        entity = existing_by_name.get(item["name"].casefold())
        if entity is None:
            entity = model(name=item["name"])
            session.add(entity)
            created += 1
        else:
            updated += 1
        entity.name = item["name"]
        entity.is_active = True

        if kind == "fabrics":
            entity.width_cm = Decimal(item["width_cm"])
            entity.price_per_m = Decimal(item["price_per_m"])
            entity.density = item.get("density") or None
        elif kind == "hardware":
            entity.unit = item["unit"]
            entity.price = Decimal(item["price"])
        elif kind == "branding":
            entity.price = Decimal(item["price"])
        elif kind == "product-types":
            entity.base_sewing_hours = Decimal(item["base_sewing_hours"])

    session.commit()
    return created, updated
