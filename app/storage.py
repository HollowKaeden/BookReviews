import uuid
from pathlib import Path

from app.config import settings

# Разрешённые типы обложек → расширение файла на диске.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class CoverError(Exception):
    """Базовая ошибка загрузки обложки (валидация входного файла)."""


class UnsupportedImageType(CoverError):
    """Тип файла не из белого списка."""


class FileTooLarge(CoverError):
    """Файл превышает лимит размера."""


def validate_cover(data: bytes, content_type: str | None) -> None:
    """Проверяет тип и размер обложки. Бросает CoverError при проблеме.

    Отдельно от сохранения — чтобы можно было проверить файл ещё до
    записи на диск (например, при создании книги вместе с обложкой).
    """
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise UnsupportedImageType(
            "Поддерживаются только изображения: jpeg, png, webp, gif"
        )
    if len(data) > settings.max_upload_bytes:
        mb = settings.max_upload_bytes // (1024 * 1024)
        raise FileTooLarge(f"Файл слишком большой (максимум {mb} МБ)")


def validate_and_save_cover(data: bytes, content_type: str | None) -> str:
    """Проверяет и сохраняет файл, возвращает имя.

    Единая точка для JSON-ручки и HTML-формы.
    """
    validate_cover(data, content_type)
    return save_cover(data, content_type)


def save_cover(data: bytes, content_type: str) -> str:
    """Сохраняет обложку под случайным именем, возвращает имя файла.

    Имя генерим сами (uuid + расширение по content-type) — не доверяем
    имени из запроса, чтобы исключить path traversal и коллизии.
    """
    ext = ALLOWED_IMAGE_TYPES[content_type]
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / filename).write_bytes(data)
    return filename


def delete_cover(filename: str | None) -> None:
    """Удаляет файл обложки, если он задан. Отсутствие файла не ошибка."""
    if not filename:
        return
    (Path(settings.upload_dir) / filename).unlink(missing_ok=True)
