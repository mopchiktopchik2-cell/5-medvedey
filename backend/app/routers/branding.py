"""Логотип цеха: загрузка технологом и публичная отдача."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.branding import MAX_UPLOAD_BYTES, LogoError, delete_logo, logo_path, save_logo
from app.schemas import LogoMeta
from app.security import Technologist

router = APIRouter(tags=["branding"])
public_router = APIRouter(prefix="/public", tags=["public"])

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _meta() -> LogoMeta:
    path = logo_path()
    updated_at = None
    if path is not None:
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    return LogoMeta(has_logo=path is not None, updated_at=updated_at)


@router.post("/dictionaries/logo", response_model=LogoMeta)
def upload_logo(file: Annotated[UploadFile, File()], _: Technologist) -> LogoMeta:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Нужен файл PNG, JPEG или WebP",
        )
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    try:
        save_logo(data)
    except LogoError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _meta()


@router.delete("/dictionaries/logo", status_code=status.HTTP_204_NO_CONTENT)
def remove_logo(_: Technologist) -> None:
    delete_logo()


@public_router.get("/logo/meta", response_model=LogoMeta)
def logo_meta() -> LogoMeta:
    return _meta()


@public_router.get("/logo")
def logo_file() -> FileResponse:
    path = logo_path()
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Логотип не загружен")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})
