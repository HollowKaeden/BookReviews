from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app import crud, schemas, storage
from app.config import settings
from app.database import get_db
from app.models import Book

router = APIRouter(prefix="/api/books", tags=["books"])


def get_book_or_404(book_id: int, db: Session = Depends(get_db)) -> Book:
    """Достаёт книгу или отдаёт 404. Переиспользуется всеми ручками по id."""
    book = crud.get_book(db, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


@router.get("", response_model=list[schemas.BookRead])
def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[Book]:
    return list(crud.list_books(db, skip=skip, limit=limit))


@router.post(
    "", response_model=schemas.BookRead, status_code=status.HTTP_201_CREATED
)
def create_book(
    data: schemas.BookCreate, db: Session = Depends(get_db)
) -> Book:
    return crud.create_book(db, data)


@router.get("/{book_id}", response_model=schemas.BookDetail)
def get_book(book: Book = Depends(get_book_or_404)) -> Book:
    return book


@router.patch("/{book_id}", response_model=schemas.BookRead)
def update_book(
    data: schemas.BookUpdate,
    book: Book = Depends(get_book_or_404),
    db: Session = Depends(get_db),
) -> Book:
    try:
        return crud.update_book(db, book, data)
    except crud.InvariantError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book: Book = Depends(get_book_or_404), db: Session = Depends(get_db)
) -> None:
    crud.delete_book(db, book)


@router.put("/{book_id}/cover", response_model=schemas.BookRead)
async def set_cover(
    book: Book = Depends(get_book_or_404),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Book:
    if file.content_type not in storage.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type (allowed: jpeg, png, webp, gif)",
        )
    # Читаем на 1 байт больше лимита — чтобы поймать превышение, не загружая
    # в память гигабайты.
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    old_filename = book.cover_filename
    filename = storage.save_cover(data, file.content_type)
    crud.set_book_cover(db, book, filename)
    storage.delete_cover(old_filename)  # подчищаем старую обложку
    return book


@router.delete("/{book_id}/cover", response_model=schemas.BookRead)
def delete_cover(
    book: Book = Depends(get_book_or_404), db: Session = Depends(get_db)
) -> Book:
    old_filename = book.cover_filename
    crud.set_book_cover(db, book, None)
    storage.delete_cover(old_filename)
    return book
