"""Тесты JSON API по книгам: CRUD, валидация, авторизация, теги.

Форму ответа GET /api/books держим стабильной, её копирует Go-бенчмарк.
"""


def make_book(**overrides) -> dict:
    payload = {
        "title": "Дюна",
        "author": "Фрэнк Герберт",
        "year": 1965,
        "status": "read",
        "date_read": "2024-01-15",
        "tags": ["fantasy", "classic"],
    }
    payload.update(overrides)
    return payload


def create_book(admin_client, **overrides) -> dict:
    resp = admin_client.post("/api/books", json=make_book(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- создание ----------


def test_create_book_returns_201_and_shape(admin_client):
    body = create_book(admin_client)
    assert body["id"] > 0
    assert body["title"] == "Дюна"
    assert body["status"] == "read"
    assert {tag["name"] for tag in body["tags"]} == {"fantasy", "classic"}
    # cover_filename наружу не отдаём, только cover_url (тут пусто).
    assert "cover_filename" not in body
    assert body["cover_url"] is None


def test_create_book_requires_auth(client):
    resp = client.post("/api/books", json=make_book())
    assert resp.status_code == 401


def test_create_book_validation_error_on_bad_year(admin_client):
    resp = admin_client.post("/api/books", json=make_book(year=3000))
    assert resp.status_code == 422


def test_create_book_date_read_only_when_read(admin_client):
    # date_read при статусе не read даёт 422 (инвариант дублируется в схеме).
    resp = admin_client.post(
        "/api/books",
        json=make_book(status="reading", date_read="2024-01-15"),
    )
    assert resp.status_code == 422


# ---------- чтение ----------


def test_list_books_is_public(client, admin_client):
    create_book(admin_client, title="Первая")
    create_book(admin_client, title="Вторая")
    resp = client.get("/api/books")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # tags присутствует в форме списка (расширенная форма).
    assert all("tags" in item for item in data)


def test_get_book_detail_includes_reviews(client, admin_client):
    book = create_book(admin_client)
    admin_client.post(
        f"/api/books/{book['id']}/reviews",
        json={"rating": 5, "text": "Шедевр"},
    )
    resp = client.get(f"/api/books/{book['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["text"] == "Шедевр"


def test_get_missing_book_404(client):
    assert client.get("/api/books/9999").status_code == 404


# ---------- обновление ----------


def test_patch_book_partial_update(admin_client):
    book = create_book(admin_client)
    resp = admin_client.patch(
        f"/api/books/{book['id']}", json={"title": "Dune"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Фрэнк Герберт"  # не тронуто


def test_patch_book_replaces_tags(admin_client):
    book = create_book(admin_client)
    resp = admin_client.patch(
        f"/api/books/{book['id']}", json={"tags": ["scifi"]}
    )
    assert resp.status_code == 200
    assert {tag["name"] for tag in resp.json()["tags"]} == {"scifi"}


def test_patch_book_invariant_returns_422(admin_client):
    book = create_book(admin_client)  # status=read, date_read задан
    # меняем статус на reading, не сбрасывая date_read, это ломает инвариант.
    resp = admin_client.patch(
        f"/api/books/{book['id']}", json={"status": "reading"}
    )
    assert resp.status_code == 422


def test_patch_requires_auth(client, admin_client):
    book = create_book(admin_client)
    resp = client.patch(f"/api/books/{book['id']}", json={"title": "x"})
    assert resp.status_code == 401


# ---------- удаление ----------


def test_delete_book(admin_client):
    book = create_book(admin_client)
    assert admin_client.delete(f"/api/books/{book['id']}").status_code == 204
    assert admin_client.get(f"/api/books/{book['id']}").status_code == 404


def test_delete_requires_auth(client, admin_client):
    book = create_book(admin_client)
    resp = client.delete(f"/api/books/{book['id']}")
    assert resp.status_code == 401
