from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


def get_db() -> Generator[Session, None, None]:
    """Зависимость FastAPI: сессия БД на время одного запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
