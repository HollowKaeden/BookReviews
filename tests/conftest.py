"""Общие фикстуры для тестов.

Тесты используют SQLite в памяти вместо PostgreSQL. Для API и CRUD этого
достаточно, а гонять их можно без внешней БД, что удобно и локально, и в CI.
Postgres-специфику проверяем на уровне миграций и docker-compose.
"""

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Обложки в тестах пишем во временный каталог. storage читает upload_dir в
# момент вызова, так что подмена атрибута работает независимо от порядка импортов.
settings.upload_dir = tempfile.mkdtemp(prefix="bookreviews-tests-")

# Учётку владельца берём из настроек (env/.env), а не хардкодим
ADMIN_AUTH = (settings.admin_username, settings.admin_password)


@pytest.fixture
def db_engine():
    """Свежая in-memory БД на каждый тест, полная изоляция состояния.

    StaticPool держит одно соединение, так что все сессии внутри теста видят
    одну базу. PRAGMA foreign_keys=ON обязателен: без него SQLite игнорирует
    ondelete=CASCADE, и каскадное удаление отзывов не отработает.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

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
