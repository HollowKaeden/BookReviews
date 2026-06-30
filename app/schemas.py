from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models import BookStatus


MAX_BOOK_YEAR = 2100


# ---------- Review ----------

class ReviewBase(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=1)


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    """Частичное обновление отзыва (PATCH) — оба поля опциональны."""

    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, min_length=1)


class ReviewRead(ReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    created_at: datetime
    updated_at: datetime


# ---------- Book ----------

class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    year: int | None = Field(default=None, ge=1, le=MAX_BOOK_YEAR)
    status: BookStatus = BookStatus.want_to_read
    date_read: date | None = None


class BookCreate(BookBase):
    @model_validator(mode="after")
    def date_read_only_when_read(self) -> "BookCreate":
        # Дублируем инвариант БД, чтобы клиент получил 422, а не 500.
        if self.date_read is not None and self.status != BookStatus.read:
            raise ValueError(
                "date_read можно задавать только при status='read'"
            )
        return self


class BookUpdate(BaseModel):
    """Все поля опциональны — это PATCH (частичное обновление)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    year: int | None = Field(default=None, ge=1, le=MAX_BOOK_YEAR)
    status: BookStatus | None = None
    date_read: date | None = None


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class BookDetail(BookRead):
    """Карточка книги с отзывами (для GET /api/books/{id} и HTML-страницы)."""

    reviews: list[ReviewRead] = []
