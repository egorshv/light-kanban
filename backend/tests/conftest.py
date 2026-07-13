import pytest

from app.repo import db
from app.services import auth


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def uid(conn, monkeypatch):
    """Пользователь по умолчанию для юнит-тестов сервисов."""
    monkeypatch.setenv("KANBAN_JWT_SECRET", "test-secret")
    return auth.sign_up(conn, "user@test.ru", "password1")["id"]
