from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud, models, schemas, storage
from app.auth import require_admin
from app.config import settings
from app.database import get_db
from app.models import BookStatus
from app.templating import not_found, redirect, render

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    include_in_schema=False,
)


def _render_admin_index(
    request: Request,
    db: Session,
    *,
    error: str | None = None,
    form: dict | None = None,
    status_code: int = 200,
) -> Response:
    ctx: dict = {
        "books": crud.list_books(db, limit=1000),
        "all_tags": crud.list_tags(db),
    }
    if error is not None:
        ctx["error"] = error
    if form is not None:
        ctx["form"] = form
    return render(request, "admin/index.html", ctx, status_code)


def _render_book_detail(
    request: Request,
    db: Session,
    book: models.Book,
    *,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    ctx: dict = {
        "book": book,
        "reviews": crud.list_reviews(db, book.id),
        "all_tags": crud.list_tags(db),
    }
    if error is not None:
        ctx["error"] = error
    return render(request, "admin/book_detail.html", ctx, status_code)


# ---------- Список / создание книг ----------


@router.get("", response_class=HTMLResponse)
def admin_index(request: Request, db: Session = Depends(get_db)) -> Response:
    return _render_admin_index(request, db)


@router.post("/books")
async def create_book(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    year: str = Form(""),
    status_value: str = Form(BookStatus.want_to_read.value, alias="status"),
    date_read: str = Form(""),
    tags: list[str] = Form(default=[]),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> Response:
    # Обложку читаем заранее, но валидируем (и сохраняем) только после того,
    # как прошли поля книги чтобы не плодить файлы при ошибке.
    cover_bytes: bytes | None = None
    if file is not None and file.filename:
        cover_bytes = await file.read(settings.max_upload_bytes + 1)

    error: str | None = None
    data: schemas.BookCreate | None = None
    try:
        data = schemas.BookCreate(
            title=title,
            author=author,
            year=year or None,
            status=status_value,
            date_read=date_read or None,
            tags=tags,
        )
    except ValidationError:
        error = (
            "Не получилось сохранить: дату прочтения можно указывать "
            "только для статуса «Прочитано»."
        )
    if error is None and cover_bytes is not None:
        try:
            storage.validate_cover(cover_bytes, file.content_type)
        except storage.CoverError as exc:
            error = str(exc)

    if error is not None:
        return _render_admin_index(
            request,
            db,
            error=error,
            form={
                "title": title,
                "author": author,
                "year": year,
                "status": status_value,
                "date_read": date_read,
                "tags": tags,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    book = crud.create_book(db, data)
    if cover_bytes is not None:
        filename = storage.save_cover(cover_bytes, file.content_type)
        crud.set_book_cover(db, book, filename)
    return redirect(f"/admin/books/{book.id}")


@router.post("/books/{book_id}/edit")
def edit_book(
    request: Request,
    book_id: int,
    title: str = Form(...),
    author: str = Form(...),
    year: str = Form(""),
    status_value: str = Form(..., alias="status"),
    date_read: str = Form(""),
    tags: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
) -> Response:
    book = crud.get_book(db, book_id)
    if book is None:
        return not_found(request)
    try:
        data = schemas.BookUpdate(
            title=title,
            author=author,
            year=year or None,
            status=status_value,
            date_read=date_read or None,
            tags=tags,
        )
        crud.update_book(db, book, data)
    except (ValidationError, crud.InvariantError) as exc:
        msg = (
            str(exc)
            if isinstance(exc, crud.InvariantError)
            else "Проверьте поля книги: год — число до 2100."
        )
        return _render_book_detail(
            request, db, book, error=msg,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return redirect(f"/admin/books/{book_id}?saved=book#book-edit")


# ---------- Карточка книги (admin) ----------


@router.get("/books/{book_id}", response_class=HTMLResponse)
def admin_book_detail(
    request: Request, book_id: int, db: Session = Depends(get_db)
) -> Response:
    book = crud.get_book(db, book_id)
    if book is None:
        return not_found(request)
    return _render_book_detail(request, db, book)


@router.post("/books/{book_id}/delete")
def delete_book(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = crud.get_book(db, book_id)
    if book is not None:
        cover_filename = book.cover_filename
        crud.delete_book(db, book)
        storage.delete_cover(cover_filename)
    return redirect("/admin")


# ---------- Отзывы ----------


@router.post("/books/{book_id}/reviews")
def add_review(
    request: Request,
    book_id: int,
    rating: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    book = crud.get_book(db, book_id)
    if book is None:
        return not_found(request)
    try:
        data = schemas.ReviewCreate(rating=rating or None, text=text)
    except ValidationError:
        return _render_book_detail(
            request, db, book,
            error="Оценка должна быть от 0 до 5, текст — не пустой.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    crud.create_review(db, book_id, data)
    return redirect(f"/admin/books/{book_id}")


@router.post("/reviews/{review_id}/edit")
def edit_review(
    request: Request,
    review_id: int,
    rating: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    review = crud.get_review(db, review_id)
    if review is None:
        return redirect("/admin")
    book_id = review.book_id
    try:
        data = schemas.ReviewUpdate(rating=rating or None, text=text)
        crud.update_review(db, review, data)
    except ValidationError:
        book = crud.get_book(db, book_id)
        return _render_book_detail(
            request, db, book,
            error="Оценка должна быть от 0 до 5, текст — не пустой.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return redirect(
        f"/admin/books/{book_id}"
        f"?saved=review&saved_id={review_id}#review-{review_id}"
    )


@router.post("/reviews/{review_id}/delete")
def delete_review(review_id: int, db: Session = Depends(get_db)) -> Response:
    review = crud.get_review(db, review_id)
    if review is None:
        return redirect("/admin")
    book_id = review.book_id
    crud.delete_review(db, review)
    return redirect(f"/admin/books/{book_id}")


# ---------- Обложка ----------


@router.post("/books/{book_id}/cover")
async def upload_cover(
    request: Request,
    book_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Response:
    book = crud.get_book(db, book_id)
    if book is None:
        return not_found(request)
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        filename = storage.validate_and_save_cover(data, file.content_type)
    except storage.CoverError as exc:
        return _render_book_detail(
            request, db, book, error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    old_filename = book.cover_filename
    crud.set_book_cover(db, book, filename)
    storage.delete_cover(old_filename)
    return redirect(f"/admin/books/{book_id}")


@router.post("/books/{book_id}/cover/delete")
def delete_cover(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = crud.get_book(db, book_id)
    if book is not None:
        old_filename = book.cover_filename
        crud.set_book_cover(db, book, None)
        storage.delete_cover(old_filename)
    return redirect(f"/admin/books/{book_id}")
