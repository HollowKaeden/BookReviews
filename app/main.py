from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.routers import admin, books, pages, reviews

app = FastAPI(title="BookReviews")

# Статика интерфейса (CSS)
APP_DIR = Path(__file__).resolve().parent
app.mount(
    "/static",
    StaticFiles(directory=str(APP_DIR / "static")),
    name="static",
)

# Загруженные обложки раздаём как статику по /media.
# Каталог создаём заранее — StaticFiles требует существующую директорию.
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount(
    "/media", StaticFiles(directory=settings.upload_dir), name="media"
)

app.include_router(books.router)
app.include_router(reviews.router)
app.include_router(reviews.review_router)
app.include_router(pages.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Процесс жив и отвечает. БД не трогаем."""
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Проверяем, что коннект к БД живой (SELECT 1)."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
