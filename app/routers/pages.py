from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app import crud
from app.database import get_db
from app.templating import not_found, render


router = APIRouter(tags=["pages"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    sort: str = Query("created"),
    order: str = Query("desc"),
    tag: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    books = crud.list_books(
        db, limit=1000, sort=sort, order=order, tag=tag or None
    )
    all_tags = crud.list_tags(db)
    return render(
        request,
        "index.html",
        {
            "books": books,
            "all_tags": all_tags,
            "sort": sort,
            "order": order,
            "active_tag": tag or None,
        },
    )


@router.get("/books/{book_id}", response_class=HTMLResponse)
def book_detail(
    request: Request, book_id: int, db: Session = Depends(get_db)
) -> Response:
    book = crud.get_book(db, book_id)
    if book is None:
        return not_found(request)
    reviews = crud.list_reviews(db, book_id, asc=True)
    return render(
        request, "book_detail.html", {"book": book, "reviews": reviews}
    )
