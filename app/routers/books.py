from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
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
