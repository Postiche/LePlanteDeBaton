"""Authentification : Argon2id, sessions serveur, CSRF, limitation des tentatives."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import LoginAttempt, PasswordResetToken, User, UserSession, utcnow

# Paramètres Argon2id (RFC 9106, profil « faible mémoire » renforcé)
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "X-CSRF-Token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Hachage factice pour égaliser le temps de réponse quand l'utilisateur n'existe pas
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def password_policy_errors(password: str, username: str | None = None) -> list[str]:
    errors = []
    if len(password) < 12:
        errors.append("Le mot de passe doit contenir au moins 12 caractères.")
    if len(password) > 256:
        errors.append("Le mot de passe est trop long.")
    classes = sum(
        [
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        ]
    )
    if classes < 3:
        errors.append("Utilisez au moins 3 types de caractères (minuscules, majuscules, chiffres, symboles).")
    if username and username.lower() in password.lower():
        errors.append("Le mot de passe ne doit pas contenir l'identifiant.")
    return errors


def _token_digest(token: str) -> str:
    key = (get_settings().secret_key or "dev-only-key").encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "inconnue")[:64]


# ---------------------------------------------------------------------------
# Limitation des tentatives
# ---------------------------------------------------------------------------


def is_login_locked(db: Session, username: str, ip: str) -> bool:
    s = get_settings()
    since = utcnow() - timedelta(minutes=s.login_lock_minutes)
    by_user = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.username == username.lower(), LoginAttempt.success.is_(False), LoginAttempt.at >= since
        )
    )
    by_ip = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.ip == ip, LoginAttempt.success.is_(False), LoginAttempt.at >= since
        )
    )
    return (by_user or 0) >= s.login_max_attempts or (by_ip or 0) >= s.login_max_attempts * 4


def record_login_attempt(db: Session, username: str, ip: str, success: bool) -> None:
    db.add(LoginAttempt(username=username.lower()[:80], ip=ip, success=success))
    if success:
        # Une connexion réussie remet à zéro le compteur de l'identifiant
        db.execute(delete(LoginAttempt).where(LoginAttempt.username == username.lower(), LoginAttempt.success.is_(False)))
    db.commit()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def create_session(db: Session, user: User, request: Request, response: Response) -> UserSession:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    now = utcnow()
    sess = UserSession(
        token_hash=_token_digest(token),
        csrf_token=csrf,
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=s.session_max_hours),
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:300],
    )
    db.add(sess)
    user.last_login_at = now
    db.commit()
    set_session_cookies(response, token, csrf)
    return sess


def set_session_cookies(response: Response, token: str, csrf: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie_name,
        token,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
        max_age=s.session_max_hours * 3600,
    )
    # Cookie CSRF lisible par le frontend (double soumission) ; la valeur fait aussi foi côté serveur.
    response.set_cookie(
        s.csrf_cookie_name,
        csrf,
        httponly=False,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
        max_age=s.session_max_hours * 3600,
    )


def clear_session_cookies(response: Response) -> None:
    s = get_settings()
    for name in (s.session_cookie_name, s.csrf_cookie_name):
        response.delete_cookie(name, path="/", secure=s.cookie_secure, samesite="strict")


def _load_session(db: Session, request: Request) -> UserSession | None:
    s = get_settings()
    token = request.cookies.get(s.session_cookie_name)
    if not token or len(token) > 200:
        return None
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == _token_digest(token)))
    if sess is None:
        return None
    now = utcnow()
    if sess.expires_at <= now or sess.last_seen_at + timedelta(minutes=s.session_idle_minutes) <= now:
        db.delete(sess)
        db.commit()
        return None
    if not sess.user or not sess.user.is_active:
        return None
    # Rafraîchissement de l'activité au plus une fois par minute
    if (now - sess.last_seen_at).total_seconds() > 60:
        sess.last_seen_at = now
        db.commit()
    return sess


def get_current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    sess = _load_session(db, request)
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise.")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not hmac.compare_digest(sent, sess.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Jeton CSRF invalide ou manquant. Rechargez la page.")
    request.state.user = sess.user
    return sess


def get_current_user(sess: UserSession = Depends(get_current_session)) -> User:
    return sess.user


def require_writer(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "collaborateur"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants (lecture seule).")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs.")
    return user


def revoke_user_sessions(db: Session, user_id: int, except_id: int | None = None) -> None:
    q = delete(UserSession).where(UserSession.user_id == user_id)
    if except_id is not None:
        q = q.where(UserSession.id != except_id)
    db.execute(q)


# ---------------------------------------------------------------------------
# Récupération d'accès (jeton à usage unique, durée limitée)
# ---------------------------------------------------------------------------


def create_reset_token(db: Session, user: User, created_by: int | None = None) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_token_digest(token),
            expires_at=utcnow() + timedelta(minutes=get_settings().reset_token_minutes),
            created_by=created_by,
        )
    )
    db.commit()
    return token


def consume_reset_token(db: Session, token: str) -> User | None:
    rec = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _token_digest(token)))
    if rec is None or rec.used_at is not None or rec.expires_at <= utcnow():
        return None
    rec.used_at = utcnow()
    return db.get(User, rec.user_id)
