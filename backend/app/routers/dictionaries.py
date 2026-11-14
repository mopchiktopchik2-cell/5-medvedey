from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import csv_import
from app.db import get_session
from app.models import Branding, ComplexityLevel, Contractor, Fabric, Hardware, ProductType
from app.schemas import (
    BrandingBase,
    BrandingRead,
    ComplexityBase,
    ComplexityRead,
    ContractorBase,
    ContractorRead,
    DictionariesRead,
    FabricBase,
    FabricRead,
    HardwareBase,
    HardwareRead,
    ImportResult,
    ProductTypeBase,
    ProductTypeRead,
    SettingsRead,
    SettingsUpdate,
)
from app.security import CurrentUser, Technologist
from app.services import get_settings_row

router = APIRouter(tags=["dictionaries"])

SessionDep = Annotated[Session, Depends(get_session)]

Model = TypeVar("Model")


def _get_or_404(session: Session, model: type[Model], entity_id: int, title: str) -> Model:
    entity = session.get(model, entity_id)
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{title} не найден(а)")
    return entity


def _active(session: Session, model: type) -> list:
    return list(session.scalars(select(model).order_by(model.id)))


def _ensure_unique_name(
    session: Session,
    model: type[Model],
    value: str,
    title: str,
    entity_id: int | None = None,
) -> None:
    """Не даёт создать второй справочник с тем же названием (без учёта регистра)."""
    needle = value.strip().casefold()
    for row in session.scalars(select(model)):
        if row.id != entity_id and row.name.strip().casefold() == needle:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{title} с названием «{value.strip()}» уже есть",
            )


def _ensure_unique_code(session: Session, value: str, entity_id: int | None = None) -> None:
    needle = value.strip().casefold()
    for row in session.scalars(select(ComplexityLevel)):
        if row.id != entity_id and row.code.strip().casefold() == needle:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Уровень с кодом «{value.strip()}» уже есть",
            )


@router.get("/dictionaries", response_model=DictionariesRead)
def read_dictionaries(session: SessionDep, _: CurrentUser) -> DictionariesRead:
    return DictionariesRead(
        fabrics=_active(session, Fabric),
        hardware=_active(session, Hardware),
        branding=_active(session, Branding),
        product_types=_active(session, ProductType),
        complexity_levels=_active(session, ComplexityLevel),
        contractors=_active(session, Contractor),
        settings=get_settings_row(session),
    )


# --- импорт из CSV ---


@router.post("/dictionaries/import/{kind}", response_model=ImportResult)
async def import_dictionary(
    kind: str,
    file: UploadFile,
    session: SessionDep,
    _: Technologist,
) -> ImportResult:
    if kind not in csv_import.KINDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Неизвестный справочник")

    data = await file.read(csv_import.MAX_BYTES + 1)
    try:
        items, errors = csv_import.parse(kind, data)
    except csv_import.ImportError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if not items:
        # Все строки с ошибками: показываем первую, чтобы было понятно, что чинить.
        message = errors[0] if errors else "В файле нет строк с данными"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)

    created, updated = csv_import.apply_rows(session, kind, items)
    return ImportResult(created=created, updated=updated, errors=errors)


@router.get("/dictionaries/import/{kind}/template.csv")
def download_template(kind: str) -> Response:
    if kind not in csv_import.KINDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Неизвестный справочник")
    return Response(
        content=csv_import.template(kind),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="template-{kind}.csv"'},
    )


# --- ткани ---


@router.post(
    "/dictionaries/fabrics", response_model=FabricRead, status_code=status.HTTP_201_CREATED
)
def create_fabric(payload: FabricBase, session: SessionDep, _: Technologist) -> Fabric:
    _ensure_unique_name(session, Fabric, payload.name, "Ткань")
    fabric = Fabric(**payload.model_dump())
    session.add(fabric)
    session.commit()
    session.refresh(fabric)
    return fabric


@router.patch("/dictionaries/fabrics/{fabric_id}", response_model=FabricRead)
def update_fabric(
    fabric_id: int, payload: FabricBase, session: SessionDep, _: Technologist
) -> Fabric:
    fabric = _get_or_404(session, Fabric, fabric_id, "Ткань")
    _ensure_unique_name(session, Fabric, payload.name, "Ткань", fabric.id)
    for field, value in payload.model_dump().items():
        setattr(fabric, field, value)
    session.commit()
    session.refresh(fabric)
    return fabric


@router.delete("/dictionaries/fabrics/{fabric_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_fabric(fabric_id: int, session: SessionDep, _: Technologist) -> None:
    fabric = _get_or_404(session, Fabric, fabric_id, "Ткань")
    fabric.is_active = False
    session.commit()


# --- фурнитура ---


@router.post(
    "/dictionaries/hardware", response_model=HardwareRead, status_code=status.HTTP_201_CREATED
)
def create_hardware(payload: HardwareBase, session: SessionDep, _: Technologist) -> Hardware:
    _ensure_unique_name(session, Hardware, payload.name, "Фурнитура")
    hardware = Hardware(**payload.model_dump())
    session.add(hardware)
    session.commit()
    session.refresh(hardware)
    return hardware


@router.patch("/dictionaries/hardware/{hardware_id}", response_model=HardwareRead)
def update_hardware(
    hardware_id: int, payload: HardwareBase, session: SessionDep, _: Technologist
) -> Hardware:
    hardware = _get_or_404(session, Hardware, hardware_id, "Фурнитура")
    _ensure_unique_name(session, Hardware, payload.name, "Фурнитура", hardware.id)
    for field, value in payload.model_dump().items():
        setattr(hardware, field, value)
    session.commit()
    session.refresh(hardware)
    return hardware


@router.delete("/dictionaries/hardware/{hardware_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_hardware(hardware_id: int, session: SessionDep, _: Technologist) -> None:
    hardware = _get_or_404(session, Hardware, hardware_id, "Фурнитура")
    hardware.is_active = False
    session.commit()


# --- брендирование ---


@router.post(
    "/dictionaries/branding", response_model=BrandingRead, status_code=status.HTTP_201_CREATED
)
def create_branding(payload: BrandingBase, session: SessionDep, _: Technologist) -> Branding:
    _ensure_unique_name(session, Branding, payload.name, "Брендирование")
    branding = Branding(**payload.model_dump())
    session.add(branding)
    session.commit()
    session.refresh(branding)
    return branding


@router.patch("/dictionaries/branding/{branding_id}", response_model=BrandingRead)
def update_branding(
    branding_id: int, payload: BrandingBase, session: SessionDep, _: Technologist
) -> Branding:
    branding = _get_or_404(session, Branding, branding_id, "Брендирование")
    _ensure_unique_name(session, Branding, payload.name, "Брендирование", branding.id)
    for field, value in payload.model_dump().items():
        setattr(branding, field, value)
    session.commit()
    session.refresh(branding)
    return branding


@router.delete("/dictionaries/branding/{branding_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_branding(branding_id: int, session: SessionDep, _: Technologist) -> None:
    branding = _get_or_404(session, Branding, branding_id, "Брендирование")
    branding.is_active = False
    session.commit()


# --- типы изделий ---


@router.post(
    "/dictionaries/product-types",
    response_model=ProductTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product_type(
    payload: ProductTypeBase, session: SessionDep, _: Technologist
) -> ProductType:
    _ensure_unique_name(session, ProductType, payload.name, "Тип изделия")
    product_type = ProductType(**payload.model_dump())
    session.add(product_type)
    session.commit()
    session.refresh(product_type)
    return product_type


@router.patch("/dictionaries/product-types/{product_type_id}", response_model=ProductTypeRead)
def update_product_type(
    product_type_id: int, payload: ProductTypeBase, session: SessionDep, _: Technologist
) -> ProductType:
    product_type = _get_or_404(session, ProductType, product_type_id, "Тип изделия")
    _ensure_unique_name(session, ProductType, payload.name, "Тип изделия", product_type.id)
    for field, value in payload.model_dump().items():
        setattr(product_type, field, value)
    session.commit()
    session.refresh(product_type)
    return product_type


@router.delete(
    "/dictionaries/product-types/{product_type_id}", status_code=status.HTTP_204_NO_CONTENT
)
def deactivate_product_type(product_type_id: int, session: SessionDep, _: Technologist) -> None:
    product_type = _get_or_404(session, ProductType, product_type_id, "Тип изделия")
    product_type.is_active = False
    session.commit()


# --- коэффициенты сложности ---


@router.post(
    "/dictionaries/complexity", response_model=ComplexityRead, status_code=status.HTTP_201_CREATED
)
def create_complexity(
    payload: ComplexityBase, session: SessionDep, _: Technologist
) -> ComplexityLevel:
    _ensure_unique_code(session, payload.code)
    level = ComplexityLevel(**payload.model_dump())
    session.add(level)
    session.commit()
    session.refresh(level)
    return level


@router.patch("/dictionaries/complexity/{level_id}", response_model=ComplexityRead)
def update_complexity(
    level_id: int, payload: ComplexityBase, session: SessionDep, _: Technologist
) -> ComplexityLevel:
    level = _get_or_404(session, ComplexityLevel, level_id, "Коэффициент сложности")
    _ensure_unique_code(session, payload.code, level.id)
    for field, value in payload.model_dump().items():
        setattr(level, field, value)
    session.commit()
    session.refresh(level)
    return level


# --- настройки ---


@router.patch("/dictionaries/settings", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, session: SessionDep, _: Technologist):
    row = get_settings_row(session)
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return row


# --- подрядчики ---


@router.post("/contractors", response_model=ContractorRead, status_code=status.HTTP_201_CREATED)
def create_contractor(payload: ContractorBase, session: SessionDep, _: Technologist) -> Contractor:
    key = payload.name.strip().casefold()
    existing = next(
        (
            item
            for item in session.scalars(select(Contractor))
            if item.name.strip().casefold() == key
        ),
        None,
    )
    if existing:
        return existing
    contractor = Contractor(**payload.model_dump())
    session.add(contractor)
    session.commit()
    session.refresh(contractor)
    return contractor


@router.patch("/contractors/{contractor_id}", response_model=ContractorRead)
def update_contractor(
    contractor_id: int, payload: ContractorBase, session: SessionDep, _: Technologist
) -> Contractor:
    contractor = _get_or_404(session, Contractor, contractor_id, "Подрядчик")
    _ensure_unique_name(session, Contractor, payload.name, "Подрядчик", contractor.id)
    contractor.name = payload.name
    contractor.contact_email = payload.contact_email
    contractor.phone = payload.phone
    session.commit()
    session.refresh(contractor)
    return contractor
