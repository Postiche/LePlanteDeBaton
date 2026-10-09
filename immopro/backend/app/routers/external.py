"""Recherche multisource : base interne + BureauxLocaux + Geolocaux (liens et import manuel)."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..connectors import CONNECTORS, ConnectorNotConfigured, source_from_url
from ..db import get_db
from ..geo import normalize
from ..matching import evaluate
from ..models import ClientRequest, Contact, ExternalListing, ExternalSearch, Property, User, utcnow
from ..schemas import ExternalListingIn, PropertyIn
from ..security import get_current_user, require_writer
from ..services import fill_property_geo, find_property_duplicates, get_setting, recompute_for_property, to_dict
from .properties import property_out
from .requests import live_matches_for_request

router = APIRouter(prefix="/api/external", tags=["recherche externe"])


def listing_as_property(l: ExternalListing) -> dict:
    d = {
        "property_type": l.property_type,
        "transaction": l.transaction,
        "city": l.city,
        "postal_code": l.postal_code,
        "surface_total": l.surface,
    }
    if l.price is not None:
        if l.price_kind == "vente":
            d["sale_price"] = l.price
        elif l.price_kind == "loyer_annuel":
            d["annual_rent"] = l.price
        elif l.price_kind == "loyer_m2_an":
            d["rent_per_sqm"] = l.price
    return d


def listing_out(db: Session, l: ExternalListing, req: ClientRequest | None = None) -> dict:
    d = to_dict(l)
    days = int(get_setting(db, "external_freshness_days") or 14)
    ref = l.last_checked_at or l.consulted_at
    d["fresh"] = bool(ref and ref >= utcnow() - timedelta(days=days))
    d["freshness_days"] = days
    d["duplicates"] = find_property_duplicates(db, {"source_url": l.url, "postal_code": l.postal_code, "surface_total": l.surface})
    if req is not None:
        d["match"] = evaluate(req, listing_as_property(l), get_setting(db, "matching_weights"))
    return d


@router.get("/connectors")
def connectors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = []
    for c in CONNECTORS.values():
        tpl = get_setting(db, c.setting_key) or ""
        out.append({
            "key": c.key, "name": c.name, "base_url": c.base_url, "automatic_search": False,
            "mode": "lien_parametre" if tpl else "lien_simple",
            "status": "Recherche automatique non disponible (aucune API officielle configurée). Lien de recherche et import manuel des annonces.",
            "template_configured": bool(tpl), "template_vars": c.supported_template_vars(),
        })
    return out


@router.post("/search/{req_id}")
def multisource_search(req_id: int, request: Request, include_eliminated: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Bouton « Rechercher des biens » : critères de la demande appliqués aux trois sources."""
    r = db.get(ClientRequest, req_id)
    if r is None:
        raise HTTPException(404, "Demande introuvable.")
    internal = live_matches_for_request(db, r, include_eliminated)
    sources = []
    for c in CONNECTORS.values():
        entry = {"key": c.key, "name": c.name, "criteria": c.criteria_summary(r), "link": c.search_link(r, get_setting(db, c.setting_key)), "results": []}
        try:
            entry["results"] = c.fetch_listings(r)
            entry["automatic"] = True
        except ConnectorNotConfigured as exc:
            entry["automatic"] = False
            entry["message"] = str(exc)
        sources.append(entry)
    # Annonces externes déjà enregistrées (importées manuellement) et compatibles avec la demande
    listings = []
    for l in db.scalars(select(ExternalListing).where(ExternalListing.imported_property_id.is_(None), ExternalListing.is_demo == r.is_demo).order_by(ExternalListing.consulted_at.desc()).limit(500)):
        lo = listing_out(db, l, r)
        if lo["match"]["eliminated"] and not include_eliminated:
            continue
        listings.append(lo)
    listings.sort(key=lambda x: -x["match"]["score"])
    search = ExternalSearch(
        request_id=r.id,
        criteria={s["key"]: s["criteria"] for s in sources},
        results_summary={"internes": len(internal), "externes_enregistrees": len(listings), "liens": {s["key"]: s["link"]["url"] for s in sources}},
        user_id=user.id,
    )
    db.add(search)
    db.commit()
    log_action(db, user, "recherche_multisource", "request", r.id, None, request)
    return {"search_id": search.id, "searched_at": search.created_at.isoformat(), "internal": internal, "sources": sources, "external_listings": listings}


@router.get("/searches")
def search_history(request_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = [ExternalSearch.request_id == request_id] if request_id else []
    out = []
    for s in db.scalars(select(ExternalSearch).where(*conds).order_by(ExternalSearch.created_at.desc()).limit(100)):
        r = db.get(ClientRequest, s.request_id) if s.request_id else None
        out.append(to_dict(s) | {"request_label": (r.reference or r.title or r.client_name) if r else None})
    return out


@router.get("/listings")
def list_listings(q: str | None = None, source: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = []
    if source:
        conds.append(ExternalListing.source == source)
    if q:
        conds.append(or_(ExternalListing.title.ilike(f"%{q}%"), ExternalListing.city.ilike(f"%{q}%")))
    return [listing_out(db, l) for l in db.scalars(select(ExternalListing).where(*conds).order_by(ExternalListing.consulted_at.desc()).limit(300))]


@router.post("/listings")
def add_listing(payload: ExternalListingIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Import manuel d'une annonce consultée par l'utilisateur sur une plateforme externe."""
    existing = db.scalar(select(ExternalListing).where(ExternalListing.url == payload.url))
    if existing:
        raise HTTPException(409, {"message": "Cette annonce a déjà été enregistrée.", "duplicates": [{"id": existing.id, "title": existing.title, "url": existing.url}]})
    data = payload.model_dump()
    data["consulted_at"] = data["consulted_at"] or utcnow()
    l = ExternalListing(**data, source=source_from_url(payload.url), created_by=user.id, last_checked_at=data["consulted_at"], still_online=True)
    db.add(l)
    db.commit()
    log_action(db, user, "annonce_externe_ajoutee", "external_listing", l.id, {"url": l.url}, request)
    return listing_out(db, l)


@router.post("/listings/{lid}/check")
def check_listing(lid: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Contrôle de fraîcheur : l'utilisateur indique s'il a vérifié que l'annonce est toujours en ligne."""
    l = db.get(ExternalListing, lid)
    if l is None:
        raise HTTPException(404, "Annonce introuvable.")
    l.still_online = bool(payload.get("still_online", True))
    l.last_checked_at = utcnow()
    db.commit()
    return listing_out(db, l)


@router.delete("/listings/{lid}")
def delete_listing(lid: int, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    l = db.get(ExternalListing, lid)
    if l is None:
        raise HTTPException(404, "Annonce introuvable.")
    db.delete(l)
    db.commit()
    return {"ok": True}


@router.post("/listings/{lid}/to-property")
def listing_to_property(lid: int, payload: PropertyIn, request: Request, force: bool = False, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Enregistre une annonce externe dans la base des offres, après validation des champs par l'utilisateur."""
    l = db.get(ExternalListing, lid)
    if l is None:
        raise HTTPException(404, "Annonce introuvable.")
    if l.imported_property_id:
        raise HTTPException(409, "Annonce déjà enregistrée comme offre.")
    data = payload.model_dump(exclude_unset=True)
    data["source_url"] = l.url
    if not force:
        dups = find_property_duplicates(db, data)
        if dups:
            raise HTTPException(409, {"message": "Doublon probable détecté.", "duplicates": dups})
    agency_id = None
    if l.advertiser_name or l.advertiser_email:
        c = db.scalar(select(Contact).where(Contact.email == l.advertiser_email)) if l.advertiser_email else None
        if c is None:
            c = Contact(kind="annonceur", last_name=l.advertiser_name, email=l.advertiser_email, phone=l.advertiser_phone, origin=f"Annonce publique {CONNECTORS.get(l.source).name if l.source in CONNECTORS else l.source} : {l.url}", legal_basis="interet_legitime", is_public_listing_contact=True)
            db.add(c)
            db.flush()
        agency_id = c.id
    p = Property(**data, source_kind="externe", created_by=user.id)
    p.source_name = CONNECTORS[l.source].name if l.source in CONNECTORS else (p.source_name or "Annonce externe")
    p.source_consulted_at = l.consulted_at
    p.status = p.status or "active"
    p.agency_contact_id = p.agency_contact_id or agency_id
    fill_property_geo(p)
    db.add(p)
    db.flush()
    l.imported_property_id = p.id
    db.commit()
    log_action(db, user, "annonce_externe_enregistree", "property", p.id, {"url": l.url}, request)
    recompute_for_property(db, p)
    return property_out(db, p, full=True)


__all__ = ["router", "normalize"]
