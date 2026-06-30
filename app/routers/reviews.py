from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.routers.books import get_book_or_404

router = APIRouter(prefix="/api/books/{book_id}/reviews", tags=["reviews"])


@router.get("", response_model=list[schemas.ReviewRead])
def list_reviews(
    book: models.Book = Depends(get_book_or_404),
    db: Session = Depends(get_db),
) -> list[models.Review]:
    return list(crud.list_reviews(db, book.id))


@router.post(
    "", response_model=schemas.ReviewRead, status_code=status.HTTP_201_CREATED
)
def create_review(
    data: schemas.ReviewCreate,
    book: models.Book = Depends(get_book_or_404),
    db: Session = Depends(get_db),
) -> models.Review:
    return crud.create_review(db, book.id, data)
