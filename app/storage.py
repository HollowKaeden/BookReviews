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
