from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import require_admin
from app.database import get_db
from app.routers.books import get_book_or_404

admin_only = [Depends(require_admin)]

router = APIRouter(prefix="/api/books/{book_id}/reviews", tags=["reviews"])

# Правка/удаление — на плоском пути: id отзыва глобально уникален,
# book_id в URL для мутаций избыточен.
review_router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def get_review_or_404(
    review_id: int, db: Session = Depends(get_db)
) -> models.Review:
    review = crud.get_review(db, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    return review


@router.get("", response_model=list[schemas.ReviewRead])
def list_reviews(
    book: models.Book = Depends(get_book_or_404),
    db: Session = Depends(get_db),
) -> list[models.Review]:
    return list(crud.list_reviews(db, book.id))


@router.post(
    "",
    response_model=schemas.ReviewRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=admin_only,
)
def create_review(
    data: schemas.ReviewCreate,
    book: models.Book = Depends(get_book_or_404),
    db: Session = Depends(get_db),
) -> models.Review:
    return crud.create_review(db, book.id, data)


@review_router.patch(
    "/{review_id}", response_model=schemas.ReviewRead, dependencies=admin_only
)
def update_review(
    data: schemas.ReviewUpdate,
    review: models.Review = Depends(get_review_or_404),
    db: Session = Depends(get_db),
) -> models.Review:
    return crud.update_review(db, review, data)


@review_router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin_only,
)
def delete_review(
    review: models.Review = Depends(get_review_or_404),
    db: Session = Depends(get_db),
) -> None:
    crud.delete_review(db, review)
