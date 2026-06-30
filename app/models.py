import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookStatus(enum.StrEnum):
    """Статус книги в моём списке чтения."""

    read = "read"
    reading = "reading"
    want_to_read = "want_to_read"
    abandoned = "abandoned"


class TimestampMixin:
    """created_at / updated_at для всех сущностей. Время с таймзоной,
    дефолты на стороне БД проставятся даже при вставке в обход ORM."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    __table_args__ = (
        # Дата прочтения осмысленна только у прочитанных книг.
        CheckConstraint(
            "date_read IS NULL OR status = 'read'",
            name="ck_books_date_read_only_when_read",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    year: Mapped[int | None]
    status: Mapped[BookStatus] = mapped_column(
        Enum(BookStatus, name="book_status"),
        default=BookStatus.want_to_read,
        server_default=BookStatus.want_to_read.value,
    )
    date_read: Mapped[date | None]

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Book {self.id}: {self.title!r}>"


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)

    book: Mapped["Book"] = relationship(back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review {self.id} book_id={self.book_id} rating={self.rating}>"
