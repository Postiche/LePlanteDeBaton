from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..config import get_settings
from ..db import get_db
from ..models import User
from ..schemas import UserIn, UserUpdate
from ..security import create_reset_token, get_current_user, hash_password, password_policy_errors, require_admin, revoke_user_sessions
from .auth import user_public

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [user_public(u) | {"is_active": u.is_active, "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None} for u in db.scalars(select(User).order_by(User.username))]


@router.get("/directory")
def directory(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": u.id, "full_name": u.full_name or u.username} for u in db.scalars(select(User).where(User.is_active.is_(True)))]


@router.post("")
def create_user(payload: UserIn, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    username = payload.username.lower()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "Cet identifiant existe déjà.")
    temp = None
    if payload.password:
        errors = password_policy_errors(payload.password, username)
        if errors:
            raise HTTPException(400, " ".join(errors))
        pwd = payload.password
    else:
        # Mot de passe temporaire aléatoire, affiché une seule fois à l'administrateur
        temp = pwd = secrets.token_urlsafe(12) + "A1!"
    u = User(
        username=username,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role=payload.role,
        password_hash=hash_password(pwd),
        must_change_password=True,
    )
    db.add(u)
    db.commit()
    log_action(db, admin, "utilisateur_cree", "user", u.id, {"username": username, "role": u.role}, request)
    return {"user": user_public(u), "temporary_password": temp}


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "Utilisateur introuvable.")
    data = payload.model_dump(exclude_unset=True)
    if u.id == admin.id and (data.get("role") not in (None, "admin") or data.get("is_active") is False):
        raise HTTPException(400, "Vous ne pouvez pas retirer vos propres droits d'administrateur.")
    for k, v in data.items():
        setattr(u, k, v)
    if data.get("is_active") is False:
        revoke_user_sessions(db, u.id)
    db.commit()
    log_action(db, admin, "utilisateur_modifie", "user", u.id, data, request)
    return user_public(u) | {"is_active": u.is_active}


@router.post("/{user_id}/reset-link")
def reset_link(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "Utilisateur introuvable.")
    token = create_reset_token(db, u, created_by=admin.id)
    log_action(db, admin, "lien_reinitialisation_cree", "user", u.id, None, request)
    url = f"{get_settings().public_base_url.rstrip('/')}/reinitialisation?token={token}"
    return {"url": url, "expires_minutes": get_settings().reset_token_minutes}


@router.post("/{user_id}/revoke-sessions")
def revoke(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    revoke_user_sessions(db, user_id)
    db.commit()
    log_action(db, admin, "sessions_revoquees", "user", user_id, None, request)
    return {"ok": True}
