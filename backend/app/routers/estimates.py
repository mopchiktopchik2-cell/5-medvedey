import csv
import io
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_session
from app.mailer import EmailDeliveryError, send_estimate_email
from app.models import (
    Contractor,
    Estimate,
    EstimateBranding,
    EstimateHardware,
    EstimatePart,
    UserRole,
)
from app.pdf import build_estimate_pdf
from app.schemas import (
    EmailSendRequest,
    EmailSendResult,
    EstimateListItem,
    EstimateListResponse,
    EstimatePreview,
    EstimateRead,
    EstimateRequest,
    PublicEstimateRead,
    ShareResult,
)
from app.security import CurrentUser
from app.services import CalculationError, calculate, get_settings_row
from app.timeutil import day_start_utc, next_day_start_utc, to_local

router = APIRouter(prefix="/estimates", tags=["estimates"])
public_router = APIRouter(prefix="/public", tags=["public"])

SessionDep = Annotated[Session, Depends(get_session)]


def _as_utc(value: datetime) -> datetime:
    """SQLite возвращает naive datetime — трактуем его как UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _share_is_alive(estimate: Estimate) -> bool:
    if not estimate.share_token:
        return False
    if estimate.share_expires_at is None:
        return True
    return _as_utc(estimate.share_expires_at) > datetime.now(UTC)


def _detail_query():
    return select(Estimate).options(
        selectinload(Estimate.parts),
        selectinload(Estimate.hardware_items),
        selectinload(Estimate.branding_items),
        selectinload(Estimate.author),
        selectinload(Estimate.contractor),
    )


def _visible_estimate(session: Session, user, estimate_id: int) -> Estimate:
    estimate = session.scalar(_detail_query().where(Estimate.id == estimate_id))
    if estimate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Расчёт не найден")
    if user.role != UserRole.TECHNOLOGIST and estimate.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Расчёт принадлежит другому менеджеру")
    return estimate


def _resolve_contractor(
    session: Session, payload: EstimateRequest
) -> tuple[int | None, str | None]:
    if payload.contractor_id:
        contractor = session.get(Contractor, payload.contractor_id)
        if contractor is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Подрядчик не найден")
        return contractor.id, contractor.name

    name = (payload.contractor_name or "").strip()
    if not name:
        return None, None

    contractor = session.scalar(select(Contractor).where(Contractor.name == name))
    if contractor is None:
        # SQLite не умеет lower() для кириллицы: ищем без учёта регистра в Python.
        key = name.casefold()
        contractor = next(
            (
                item
                for item in session.scalars(select(Contractor))
                if item.name.strip().casefold() == key
            ),
            None,
        )
    if contractor is None:
        contractor = Contractor(name=name)
        session.add(contractor)
        session.flush()
    return contractor.id, contractor.name


def _lower(column):
    """Регистронезависимое сравнение: в SQLite используем питоновский py_lower."""
    if settings.database_url.startswith("sqlite"):
        return func.py_lower(column)
    return func.lower(column)


@router.post("/preview", response_model=EstimatePreview)
def preview_estimate(
    payload: EstimateRequest, session: SessionDep, _: CurrentUser
) -> EstimatePreview:
    try:
        return calculate(session, payload).preview
    except CalculationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("", response_model=EstimateRead, status_code=status.HTTP_201_CREATED)
def create_estimate(payload: EstimateRequest, session: SessionDep, user: CurrentUser) -> Estimate:
    try:
        calculated = calculate(session, payload)
    except CalculationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    contractor_id, contractor_name = _resolve_contractor(session, payload)
    view = calculated.preview

    estimate = Estimate(
        author_id=user.id,
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        product_type_id=calculated.product_type.id,
        product_type_name=calculated.product_type.name,
        complexity_id=calculated.complexity.id,
        complexity_name=calculated.complexity.name,
        complexity_factor=calculated.complexity.factor,
        quantity=payload.quantity,
        has_lining=payload.has_lining,
        has_hood=payload.has_hood,
        has_pockets=payload.has_pockets,
        fabric_id=calculated.fabric.id,
        fabric_name=calculated.fabric.name,
        fabric_width_cm=calculated.roll_width_cm,
        fabric_price_per_m=calculated.price_per_m,
        waste_coefficient=calculated.waste_coefficient,
        seam_allowance_cm=calculated.seam_allowance_cm,
        sewing_hours=view.sewing.hours,
        sewing_normohour=view.sewing.normohour,
        sewing_cost=view.totals.sewing_cost,
        cutting_hours=view.cutting.hours,
        cutting_normohour=view.cutting.normohour,
        cutting_cost=view.totals.cutting_cost,
        material_length_m=view.material.length_with_waste_m,
        material_cost=view.totals.material_cost,
        hardware_cost=view.totals.hardware_cost,
        branding_cost=view.totals.branding_cost,
        total_cost=view.totals.total_cost,
        unit_cost=view.totals.unit_cost,
        lead_time_days=view.lead_time_days,
        notes=payload.notes,
    )

    for part in calculated.parts:
        estimate.parts.append(
            EstimatePart(
                name=part.name,
                length_cm=part.length_cm,
                width_cm=part.width_cm,
                count_per_unit=part.count_per_unit,
            )
        )

    for item, qty, total in calculated.hardware_lines:
        estimate.hardware_items.append(
            EstimateHardware(
                hardware_id=item.id,
                name=item.name,
                unit=item.unit,
                price=item.price,
                qty=qty,
                total=total,
            )
        )

    for item, positions, total in calculated.branding_lines:
        estimate.branding_items.append(
            EstimateBranding(
                branding_id=item.id,
                name=item.name,
                price=item.price,
                positions=positions,
                total=total,
            )
        )

    session.add(estimate)
    session.flush()
    estimate.number = f"КП-{to_local(estimate.created_at).year}-{estimate.id:04d}"
    session.commit()
    session.refresh(estimate)
    return estimate


def _filter_conditions(
    user,
    date_from: date | None,
    date_to: date | None,
    contractor_id: int | None,
    product_type_id: int | None,
    q: str | None,
) -> list:
    conditions = []
    if user.role != UserRole.TECHNOLOGIST:
        conditions.append(Estimate.author_id == user.id)
    if date_from is not None:
        conditions.append(Estimate.created_at >= day_start_utc(date_from))
    if date_to is not None:
        conditions.append(Estimate.created_at < next_day_start_utc(date_to))
    if contractor_id is not None:
        conditions.append(Estimate.contractor_id == contractor_id)
    if product_type_id is not None:
        conditions.append(Estimate.product_type_id == product_type_id)
    if q:
        needle = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                _lower(Estimate.number).like(needle),
                _lower(Estimate.product_type_name).like(needle),
                _lower(Estimate.contractor_name).like(needle),
            )
        )
    return conditions


@router.get("", response_model=EstimateListResponse)
def list_estimates(
    session: SessionDep,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    contractor_id: int | None = None,
    product_type_id: int | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EstimateListResponse:
    conditions = _filter_conditions(user, date_from, date_to, contractor_id, product_type_id, q)
    base = select(Estimate).where(*conditions)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0

    items = session.scalars(
        base.options(selectinload(Estimate.author))
        .order_by(Estimate.created_at.desc(), Estimate.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return EstimateListResponse(
        items=[EstimateListItem.model_validate(item) for item in items],
        total=total,
    )


def _csv_money(value) -> str:
    return f"{value:.2f}".replace(".", ",")


@router.get("/export.csv")
def export_estimates_csv(
    session: SessionDep,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    contractor_id: int | None = None,
    product_type_id: int | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 10_000,
) -> Response:
    conditions = _filter_conditions(user, date_from, date_to, contractor_id, product_type_id, q)
    items = session.scalars(
        select(Estimate)
        .where(*conditions)
        .options(selectinload(Estimate.author))
        .order_by(Estimate.created_at.desc(), Estimate.id.desc())
        .limit(limit)
    ).all()

    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM, чтобы Excel корректно открыл кириллицу
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "Номер",
            "Дата",
            "Подрядчик",
            "Изделие",
            "Сложность",
            "Тираж, шт.",
            "Материал",
            "Раскрой",
            "Пошив",
            "Фурнитура",
            "Брендирование",
            "Итого",
            "За единицу",
            "Срок, дн.",
            "Автор",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.number,
                to_local(item.created_at).strftime("%d.%m.%Y %H:%M"),
                item.contractor_name or "",
                item.product_type_name,
                item.complexity_name,
                item.quantity,
                _csv_money(item.material_cost),
                _csv_money(item.cutting_cost),
                _csv_money(item.sewing_cost),
                _csv_money(item.hardware_cost),
                _csv_money(item.branding_cost),
                _csv_money(item.total_cost),
                _csv_money(item.unit_cost),
                item.lead_time_days,
                item.author_name or "",
            ]
        )

    filename = f"kp-history-{to_local(datetime.now(UTC)):%Y-%m-%d}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{estimate_id}", response_model=EstimateRead)
def get_estimate(estimate_id: int, session: SessionDep, user: CurrentUser) -> Estimate:
    return _visible_estimate(session, user, estimate_id)


@router.delete("/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate(estimate_id: int, session: SessionDep, user: CurrentUser) -> None:
    estimate = _visible_estimate(session, user, estimate_id)
    if user.role != UserRole.TECHNOLOGIST and estimate.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    session.delete(estimate)
    session.commit()


def _pdf_response(estimate: Estimate, settings_row) -> Response:
    content = build_estimate_pdf(estimate, settings_row)
    # Заголовки должны быть в latin-1: ASCII-имя + filename* для кириллицы.
    ascii_name = estimate.number.replace("КП", "KP")
    disposition = (
        f'attachment; filename="{ascii_name}.pdf"; '
        f"filename*=UTF-8''{quote(f'{estimate.number}.pdf')}"
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition, "Cache-Control": "no-store"},
    )


@router.get("/{estimate_id}/pdf")
def download_pdf(estimate_id: int, session: SessionDep, user: CurrentUser) -> Response:
    estimate = _visible_estimate(session, user, estimate_id)
    return _pdf_response(estimate, get_settings_row(session))


@router.post("/{estimate_id}/share", response_model=ShareResult)
def share_estimate(estimate_id: int, session: SessionDep, user: CurrentUser) -> ShareResult:
    """Выдаёт публичную ссылку. Действующая ссылка переиспользуется."""
    estimate = _visible_estimate(session, user, estimate_id)

    if not _share_is_alive(estimate):
        estimate.share_token = secrets.token_urlsafe(16)
        estimate.share_expires_at = datetime.now(UTC) + timedelta(
            days=max(1, settings.share_token_ttl_days)
        )
        session.commit()
        session.refresh(estimate)

    return ShareResult(
        token=estimate.share_token or "",
        path=f"/share/{estimate.share_token}",
        expires_at=estimate.share_expires_at,
    )


@router.delete("/{estimate_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(estimate_id: int, session: SessionDep, user: CurrentUser) -> None:
    """Отзывает публичную ссылку: старый токен перестаёт работать."""
    estimate = _visible_estimate(session, user, estimate_id)
    estimate.share_token = None
    estimate.share_expires_at = None
    session.commit()


@router.post("/{estimate_id}/send-email", response_model=EmailSendResult)
def send_estimate_by_email(
    estimate_id: int,
    payload: EmailSendRequest,
    session: SessionDep,
    user: CurrentUser,
) -> EmailSendResult:
    estimate = _visible_estimate(session, user, estimate_id)
    company = get_settings_row(session)
    pdf_bytes = build_estimate_pdf(estimate, company)
    try:
        result = send_estimate_email(
            estimate,
            company,
            pdf_bytes,
            str(payload.to),
            payload.message,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return EmailSendResult(status=result.status, detail=result.detail, to=payload.to)


@public_router.get("/estimates/{token}", response_model=PublicEstimateRead)
def get_shared_estimate(token: str, session: SessionDep) -> Estimate:
    estimate = session.scalar(_detail_query().where(Estimate.share_token == token))
    if estimate is None or not _share_is_alive(estimate):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ссылка недействительна или истекла")
    return estimate


@public_router.get("/estimates/{token}/pdf")
def download_shared_pdf(token: str, session: SessionDep) -> Response:
    estimate = session.scalar(_detail_query().where(Estimate.share_token == token))
    if estimate is None or not _share_is_alive(estimate):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ссылка недействительна или истекла")
    return _pdf_response(estimate, get_settings_row(session))
