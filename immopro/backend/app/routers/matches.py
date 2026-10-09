from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..matching import evaluate
from ..models import PIPELINE_LABELS, ClientRequest, Interaction, Match, Property, User, utcnow
from ..schemas import MatchUpdate
from ..security import get_current_user, require_admin, require_writer
from ..services import contact_summary, get_setting, recompute_all

router = APIRouter(prefix="/api/matches", tags=["correspondances"])


def match_out(m: Match) -> dict:
    p, r = m.property, m.request
    return {
        "id": m.id,
        "score": m.score,
        "score_potential": m.score_potential,
        "eliminated": m.eliminated,
        "status": m.status,
        "status_label": PIPELINE_LABELS.get(m.status, m.status),
        "dismissed": m.dismissed,
        "computed_at": m.computed_at.isoformat() if m.computed_at else None,
        "details": m.details,
        "property": {"id": p.id, "reference": p.reference, "title": p.title, "city": p.city, "postal_code": p.postal_code, "surface_total": p.surface_total, "property_type": p.property_type, "transaction": p.transaction, "sale_price": p.sale_price, "annual_rent": p.annual_rent, "is_demo": p.is_demo},
        "request": {"id": r.id, "reference": r.reference, "title": r.title, "client_name": r.client_name or (r.company.name if r.company else None), "contact": contact_summary(r.contact), "contact_name": r.contact_name, "email": r.email, "phone": r.phone, "priority": r.priority},
    }


@router.get("")
def list_matches(
    status: str | None = None,
    min_score: float | None = None,
    request_id: int | None = None,
    property_id: int | None = None,
    include_dismissed: bool = False,
    demo: str = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = [Match.eliminated.is_(False)]
    if not include_dismissed:
        conds.append(Match.dismissed.is_(False))
    if status:
        conds.append(Match.status.in_(status.split(",")))
    if min_score is not None:
        conds.append(Match.score >= min_score)
    if request_id:
        conds.append(Match.request_id == request_id)
    if property_id:
        conds.append(Match.property_id == property_id)
    q = select(Match).join(Property, Match.property_id == Property.id)
    if demo == "real":
        conds.append(Property.is_demo.is_(False))
    elif demo == "demo":
        conds.append(Property.is_demo.is_(True))
    total = db.scalar(select(func.count()).select_from(Match).join(Property, Match.property_id == Property.id).where(*conds))
    rows = db.scalars(q.where(*conds).order_by(Match.score.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"total": total, "items": [match_out(m) for m in rows], "labels": PIPELINE_LABELS}


class EnsureIn(BaseModel):
    request_id: int
    property_id: int


@router.post("/ensure")
def ensure_match(payload: EnsureIn, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Crée (si besoin) l'enregistrement de suivi d'un couple demande/offre, même sous le seuil."""
    m = db.scalar(select(Match).where(Match.request_id == payload.request_id, Match.property_id == payload.property_id))
    if m is None:
        r, p = db.get(ClientRequest, payload.request_id), db.get(Property, payload.property_id)
        if r is None or p is None:
            raise HTTPException(404, "Demande ou offre introuvable.")
        res = evaluate(r, p, get_setting(db, "matching_weights"))
        m = Match(request_id=r.id, property_id=p.id, score=res["score"], score_potential=res["score_potential"], eliminated=res["eliminated"], details=res)
        db.add(m)
        db.commit()
    return match_out(m)


@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(Match, match_id)
    if m is None:
        raise HTTPException(404, "Correspondance introuvable.")
    return match_out(m)


@router.patch("/{match_id}")
def update_match(match_id: int, payload: MatchUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    m = db.get(Match, match_id)
    if m is None:
        raise HTTPException(404, "Correspondance introuvable.")
    changes = {}
    if payload.status and payload.status != m.status:
        changes["status"] = [m.status, payload.status]
        m.status = payload.status
        m.status_updated_at = utcnow()
    if payload.dismissed is not None:
        m.dismissed = payload.dismissed
        changes["dismissed"] = payload.dismissed
    if changes or payload.note:
        r = m.request
        db.add(
            Interaction(
                kind="statut",
                subject=f"Correspondance : {PIPELINE_LABELS.get(m.status, m.status)}",
                content=payload.note,
                contact_id=r.contact_id,
                company_id=r.company_id,
                property_id=m.property_id,
                request_id=m.request_id,
                match_id=m.id,
                user_id=user.id,
                is_demo=m.property.is_demo,
            )
        )
    db.commit()
    log_action(db, user, "correspondance_modifiee", "match", m.id, changes or None, request)
    return match_out(m)


@router.post("/recompute")
def recompute(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    n = recompute_all(db)
    log_action(db, admin, "correspondances_recalculees", "match", None, {"demandes": n}, request)
    return {"requests": n}
