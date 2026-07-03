"""Общие фикстуры для тестов.

По умолчанию тесты идут на SQLite в памяти: быстро и без внешней БД. Но БД
выбирается через TEST_DATABASE_URL, поэтому тот же набор гоняется и на реальном
PostgreSQL (в CI поднимаем сервис). Это ловит диалект-специфику, которой SQLite
не воспроизводит, например Unicode в lower() при регистронезависимом матче тегов.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

# Обложки в тестах пишем во временный каталог. storage читает upload_dir в
# момент вызова, так что подмена атрибута работает независимо от порядка импортов.
settings.upload_dir = tempfile.mkdtemp(prefix="bookreviews-tests-")

# Учётку владельца берём из настроек (env/.env), а не хардкодим
ADMIN_AUTH = (settings.admin_username, settings.admin_password)


@pytest.fixture
def db_engine():
    """Чистая схема на каждый тест, полная изоляция состояния.

    Для SQLite: StaticPool держит одно соединение (все сессии видят одну
    in-memory базу), а PRAGMA foreign_keys=ON обязателен, иначе SQLite
    игнорирует ondelete=CASCADE и каскадное удаление отзывов не отработает.
    Для Postgres пул обычный; drop_all перед create_all подчищает остатки
    схемы от предыдущего прогона в постоянной БД.
    """
    if IS_SQLITE:
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    else:
        engine = create_engine(TEST_DATABASE_URL)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(
        bind=db_engine, autocommit=False, autoflush=False, class_=Session
    )


@pytest.fixture
def db_session(session_factory):
    """Прямой доступ к БД для тестов crud-слоя."""
    with session_factory() as session:
        yield session


@pytest.fixture
def _override_db(session_factory):
    """Подменяет зависимость get_db на тестовую БД для всего приложения."""

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(_override_db):
    """Анонимный клиент: читающие ручки и проверки 401."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_client(_override_db):
    """Клиент с HTTP Basic владельца для мутирующих ручек."""
    with TestClient(app) as test_client:
        test_client.auth = ADMIN_AUTH
        yield test_client
