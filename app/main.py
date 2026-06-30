from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers import books, reviews

app = FastAPI(title="BookReviews")

app.include_router(books.router)
app.include_router(reviews.router)
app.include_router(reviews.review_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Процесс жив и отвечает. БД не трогаем."""
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Проверяем, что коннект к БД живой (SELECT 1)."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
