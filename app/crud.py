from collections.abc import Sequence
from sqlalchemy import delete, func, nullslast, select
from sqlalchemy.orm import Session, selectinload
from app import models, schemas


class InvariantError(ValueError):
    """Нарушен инвариант данных. Роутер ловит и отдаёт HTTP 422."""


BOOK_SORT_COLUMNS = {
    "created": models.Book.created_at,
    "title": models.Book.title,
    "date_read": models.Book.date_read,
}
DEFAULT_BOOK_SORT = "created"


# ---------- Tag ----------


def list_tags(db: Session) -> Sequence[models.Tag]:
    stmt = select(models.Tag).order_by(models.Tag.name)
    return db.execute(stmt).scalars().all()


def get_or_create_tags(
    db: Session, names: Sequence[str]
) -> list[models.Tag]:
    """Находит существующие теги и создаёт недостающие. Матчинг
    регистронезависимый (Python .lower() ↔ SQL lower()), дубли и пустые
    строки отбрасываются. Новые теги только add(), commit — на вызывающем."""
    wanted: dict[str, str] = {}
    for raw in names:
        name = raw.strip()
        if name:
            # Первое встреченное написание каноничное для новых тегов.
            wanted.setdefault(name.lower(), name)
    if not wanted:
        return []

    rows = (
        db.execute(
            select(models.Tag).where(
                func.lower(models.Tag.name).in_(list(wanted))
            )
        )
        .scalars()
        .all()
    )
    result = list(rows)
    have = {tag.name.lower() for tag in rows}
    for key, original in wanted.items():
        if key not in have:
            tag = models.Tag(name=original)
            db.add(tag)
            result.append(tag)
    return result


def delete_orphan_tags(db: Session) -> None:
    """Удаляет теги, не привязанные ни к одной книге. Вызывается после
    операций, способных осиротить тег (смена набора тегов у книги,
    удаление книги). flush() — чтобы правки book_tags попали в БД и
    EXISTS их учёл; commit остаётся на вызывающем."""
    db.flush()
    db.execute(
        delete(models.Tag)
        .where(~models.Tag.books.any())
        .execution_options(synchronize_session="fetch")
    )


# ---------- Book ----------


def list_books(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    sort: str = DEFAULT_BOOK_SORT,
    order: str = "desc",
    tag: str | None = None,
) -> Sequence[models.Book]:
    column = BOOK_SORT_COLUMNS.get(sort, BOOK_SORT_COLUMNS[DEFAULT_BOOK_SORT])
    direction = column.asc() if order == "asc" else column.desc()
    stmt = (
        select(models.Book)
        .options(selectinload(models.Book.tags))
        .order_by(nullslast(direction))
    )

    if tag:
        # any() фильтр без ручного join и без дублей строк книги.
        stmt = stmt.where(
            models.Book.tags.any(func.lower(models.Tag.name) == tag.lower())
        )

    # Дата прочтения осмысленна только у прочитанных книг, иначе список
    # разбавляют записи без даты. При этой сортировке показываем только их.
    if sort == "date_read":
        stmt = stmt.where(models.Book.status == models.BookStatus.read)

    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_book(db: Session, book_id: int) -> models.Book | None:
    return db.get(models.Book, book_id)


def create_book(db: Session, data: schemas.BookCreate) -> models.Book:
    payload = data.model_dump()
    tag_names = payload.pop("tags", [])
    book = models.Book(**payload)
    book.tags = get_or_create_tags(db, tag_names)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(
    db: Session, book: models.Book, data: schemas.BookUpdate
) -> models.Book:
    # exclude_unset: применяем только поля, реально присланные клиентом (PATCH).
    updates = data.model_dump(exclude_unset=True)

    tag_names = updates.pop("tags", None)

    # Инвариант проверяем на слитом состоянии (старое + патч) ДО мутации,
    # чтобы при ошибке сессия осталась чистой, а клиент получил 422, не 500.
    new_status = updates.get("status", book.status)
    new_date_read = updates.get("date_read", book.date_read)
    if new_date_read is not None and new_status != models.BookStatus.read:
        raise InvariantError(
            "date_read можно задавать только при status='read'"
        )

    for field, value in updates.items():
        setattr(book, field, value)
    if tag_names is not None:
        book.tags = get_or_create_tags(db, tag_names)
        delete_orphan_tags(db)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book: models.Book) -> None:
    db.delete(book)
    delete_orphan_tags(db)
    db.commit()


def set_book_cover(
    db: Session, book: models.Book, filename: str | None
) -> models.Book:
    book.cover_filename = filename
    db.commit()
    db.refresh(book)
    return book


# ---------- Review ----------


def list_reviews(
    db: Session, book_id: int, *, asc: bool = False
) -> Sequence[models.Review]:
    order = (
        models.Review.created_at.asc()
        if asc
        else models.Review.created_at.desc()
    )
    stmt = (
        select(models.Review)
        .where(models.Review.book_id == book_id)
        .order_by(order)
    )
    return db.execute(stmt).scalars().all()


def create_review(
    db: Session, book_id: int, data: schemas.ReviewCreate
) -> models.Review:
    review = models.Review(book_id=book_id, **data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: int) -> models.Review | None:
    return db.get(models.Review, review_id)


def update_review(
    db: Session, review: models.Review, data: schemas.ReviewUpdate
) -> models.Review:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: models.Review) -> None:
    db.delete(review)
    db.commit()
