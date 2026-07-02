"""Тесты обложек: валидация в storage и загрузка через JSON-ручку."""

import pytest

from app import storage

# Содержимое файла не парсим, важны только content-type и размер.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


# ---------- storage (юнит) ----------


def test_validate_cover_rejects_unsupported_type():
    with pytest.raises(storage.UnsupportedImageType):
        storage.validate_cover(PNG_BYTES, "text/plain")


def test_validate_cover_rejects_too_large(monkeypatch):
    monkeypatch.setattr(storage.settings, "max_upload_bytes", 10)
    with pytest.raises(storage.FileTooLarge):
        storage.validate_cover(b"0" * 11, "image/png")


def test_validate_cover_accepts_allowed():
    # не должно бросать
    storage.validate_cover(PNG_BYTES, "image/png")


# ---------- API ----------


@pytest.fixture
def book_id(admin_client) -> int:
    resp = admin_client.post(
        "/api/books", json={"title": "T", "author": "A"}
    )
    return resp.json()["id"]


def test_upload_cover_sets_url(admin_client, book_id):
    resp = admin_client.put(
        f"/api/books/{book_id}/cover",
        files={"file": ("cover.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["cover_url"].startswith("/media/")


def test_upload_cover_unsupported_type_415(admin_client, book_id):
    resp = admin_client.put(
        f"/api/books/{book_id}/cover",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_upload_cover_requires_auth(client, book_id):
    resp = client.put(
        f"/api/books/{book_id}/cover",
        files={"file": ("cover.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 401


def test_delete_cover_clears_url(admin_client, book_id):
    admin_client.put(
        f"/api/books/{book_id}/cover",
        files={"file": ("cover.png", PNG_BYTES, "image/png")},
    )
    resp = admin_client.delete(f"/api/books/{book_id}/cover")
    assert resp.status_code == 200
    assert resp.json()["cover_url"] is None
