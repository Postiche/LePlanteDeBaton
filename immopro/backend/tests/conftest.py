import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="immopro-tests-"))
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "COOKIE_SECURE": "false",
        "UPLOAD_DIR": str(_TMP / "uploads"),
        "BACKUP_DIR": str(_TMP / "backups"),
        "GEOCODER_ENABLED": "false",
        "SECRET_KEY": "test-secret-key-test-secret-key-0123456789",
        "FRONTEND_DIST": str(_TMP / "no-dist"),
        "LOGIN_MAX_ATTEMPTS": "5",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import Base, SessionLocal, get_engine, reset_engine  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402

ADMIN_PASSWORD = "Adm1n-Mot-De-Passe!"


@pytest.fixture(autouse=True)
def fresh_db():
    get_settings.cache_clear()
    reset_engine()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(username="admin", full_name="Admin Test", role="admin", password_hash=hash_password(ADMIN_PASSWORD), email="admin@exemple.test"))
        db.add(User(username="lecteur", full_name="Lecteur", role="lecteur", password_hash=hash_password(ADMIN_PASSWORD)))
        db.commit()
    yield


@pytest.fixture
def client():
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def login(c, username="admin", password=ADMIN_PASSWORD):
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    me = c.get("/api/auth/me").json()
    c.headers["X-CSRF-Token"] = me["csrf_token"]
    return me


@pytest.fixture
def auth_client(client):
    login(client)
    return client
