"""Тесты crud-слоя напрямую (в обход HTTP): теги и выборка книг."""

from app import crud, schemas
from app.models import BookStatus


def make_book(db_session, **overrides):
    data = {
        "title": "T",
        "author": "A",
        "status": BookStatus.want_to_read,
    }
    data.update(overrides)
    return crud.create_book(db_session, schemas.BookCreate(**data))


# ---------- теги ----------


def test_get_or_create_tags_is_case_insensitive_and_dedups(db_session):
    tags = crud.get_or_create_tags(
        db_session, ["SciFi", "scifi", "  scifi  ", "Classic"]
    )
    db_session.commit()
    # 'scifi' в разных регистрах схлопывается в один тег.
    names = sorted(tag.name for tag in tags)
    assert len(tags) == 2
    assert names == ["Classic", "SciFi"]


def test_get_or_create_tags_reuses_existing(db_session):
    first = crud.get_or_create_tags(db_session, ["python"])
    db_session.commit()
    second = crud.get_or_create_tags(db_session, ["PYTHON"])
    db_session.commit()
    assert first[0].id == second[0].id


def test_get_or_create_tags_ignores_blank(db_session):
    assert crud.get_or_create_tags(db_session, ["", "   "]) == []


def test_delete_orphan_tags_removes_unlinked(db_session):
    from app import models

    book = make_book(db_session, tags=["keep", "drop"])
    # отвязываем 'drop', оставляем 'keep'
    crud.update_book(
        db_session, book, schemas.BookUpdate(tags=["keep"])
    )
    remaining = {tag.name for tag in db_session.query(models.Tag).all()}
    assert remaining == {"keep"}


# ---------- выборка книг ----------


def test_list_books_sort_title_asc(db_session):
    make_book(db_session, title="Bravo")
    make_book(db_session, title="Alpha")
    books = crud.list_books(db_session, sort="title", order="asc")
    assert [b.title for b in books] == ["Alpha", "Bravo"]


def test_list_books_filter_by_tag(db_session):
    make_book(db_session, title="With", tags=["target"])
    make_book(db_session, title="Without", tags=["other"])
    books = crud.list_books(db_session, tag="TARGET")  # регистр не важен
    assert [b.title for b in books] == ["With"]


def test_list_books_sort_date_read_only_read_status(db_session):
    # date_read осмысленен только у прочитанных: при сортировке по нему
    # непрочитанные книги отсекаются.
    make_book(
        db_session,
        title="Read",
        status=BookStatus.read,
        date_read="2024-01-01",
    )
    make_book(db_session, title="Want", status=BookStatus.want_to_read)
    books = crud.list_books(db_session, sort="date_read")
    assert [b.title for b in books] == ["Read"]
