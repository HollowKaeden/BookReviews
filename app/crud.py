from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models, schemas


class InvariantError(ValueError):
    """Нарушен инвариант данных. Роутер ловит и отдаёт HTTP 422."""


# ---------- Book ----------


def list_books(
    db: Session, *, skip: int = 0, limit: int = 100
) -> Sequence[models.Book]:
    stmt = (
        select(models.Book)
        .order_by(models.Book.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def get_book(db: Session, book_id: int) -> models.Book | None:
    return db.get(models.Book, book_id)


def create_book(db: Session, data: schemas.BookCreate) -> models.Book:
    book = models.Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(
    db: Session, book: models.Book, data: schemas.BookUpdate
) -> models.Book:
    # exclude_unset: применяем только поля, реально присланные клиентом (PATCH).
    updates = data.model_dump(exclude_unset=True)

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
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book: models.Book) -> None:
    db.delete(book)
    db.commit()


# ---------- Review ----------


def list_reviews(db: Session, book_id: int) -> Sequence[models.Review]:
    stmt = (
        select(models.Review)
        .where(models.Review.book_id == book_id)
        .order_by(models.Review.created_at.desc())
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
