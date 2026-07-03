# BookReviews

[![CI](https://github.com/HollowKaeden/BookReviews/actions/workflows/ci.yml/badge.svg)](https://github.com/HollowKaeden/BookReviews/actions/workflows/ci.yml)

Веб-сервис с прочитанными мной книгами: каталог книг со статусами чтения,
оценками, отзывами, тегами и обложками. Есть публичный просмотр и закрытая
админка владельца.

Pet-проект в портфолио: аккуратный backend на Python с реляционной БД,
миграциями, тестами (в том числе против реального PostgreSQL), веб-интерфейсом
и CI. Читающий JSON API держится стабильным по форме, чтобы поверх него можно
было надстраивать наблюдаемость и переиспользовать в других проектах.

## Возможности

- Каталог книг: автор, год, статус (`read` / `reading` / `want_to_read` / `abandoned`), дата прочтения.
- Отзывы с оценкой 0–5 к каждой книге.
- Теги: регистронезависимые, создаются на лету, фильтрация и сортировка списка.
- Загрузка обложек (jpeg/png/webp/gif) с валидацией типа и размера.
- Публичные страницы только для чтения и админка владельца под `/admin` за HTTP Basic.
- JSON API с автодокументацией (Swagger UI на `/docs`).
- Служебные ручки `/health` и `/ready` для проверок живости и готовности.

## Стек

FastAPI · Uvicorn · Jinja2 · PostgreSQL · SQLAlchemy 2 · Alembic · pytest + httpx · Docker Compose · GitHub Actions

## Быстрый старт (Docker)

Поднимает сервис и PostgreSQL из чистого состояния, миграции применяются автоматически.

```bash
cp .env.example .env      # при желании поменяйте логин/пароль владельца
docker compose up --build
```

- Приложение: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Админка: http://localhost:8000/admin (логин/пароль из `.env`)

## Локальная разработка

```bash
python -m venv venv
source venv/Scripts/activate      # Windows; на Linux/macOS: source venv/bin/activate
pip install -e ".[dev]"

docker compose up -d db           # поднять только базу
alembic upgrade head              # применить миграции
uvicorn app.main:app --reload     # запустить приложение
```

Настройки читаются из `.env` (см. `.env.example`): строка подключения к БД и
учётка владельца. По умолчанию БД слушает хостовый порт `5433`, чтобы не
конфликтовать с локально установленным PostgreSQL.

## Тесты

```bash
pytest                            # по умолчанию на SQLite in-memory, быстро
```

Тот же набор можно прогнать против реального PostgreSQL, задав `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/bookreviews_test pytest
```

В CI проверяются оба варианта: быстрый SQLite для логики и Postgres для
диалект-специфики (плюс отдельная проверка, что миграции применяются вперёд и назад).

## API

Полная интерактивная документация: `/docs`. Кратко:

| Метод и путь | Назначение | Доступ |
| --- | --- | --- |
| `GET /api/books` | Список книг (с тегами) | открыт |
| `POST /api/books` | Создать книгу | владелец |
| `GET /api/books/{id}` | Книга с отзывами | открыт |
| `PATCH /api/books/{id}` | Изменить книгу | владелец |
| `DELETE /api/books/{id}` | Удалить книгу | владелец |
| `GET /api/books/{id}/reviews` | Отзывы книги | открыт |
| `POST /api/books/{id}/reviews` | Добавить отзыв | владелец |
| `PATCH /api/reviews/{id}` | Изменить отзыв | владелец |
| `DELETE /api/reviews/{id}` | Удалить отзыв | владелец |
| `PUT /api/books/{id}/cover` | Загрузить обложку (multipart) | владелец |
| `DELETE /api/books/{id}/cover` | Удалить обложку | владелец |

Читающие ручки (`GET`) открыты; мутирующие требуют HTTP Basic владельца.
Загруженные обложки раздаются по `/media/<file>`.

## Схема БД

```mermaid
erDiagram
    Book ||--o{ Review : "has"
    Book }o--o{ Tag : "tagged with"

    Book {
        int id PK
        string title
        string author
        int year
        enum status
        date date_read
        string cover_filename
        datetime created_at
        datetime updated_at
    }
    Review {
        int id PK
        int book_id FK
        float rating
        text text
        datetime created_at
        datetime updated_at
    }
    Tag {
        int id PK
        string name UK
    }
```

Связь `Book` - `Tag` реализована через ассоциативную таблицу `book_tags`.
Удаление книги каскадно уносит её отзывы и связи с тегами; теги, оставшиеся
без книг, подчищаются.

## Структура проекта

```
app/
  main.py            сборка приложения, роутеры, статика
  config.py          настройки (pydantic-settings)
  database.py        engine, сессия, get_db()
  models.py          SQLAlchemy-модели
  schemas.py         Pydantic-схемы
  crud.py            вся работа с БД
  routers/           JSON API (books, reviews) и HTML-страницы (pages, admin)
  templates/         Jinja2-шаблоны
  static/            CSS и JS
tests/               pytest + фикстуры
alembic/             миграции
```

Роутеры не ходят в БД напрямую: единственный источник для работы с
данными это слой `crud`, к которому обращаются и JSON API, и HTML-страницы.
