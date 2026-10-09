from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..matching import evaluate
from ..models import ClientRequest, Match, Property, User
from ..schemas import RequestIn
from ..security import get_current_user, require_admin, require_writer
from ..services import contact_summary, find_request_duplicates, get_setting, recompute_for_request, to_dict
from .properties import demo_filter, property_out

router = APIRouter(prefix="/api/requests", tags=["demandes"])


def request_out(db: Session, r: ClientRequest, full: bool = False) -> dict:
    d = to_dict(r)
    d["company_name"] = r.company.name if r.company else None
    d["display_client"] = r.client_name or (r.company.name if r.company else None) or (contact_summary(r.contact) or {}).get("display_name")
    d["match_count"] = db.scalar(select(func.count()).select_from(Match).where(Match.request_id == r.id, Match.eliminated.is_(False), Match.dismissed.is_(False)))
    if full:
        d["contact"] = contact_summary(r.contact)
    return d


@router.get("")
def list_requests(
    q: str | None = None,
    status: str | None = "active",
    priority: str | None = None,
    property_type: str | None = None,
    transaction: str | None = None,
    department: str | None = None,
    demo: str = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = []
    if q:
        like = f"%{q.strip()}%"
        conds.append(or_(ClientRequest.reference.ilike(like), ClientRequest.title.ilike(like), ClientRequest.client_name.ilike(like), ClientRequest.contact_name.ilike(like), ClientRequest.comments.ilike(like), ClientRequest.email.ilike(like)))
    if status and status != "toutes":
        conds.append(ClientRequest.status == status)
    if priority:
        conds.append(ClientRequest.priority == priority)
    if transaction:
        conds.append(ClientRequest.transaction == transaction)
    f = demo_filter(ClientRequest, demo)
    if f is not None:
        conds.append(f)
    rows = list(db.scalars(select(ClientRequest).where(*conds).order_by(ClientRequest.updated_at.desc())))
    # Filtres sur champs JSON appliqués en Python (compatibilité SQLite/PostgreSQL)
    if property_type:
        rows = [r for r in rows if property_type in (r.property_types or [])]
    if department:
        rows = [r for r in rows if department.upper().zfill(2) in (r.departments or [])]
    total = len(rows)
    rows = rows[(page - 1) * page_size : page * page_size]
    return {"total": total, "page": page, "page_size": page_size, "items": [request_out(db, r) for r in rows]}


@router.post("")
def create_request(payload: RequestIn, request: Request, force: bool = False, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    data = payload.model_dump(exclude_unset=True)
    if not force:
        dups = find_request_duplicates(db, data)
        if dups:
            raise HTTPException(409, {"message": "Une demande active similaire existe déjà.", "duplicates": dups})
    _check_ranges(data)
    r = ClientRequest(created_by=user.id, source_kind=data.pop("source_kind", None) or "manuel")
    for k, v in data.items():
        setattr(r, k, v)
    r.status = r.status or "active"
    r.priority = r.priority or "normale"
    db.add(r)
    db.commit()
    log_action(db, user, "demande_creee", "request", r.id, {"reference": r.reference}, request)
    recompute_for_request(db, r)
    return request_out(db, r, full=True)


def _check_ranges(data: dict) -> None:
    if data.get("surface_min") and data.get("surface_max") and data["surface_min"] > data["surface_max"]:
        raise HTTPException(400, "La surface minimale dépasse la surface maximale.")


@router.get("/{req_id}")
def get_request(req_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(ClientRequest, req_id)
    if r is None:
        raise HTTPException(404, "Demande introuvable.")
    return request_out(db, r, full=True)


@router.put("/{req_id}")
def update_request(req_id: int, payload: RequestIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    r = db.get(ClientRequest, req_id)
    if r is None:
        raise HTTPException(404, "Demande introuvable.")
    data = payload.model_dump(exclude_unset=True)
    merged = to_dict(r) | data
    _check_ranges(merged)
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    log_action(db, user, "demande_modifiee", "request", r.id, {"champs": sorted(data)}, request)
    recompute_for_request(db, r)
    return request_out(db, r, full=True)


@router.delete("/{req_id}")
def delete_request(req_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    r = db.get(ClientRequest, req_id)
    if r is None:
        raise HTTPException(404, "Demande introuvable.")
    db.delete(r)
    db.commit()
    log_action(db, admin, "demande_supprimee", "request", req_id, None, request)
    return {"ok": True}


@router.get("/{req_id}/matches")
def request_matches(req_id: int, include_eliminated: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Biens adaptés à cette demande (calcul en direct sur toutes les offres actives)."""
    r = db.get(ClientRequest, req_id)
    if r is None:
        raise HTTPException(404, "Demande introuvable.")
    return live_matches_for_request(db, r, include_eliminated)


def live_matches_for_request(db: Session, r: ClientRequest, include_eliminated: bool = False) -> list[dict]:
    weights = get_setting(db, "matching_weights")
    stored = {m.property_id: m for m in db.scalars(select(Match).where(Match.request_id == r.id))}
    out = []
    for p in db.scalars(select(Property).where(Property.status.in_(("active", "sous_offre")), Property.is_demo == r.is_demo)):
        res = evaluate(r, p, weights)
        if res["eliminated"] and not include_eliminated:
            continue
        m = stored.get(p.id)
        d = property_out(db, p)
        d["sales_contact"] = contact_summary(p.sales_contact)
        d["agency_contact"] = contact_summary(p.agency_contact)
        out.append({"property": d, "match_id": m.id if m else None, "status": m.status if m else None, "dismissed": m.dismissed if m else False, **res})
    out.sort(key=lambda x: (x["eliminated"], -x["score"], -x["score_potential"]))
    return out
