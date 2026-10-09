"""CRM : entreprises, contacts, interactions/rappels, visites, droits RGPD."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..models import (
    ClientRequest,
    Company,
    Contact,
    Document,
    EmailDraft,
    Interaction,
    Match,
    Property,
    User,
    Visit,
    utcnow,
)
from ..schemas import CompanyIn, ContactIn, InteractionIn, VisitIn, VisitUpdate, to_utc_naive
from ..security import get_current_user, require_admin, require_writer
from ..services import contact_display_name, contact_summary, to_dict

router = APIRouter(prefix="/api", tags=["crm"])


# ---------------------------------------------------------------------------
# Entreprises
# ---------------------------------------------------------------------------


@router.get("/companies")
def list_companies(q: str | None = None, kind: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = []
    if q:
        conds.append(or_(Company.name.ilike(f"%{q}%"), Company.city.ilike(f"%{q}%")))
    if kind:
        conds.append(Company.kind == kind)
    return [to_dict(c) for c in db.scalars(select(Company).where(*conds).order_by(Company.name).limit(500))]


@router.post("/companies")
def create_company(payload: CompanyIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    c = Company(**payload.model_dump())
    db.add(c)
    db.commit()
    log_action(db, user, "entreprise_creee", "company", c.id, None, request)
    return to_dict(c)


@router.get("/companies/{cid}")
def get_company(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Company, cid)
    if c is None:
        raise HTTPException(404, "Entreprise introuvable.")
    d = to_dict(c)
    d["contacts"] = [contact_summary(x) for x in db.scalars(select(Contact).where(Contact.company_id == cid))]
    d["requests"] = [{"id": r.id, "reference": r.reference, "title": r.title, "status": r.status} for r in db.scalars(select(ClientRequest).where(ClientRequest.company_id == cid))]
    return d


@router.put("/companies/{cid}")
def update_company(cid: int, payload: CompanyIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    c = db.get(Company, cid)
    if c is None:
        raise HTTPException(404, "Entreprise introuvable.")
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    db.commit()
    log_action(db, user, "entreprise_modifiee", "company", c.id, None, request)
    return to_dict(c)


@router.delete("/companies/{cid}")
def delete_company(cid: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Company, cid)
    if c is None:
        raise HTTPException(404, "Entreprise introuvable.")
    db.delete(c)
    db.commit()
    log_action(db, admin, "entreprise_supprimee", "company", cid, None, request)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@router.get("/contacts")
def list_contacts(q: str | None = None, kind: str | None = None, company_id: int | None = None, demo: str = "all", page: int = Query(1, ge=1), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = []
    if q:
        like = f"%{q}%"
        conds.append(or_(Contact.first_name.ilike(like), Contact.last_name.ilike(like), Contact.email.ilike(like), Contact.phone.ilike(like), Contact.mobile.ilike(like)))
    if kind:
        conds.append(Contact.kind == kind)
    if company_id:
        conds.append(Contact.company_id == company_id)
    if demo == "real":
        conds.append(Contact.is_demo.is_(False))
    elif demo == "demo":
        conds.append(Contact.is_demo.is_(True))
    rows = db.scalars(select(Contact).where(*conds).order_by(Contact.last_name, Contact.first_name).offset((page - 1) * 200).limit(200))
    return [contact_summary(c) for c in rows]


@router.post("/contacts")
def create_contact(payload: ContactIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    data = payload.model_dump()
    if not (data.get("last_name") or data.get("first_name") or data.get("company_id") or data.get("email")):
        raise HTTPException(400, "Renseignez au moins un nom, une entreprise ou un email.")
    if data.get("email"):
        dup = db.scalar(select(Contact).where(Contact.email == data["email"]))
        if dup:
            raise HTTPException(409, {"message": "Un contact avec cet email existe déjà.", "duplicates": [contact_summary(dup)]})
    c = Contact(**data)
    db.add(c)
    db.commit()
    log_action(db, user, "contact_cree", "contact", c.id, None, request)
    return contact_summary(c)


@router.get("/contacts/{cid}")
def get_contact(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Contact, cid)
    if c is None:
        raise HTTPException(404, "Contact introuvable.")
    d = contact_summary(c)
    d["notes"] = c.notes
    d["requests"] = [{"id": r.id, "reference": r.reference, "title": r.title, "status": r.status} for r in db.scalars(select(ClientRequest).where(ClientRequest.contact_id == cid))]
    d["properties"] = [
        {"id": p.id, "reference": p.reference, "title": p.title, "city": p.city, "role": role}
        for role, col in (("propriétaire", Property.owner_contact_id), ("agence", Property.agency_contact_id), ("commercial", Property.sales_contact_id))
        for p in db.scalars(select(Property).where(col == cid))
    ]
    return d


@router.put("/contacts/{cid}")
def update_contact(cid: int, payload: ContactIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    c = db.get(Contact, cid)
    if c is None:
        raise HTTPException(404, "Contact introuvable.")
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    db.commit()
    log_action(db, user, "contact_modifie", "contact", c.id, None, request)
    return contact_summary(c)


@router.get("/contacts/{cid}/timeline")
def contact_timeline(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Historique chronologique : interactions, visites, emails, biens proposés."""
    c = db.get(Contact, cid)
    if c is None:
        raise HTTPException(404, "Contact introuvable.")
    return build_timeline(db, contact_id=cid)


def build_timeline(db: Session, contact_id: int | None = None, property_id: int | None = None, request_id: int | None = None) -> list[dict]:
    items = []
    conds_i = []
    if contact_id:
        conds_i.append(Interaction.contact_id == contact_id)
    if property_id:
        conds_i.append(Interaction.property_id == property_id)
    if request_id:
        conds_i.append(Interaction.request_id == request_id)
    for i in db.scalars(select(Interaction).where(or_(*conds_i)).order_by(Interaction.at.desc()).limit(300)):
        items.append({"type": "interaction", "at": i.at.isoformat(), "kind": i.kind, "subject": i.subject, "content": i.content, "id": i.id, "remind_at": i.remind_at.isoformat() if i.remind_at else None, "done": i.done, "property_id": i.property_id, "request_id": i.request_id})
    conds_v = []
    if contact_id:
        conds_v.append(Visit.contact_id == contact_id)
    if property_id:
        conds_v.append(Visit.property_id == property_id)
    if request_id:
        conds_v.append(Visit.request_id == request_id)
    for v in db.scalars(select(Visit).where(or_(*conds_v)).limit(200)):
        items.append({"type": "visite", "at": (v.confirmed_slot or v.created_at).isoformat(), "kind": v.status, "subject": f"Visite – {v.property.reference or v.property.title or v.property.city or ''}", "content": v.notes, "id": v.id, "property_id": v.property_id})
    conds_e = []
    if contact_id:
        conds_e.append(EmailDraft.contact_id == contact_id)
    if request_id:
        conds_e.append(EmailDraft.request_id == request_id)
    if conds_e:
        for e in db.scalars(select(EmailDraft).where(or_(*conds_e)).limit(200)):
            items.append({"type": "email", "at": (e.sent_confirmed_at or e.updated_at).isoformat(), "kind": e.status, "subject": e.subject, "content": None, "id": e.id})
    items.sort(key=lambda x: x["at"], reverse=True)
    return items


@router.get("/contacts/{cid}/export")
def export_contact_data(cid: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Droit d'accès RGPD : export de toutes les données relatives à une personne."""
    c = db.get(Contact, cid)
    if c is None:
        raise HTTPException(404, "Contact introuvable.")
    data = {
        "contact": to_dict(c),
        "demandes": [to_dict(r) for r in db.scalars(select(ClientRequest).where(ClientRequest.contact_id == cid))],
        "interactions": [to_dict(i) for i in db.scalars(select(Interaction).where(Interaction.contact_id == cid))],
        "visites": [to_dict(v) for v in db.scalars(select(Visit).where(Visit.contact_id == cid))],
        "emails": [to_dict(e) for e in db.scalars(select(EmailDraft).where(EmailDraft.contact_id == cid))],
        "documents": [to_dict(d) for d in db.scalars(select(Document).where(Document.owner_type == "contact", Document.owner_id == cid))],
    }
    log_action(db, admin, "rgpd_export", "contact", cid, None, request)
    return data


@router.delete("/contacts/{cid}")
def delete_contact(cid: int, request: Request, mode: str = "anonymiser", db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Droit à l'effacement : anonymisation (conserve l'historique commercial non nominatif) ou suppression."""
    c = db.get(Contact, cid)
    if c is None:
        raise HTTPException(404, "Contact introuvable.")
    if mode == "supprimer":
        db.execute(update(ClientRequest).where(ClientRequest.contact_id == cid).values(email=None, phone=None, contact_name=None))
        db.delete(c)
    else:
        for f in ("first_name", "email", "phone", "mobile", "address", "notes", "job_title", "civility"):
            setattr(c, f, None)
        c.last_name = f"Contact anonymisé #{c.id}"
        c.opposed_to_prospecting = True
        db.execute(update(ClientRequest).where(ClientRequest.contact_id == cid).values(email=None, phone=None, contact_name=None))
    db.commit()
    log_action(db, admin, f"rgpd_{mode}", "contact", cid, None, request)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Interactions et rappels
# ---------------------------------------------------------------------------


def interaction_out(db: Session, i: Interaction) -> dict:
    d = to_dict(i)
    if i.contact_id:
        d["contact_name"] = contact_display_name(db.get(Contact, i.contact_id))
    if i.property_id:
        p = db.get(Property, i.property_id)
        d["property_label"] = (p.reference or p.title or p.city) if p else None
    if i.request_id:
        r = db.get(ClientRequest, i.request_id)
        d["request_label"] = (r.reference or r.title or r.client_name) if r else None
    return d


@router.get("/interactions")
def list_interactions(
    contact_id: int | None = None,
    property_id: int | None = None,
    request_id: int | None = None,
    reminders: bool = False,
    due_only: bool = False,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = []
    if contact_id:
        conds.append(Interaction.contact_id == contact_id)
    if property_id:
        conds.append(Interaction.property_id == property_id)
    if request_id:
        conds.append(Interaction.request_id == request_id)
    order = Interaction.at.desc()
    if reminders:
        conds += [Interaction.remind_at.is_not(None), Interaction.done.is_(False)]
        order = Interaction.remind_at.asc()
        if due_only:
            conds.append(Interaction.remind_at <= utcnow() + timedelta(days=1))
    return [interaction_out(db, i) for i in db.scalars(select(Interaction).where(*conds).order_by(order).limit(limit))]


@router.post("/interactions")
def create_interaction(payload: InteractionIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    data = payload.model_dump()
    if data["kind"] == "email_envoye":
        raise HTTPException(400, "Utilisez « Marquer comme envoyé » depuis l'email concerné.")
    data["at"] = data["at"] or utcnow()
    i = Interaction(**data, user_id=user.id)
    db.add(i)
    db.commit()
    log_action(db, user, "interaction_creee", "interaction", i.id, {"kind": i.kind}, request)
    return interaction_out(db, i)


@router.patch("/interactions/{iid}")
def update_interaction(iid: int, payload: dict, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    i = db.get(Interaction, iid)
    if i is None:
        raise HTTPException(404, "Interaction introuvable.")
    if "done" in payload:
        i.done = bool(payload["done"])
    if "remind_at" in payload:
        try:
            i.remind_at = to_utc_naive(datetime.fromisoformat(payload["remind_at"])) if payload["remind_at"] else None
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, "Date de rappel invalide.") from exc
    if "content" in payload:
        i.content = payload["content"]
    if "subject" in payload:
        i.subject = payload["subject"]
    db.commit()
    return interaction_out(db, i)


@router.delete("/interactions/{iid}")
def delete_interaction(iid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    i = db.get(Interaction, iid)
    if i is None:
        raise HTTPException(404, "Interaction introuvable.")
    db.delete(i)
    db.commit()
    log_action(db, user, "interaction_supprimee", "interaction", iid, None, request)
    return {"ok": True}


@router.get("/timeline")
def timeline(property_id: int | None = None, request_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not property_id and not request_id:
        raise HTTPException(400, "Précisez une offre ou une demande.")
    return build_timeline(db, property_id=property_id, request_id=request_id)


# ---------------------------------------------------------------------------
# Visites
# ---------------------------------------------------------------------------


def visit_out(v: Visit) -> dict:
    d = to_dict(v)
    p = v.property
    d["property"] = {"id": p.id, "reference": p.reference, "title": p.title, "city": p.city, "address": p.address}
    d["contact"] = contact_summary(v.contact)
    d["request_label"] = (v.request.reference or v.request.title or v.request.client_name) if v.request else None
    return d


def _sync_match(db: Session, match_id: int | None, status: str) -> None:
    if not match_id:
        return
    m = db.get(Match, match_id)
    if m is not None:
        m.status = status
        m.status_updated_at = utcnow()


@router.get("/visits")
def list_visits(status: str | None = None, property_id: int | None = None, request_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = []
    if status:
        conds.append(Visit.status.in_(status.split(",")))
    if property_id:
        conds.append(Visit.property_id == property_id)
    if request_id:
        conds.append(Visit.request_id == request_id)
    return [visit_out(v) for v in db.scalars(select(Visit).where(*conds).order_by(Visit.updated_at.desc()).limit(300))]


@router.post("/visits")
def create_visit(payload: VisitIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    p = db.get(Property, payload.property_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    contact_id = payload.contact_id
    if not contact_id and payload.request_id:
        r = db.get(ClientRequest, payload.request_id)
        contact_id = r.contact_id if r else None
    v = Visit(
        property_id=p.id,
        request_id=payload.request_id,
        contact_id=contact_id,
        match_id=payload.match_id,
        proposed_slots=[s.isoformat() for s in payload.proposed_slots],
        notes=payload.notes,
        status="proposee",
        user_id=user.id,
        is_demo=p.is_demo,
    )
    db.add(v)
    _sync_match(db, payload.match_id, "visite_proposee")
    db.flush()
    db.add(Interaction(kind="visite", subject="Visite proposée", content=f"{len(v.proposed_slots or [])} créneau(x) proposé(s)", contact_id=contact_id, property_id=p.id, request_id=payload.request_id, match_id=payload.match_id, user_id=user.id, is_demo=p.is_demo))
    db.commit()
    log_action(db, user, "visite_proposee", "visit", v.id, None, request)
    return visit_out(v)


@router.patch("/visits/{vid}")
def update_visit(vid: int, payload: VisitUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    v = db.get(Visit, vid)
    if v is None:
        raise HTTPException(404, "Visite introuvable.")
    data = payload.model_dump(exclude_unset=True)
    if "proposed_slots" in data and data["proposed_slots"] is not None:
        v.proposed_slots = [s.isoformat() for s in payload.proposed_slots]
    for k in ("notes", "report"):
        if k in data:
            setattr(v, k, data[k])
    new_status = data.get("status")
    if new_status == "confirmee":
        # Une confirmation n'est jamais déduite : elle exige un créneau explicitement choisi par l'utilisateur.
        slot = payload.confirmed_slot
        if slot is None:
            raise HTTPException(400, "Indiquez le créneau confirmé par le client pour valider la visite.")
        v.confirmed_slot = slot
        _sync_match(db, v.match_id, "visite_confirmee")
    elif new_status == "effectuee":
        _sync_match(db, v.match_id, "visite_effectuee")
    if new_status:
        v.status = new_status
        labels = {"proposee": "Visite proposée", "confirmee": "Visite confirmée", "effectuee": "Visite effectuée", "annulee": "Visite annulée"}
        db.add(Interaction(kind="visite", subject=labels[new_status], content=data.get("report") or data.get("notes"), contact_id=v.contact_id, property_id=v.property_id, request_id=v.request_id, match_id=v.match_id, user_id=user.id, is_demo=v.is_demo))
    db.commit()
    log_action(db, user, "visite_modifiee", "visit", v.id, {"status": new_status} if new_status else None, request)
    return visit_out(v)
