"""Логотип цеха: хранение и подготовка для PDF.

Файл всегда нормализуется в PNG и ужимается до разумных размеров, поэтому
в PDF и на сайте попадает предсказуемое изображение без «тяжёлых» исходников.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import settings

LOGO_FILENAME = "logo.png"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_SOURCE_SIDE = 6000
LOGO_SIZE = (600, 300)
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}


class LogoError(ValueError):
    """Файл не подходит на роль логотипа."""


def logo_dir() -> Path:
    return Path(settings.uploads_dir)


def logo_path() -> Path | None:
    path = logo_dir() / LOGO_FILENAME
    return path if path.is_file() else None


def save_logo(data: bytes) -> Path:
    if not data:
        raise LogoError("Файл пустой")
    if len(data) > MAX_UPLOAD_BYTES:
        raise LogoError("Логотип больше 2 МБ")

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in ALLOWED_FORMATS:
                raise LogoError("Поддерживаются PNG, JPEG и WebP")
            if image.width > MAX_SOURCE_SIDE or image.height > MAX_SOURCE_SIDE:
                raise LogoError("Слишком большое изображение — максимум 6000 px по стороне")
            image.load()
            prepared = image.convert("RGBA")
            prepared.thumbnail(LOGO_SIZE, Image.Resampling.LANCZOS)
    except LogoError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise LogoError("Не удалось прочитать изображение") from exc

    target = logo_dir() / LOGO_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    prepared.save(target, format="PNG", optimize=True)
    return target


def delete_logo() -> bool:
    path = logo_path()
    if path is None:
        return False
    path.unlink()
    return True
