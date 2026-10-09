from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import create_reset_token

from .conftest import ADMIN_PASSWORD, login


def test_api_requires_authentication(client):
    for url in ["/api/properties", "/api/requests", "/api/dashboard", "/api/contacts", "/api/files/1", "/api/settings", "/api/matches"]:
        assert client.get(url).status_code == 401, url
    assert client.get("/api/health").status_code == 200


def test_password_hash_is_argon2id():
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == "admin"))
        assert u.password_hash.startswith("$argon2id$")


def test_login_sets_secure_cookies(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("immopro_session="))
    assert "HttpOnly" in session and "SameSite=strict" in session.replace("Strict", "strict")
    assert "password" not in r.text.lower() or "must_change_password" in r.text


def test_wrong_password_and_lockout(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "admin", "password": "mauvais"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert r.status_code == 429


def test_csrf_required_for_writes(client):
    login(client)
    token = client.headers.pop("X-CSRF-Token")
    assert client.post("/api/properties", json={"title": "x"}).status_code == 403
    client.headers["X-CSRF-Token"] = token
    assert client.post("/api/properties", json={"title": "x"}).status_code == 200


def test_logout_invalidates_session(client):
    login(client)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_reader_cannot_write(client):
    login(client, "lecteur")
    assert client.get("/api/properties").status_code == 200
    assert client.post("/api/properties", json={"title": "x"}).status_code == 403


def test_password_policy_and_change(auth_client):
    r = auth_client.post("/api/auth/change-password", json={"current_password": ADMIN_PASSWORD, "new_password": "court"})
    assert r.status_code == 400
    r = auth_client.post("/api/auth/change-password", json={"current_password": ADMIN_PASSWORD, "new_password": "Nouveau-Mot2Passe"})
    assert r.status_code == 200


def test_reset_token_single_use(client):
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == "admin"))
        token = create_reset_token(db, u)
    assert client.post("/api/auth/reset", json={"token": token, "new_password": "Reinit-Mot2Passe!"}).status_code == 200
    assert client.post("/api/auth/reset", json={"token": token, "new_password": "Autre-Mot2Passe!"}).status_code == 400
    login(client, "admin", "Reinit-Mot2Passe!")


def test_admin_creates_collaborator_with_temporary_password(auth_client):
    r = auth_client.post("/api/users", json={"username": "collab", "role": "collaborateur", "full_name": "Collab"})
    assert r.status_code == 200
    temp = r.json()["temporary_password"]
    assert temp and len(temp) >= 12
    auth_client.cookies.clear()
    me = login(auth_client, "collab", temp)
    assert me["user"]["must_change_password"] is True


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in r.headers["content-security-policy"]
