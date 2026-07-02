"""Тесты JSON API по отзывам: CRUD, связь книга↔отзыв, валидация."""

import pytest


@pytest.fixture
def book(admin_client) -> dict:
    resp = admin_client.post(
        "/api/books",
        json={"title": "Книга", "author": "Автор", "status": "read"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def add_review(admin_client, book_id, **overrides) -> dict:
    payload = {"rating": 4, "text": "Хорошо"}
    payload.update(overrides)
    resp = admin_client.post(f"/api/books/{book_id}/reviews", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_review_links_to_book(admin_client, book):
    review = add_review(admin_client, book["id"])
    assert review["book_id"] == book["id"]
    assert review["rating"] == 4


def test_create_review_requires_auth(client, book):
    resp = client.post(
        f"/api/books/{book['id']}/reviews",
        json={"rating": 4, "text": "Хорошо"},
    )
    assert resp.status_code == 401


def test_create_review_on_missing_book_404(admin_client):
    resp = admin_client.post(
        "/api/books/9999/reviews", json={"rating": 4, "text": "x"}
    )
    assert resp.status_code == 404


@pytest.mark.parametrize("rating", [-1, 6])
def test_create_review_rating_out_of_range(admin_client, book, rating):
    resp = admin_client.post(
        f"/api/books/{book['id']}/reviews",
        json={"rating": rating, "text": "x"},
    )
    assert resp.status_code == 422


def test_create_review_empty_text_rejected(admin_client, book):
    resp = admin_client.post(
        f"/api/books/{book['id']}/reviews",
        json={"rating": 4, "text": ""},
    )
    assert resp.status_code == 422


def test_list_reviews_is_public(client, admin_client, book):
    add_review(admin_client, book["id"], text="Первый")
    add_review(admin_client, book["id"], text="Второй")
    resp = client.get(f"/api/books/{book['id']}/reviews")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_patch_review(admin_client, book):
    review = add_review(admin_client, book["id"])
    resp = admin_client.patch(
        f"/api/reviews/{review['id']}", json={"rating": 5}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating"] == 5
    assert data["text"] == "Хорошо"  # не тронуто


def test_delete_review(admin_client, book):
    review = add_review(admin_client, book["id"])
    assert (
        admin_client.delete(f"/api/reviews/{review['id']}").status_code == 204
    )
    resp = admin_client.get(f"/api/books/{book['id']}/reviews")
    assert resp.json() == []


def test_delete_review_requires_auth(client, admin_client, book):
    review = add_review(admin_client, book["id"])
    resp = client.delete(f"/api/reviews/{review['id']}")
    assert resp.status_code == 401


def test_deleting_book_cascades_reviews(admin_client, book, db_session):
    """Удаление книги уносит её отзывы (ondelete=CASCADE + passive_deletes)."""
    from app import models

    add_review(admin_client, book["id"])
    assert admin_client.delete(f"/api/books/{book['id']}").status_code == 204

    remaining = (
        db_session.query(models.Review)
        .filter_by(book_id=book["id"])
        .count()
    )
    assert remaining == 0
