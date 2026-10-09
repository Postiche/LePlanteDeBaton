from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..models import User, UserSession
from ..schemas import ChangePasswordIn, LoginIn, ProfileUpdate, ResetIn
from ..security import (
    _DUMMY_HASH,
    clear_session_cookies,
    client_ip,
    consume_reset_token,
    create_session,
    get_current_session,
    hash_password,
    is_login_locked,
    needs_rehash,
    password_policy_errors,
    record_login_attempt,
    revoke_user_sessions,
    verify_password,
)
from ..services import to_dict

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "must_change_password": u.must_change_password,
        "email_signature": u.email_signature,
    }


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    username = payload.username.strip().lower()
    if is_login_locked(db, username, ip):
        raise HTTPException(429, "Trop de tentatives. Réessayez dans quelques minutes.")
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        verify_password(_DUMMY_HASH, payload.password)  # temps de réponse constant
        ok = False
    else:
        ok = user.is_active and verify_password(user.password_hash, payload.password)
    record_login_attempt(db, username, ip, ok)
    if not ok:
        log_action(db, None, "connexion_echec", "user", None, {"username": username[:80]}, request)
        raise HTTPException(401, "Identifiant ou mot de passe incorrect.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    create_session(db, user, request, response)
    log_action(db, user, "connexion", "user", user.id, None, request)
    return {"user": user_public(user)}


@router.post("/logout")
def logout(request: Request, response: Response, sess: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    user = sess.user
    db.delete(db.get(UserSession, sess.id))
    db.commit()
    clear_session_cookies(response)
    log_action(db, user, "deconnexion", "user", user.id, None, request)
    return {"ok": True}


@router.get("/me")
def me(sess: UserSession = Depends(get_current_session)):
    return {"user": user_public(sess.user), "csrf_token": sess.csrf_token}


@router.put("/me")
def update_me(payload: ProfileUpdate, request: Request, sess: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    user = db.get(User, sess.user_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    log_action(db, user, "profil_modifie", "user", user.id, None, request)
    return {"user": user_public(user)}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, request: Request, sess: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    user = db.get(User, sess.user_id)
    if not verify_password(user.password_hash, payload.current_password):
        raise HTTPException(400, "Mot de passe actuel incorrect.")
    errors = password_policy_errors(payload.new_password, user.username)
    if errors:
        raise HTTPException(400, " ".join(errors))
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    revoke_user_sessions(db, user.id, except_id=sess.id)
    db.commit()
    log_action(db, user, "mot_de_passe_modifie", "user", user.id, None, request)
    return {"ok": True}


@router.post("/reset")
def reset_password(payload: ResetIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if is_login_locked(db, "reset:" + ip, ip):
        raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
    user = consume_reset_token(db, payload.token)
    if user is None:
        record_login_attempt(db, "reset:" + ip, ip, False)
        raise HTTPException(400, "Lien de réinitialisation invalide ou expiré.")
    errors = password_policy_errors(payload.new_password, user.username)
    if errors:
        db.rollback()
        raise HTTPException(400, " ".join(errors))
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    revoke_user_sessions(db, user.id)
    db.commit()
    log_action(db, user, "mot_de_passe_reinitialise", "user", user.id, None, request)
    return {"ok": True}


__all__ = ["router", "user_public", "to_dict"]
