from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..matching import evaluate
from ..models import ClientRequest, Document, Match, Property, User
from ..pdfgen import property_pdf
from ..schemas import PropertyIn
from ..security import get_current_user, require_admin, require_writer
from ..services import (
    contact_summary,
    fill_property_geo,
    find_property_duplicates,
    get_setting,
    recompute_for_property,
    to_dict,
)
from ..storage import read_bytes

router = APIRouter(prefix="/api/properties", tags=["offres"])

PROPERTY_FIELDS = set(PropertyIn.model_fields)


def demo_filter(model, demo: str):
    if demo == "real":
        return model.is_demo.is_(False)
    if demo == "demo":
        return model.is_demo.is_(True)
    return None


def property_out(db: Session, p: Property, full: bool = False) -> dict:
    d = to_dict(p)
    photo = db.scalar(
        select(Document.id).where(Document.owner_type == "property", Document.owner_id == p.id, Document.kind == "photo").order_by(Document.position, Document.id).limit(1)
    )
    d["cover_photo_id"] = photo
    if full:
        d["owner_contact"] = contact_summary(p.owner_contact)
        d["agency_contact"] = contact_summary(p.agency_contact)
        d["sales_contact"] = contact_summary(p.sales_contact)
        d["documents"] = [
            to_dict(doc)
            for doc in db.scalars(select(Document).where(Document.owner_type == "property", Document.owner_id == p.id).order_by(Document.kind.desc(), Document.position, Document.id))
        ]
    return d


@router.get("")
def list_properties(
    q: str | None = None,
    property_type: str | None = None,
    transaction: str | None = None,
    status: str | None = Query("actives"),
    city: str | None = None,
    department: str | None = None,
    surface_min: float | None = None,
    surface_max: float | None = None,
    price_max: float | None = None,
    rent_max: float | None = None,
    min_height: float | None = None,
    min_docks: int | None = None,
    hgv: bool | None = None,
    geocoded: bool | None = None,
    source_kind: str | None = None,
    demo: str = "all",
    sort: str = "-updated_at",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = []
    if q:
        like = f"%{q.strip()}%"
        conds.append(or_(Property.reference.ilike(like), Property.title.ilike(like), Property.city.ilike(like), Property.address.ilike(like), Property.description.ilike(like), Property.postal_code.ilike(like)))
    if property_type:
        conds.append(Property.property_type.in_(property_type.split(",")))
    if transaction:
        conds.append(or_(Property.transaction == transaction, Property.transaction == "vente_ou_location"))
    if status == "actives":
        conds.append(Property.status.in_(("active", "sous_offre")))
    elif status and status != "toutes":
        conds.append(Property.status == status)
    if city:
        conds.append(Property.city.ilike(f"%{city}%"))
    if department:
        conds.append(Property.department.in_([d.strip().upper().zfill(2) for d in department.split(",")]))
    if surface_min is not None:
        conds.append(Property.surface_total >= surface_min)
    if surface_max is not None:
        conds.append(or_(Property.surface_total <= surface_max, Property.surface_divisible_min <= surface_max))
    if price_max is not None:
        conds.append(Property.sale_price <= price_max)
    if rent_max is not None:
        conds.append(Property.annual_rent <= rent_max)
    if min_height is not None:
        conds.append(Property.clear_height >= min_height)
    if min_docks is not None:
        conds.append(Property.dock_count >= min_docks)
    if hgv is not None:
        conds.append(Property.hgv_access.is_(hgv))
    if geocoded is True:
        conds.append(Property.latitude.is_not(None))
    elif geocoded is False:
        conds.append(Property.latitude.is_(None))
    if source_kind:
        conds.append(Property.source_kind == source_kind)
    f = demo_filter(Property, demo)
    if f is not None:
        conds.append(f)
    sortable = {"updated_at", "created_at", "surface_total", "sale_price", "annual_rent", "city", "reference"}
    key = sort.lstrip("-")
    col = getattr(Property, key if key in sortable else "updated_at")
    order = col.desc() if sort.startswith("-") else col.asc()
    total = db.scalar(select(func.count()).select_from(Property).where(*conds))
    rows = db.scalars(select(Property).where(*conds).order_by(order, Property.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"total": total, "page": page, "page_size": page_size, "items": [property_out(db, p) for p in rows]}


@router.get("/map")
def map_points(demo: str = "all", status: str = "actives", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Points de carte : aucune coordonnée de contact n'est incluse."""
    conds = []
    if status == "actives":
        conds.append(Property.status.in_(("active", "sous_offre")))
    f = demo_filter(Property, demo)
    if f is not None:
        conds.append(f)
    out = {"points": [], "not_geocoded": []}
    for p in db.scalars(select(Property).where(*conds)):
        base = {
            "id": p.id, "reference": p.reference, "title": p.title, "property_type": p.property_type, "transaction": p.transaction,
            "city": p.city, "postal_code": p.postal_code, "surface_total": p.surface_total, "sale_price": p.sale_price,
            "annual_rent": p.annual_rent, "is_demo": p.is_demo,
        }
        if p.latitude is not None and p.longitude is not None:
            out["points"].append(base | {"lat": p.latitude, "lon": p.longitude, "geocode_status": p.geocode_status})
        else:
            out["not_geocoded"].append(base | {"address": p.address})
    return out


@router.post("/check-duplicates")
def check_duplicates(payload: PropertyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return find_property_duplicates(db, payload.model_dump())


@router.post("")
def create_property(payload: PropertyIn, request: Request, force: bool = False, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    data = payload.model_dump(exclude_unset=True)
    if not force:
        dups = find_property_duplicates(db, data)
        if dups:
            raise HTTPException(409, {"message": "Doublon probable détecté.", "duplicates": dups})
    p = Property(created_by=user.id, source_kind=data.pop("source_kind", None) or "manuel")
    for k, v in data.items():
        setattr(p, k, v)
    if not p.status:
        p.status = "active"
    fill_property_geo(p)
    db.add(p)
    db.commit()
    log_action(db, user, "offre_creee", "property", p.id, {"reference": p.reference}, request)
    recompute_for_property(db, p)
    return property_out(db, p, full=True)


@router.get("/{prop_id}")
def get_property(prop_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    d = property_out(db, p, full=True)
    d["duplicates"] = find_property_duplicates(db, to_dict(p), exclude_id=p.id)
    return d


@router.put("/{prop_id}")
def update_property(prop_id: int, payload: PropertyIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    data = payload.model_dump(exclude_unset=True)
    loc_changed = any(k in data and data[k] != getattr(p, k) for k in ("address", "postal_code", "city"))
    coords_given = "latitude" in data or "longitude" in data
    for k, v in data.items():
        setattr(p, k, v)
    if loc_changed and not coords_given:
        p.latitude = p.longitude = None
        p.geocode_status = None
        p.region = None
    elif coords_given and p.latitude is not None:
        p.geocode_status = "manuel"
    fill_property_geo(p)
    db.commit()
    log_action(db, user, "offre_modifiee", "property", p.id, {"champs": sorted(data)}, request)
    recompute_for_property(db, p)
    return property_out(db, p, full=True)


@router.post("/{prop_id}/archive")
def archive_property(prop_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    p.status = "archivee"
    db.commit()
    log_action(db, user, "offre_archivee", "property", p.id, None, request)
    recompute_for_property(db, p)
    return property_out(db, p)


@router.post("/{prop_id}/restore")
def restore_property(prop_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    p.status = "active"
    db.commit()
    log_action(db, user, "offre_restauree", "property", p.id, None, request)
    recompute_for_property(db, p)
    return property_out(db, p)


@router.delete("/{prop_id}")
def delete_property(prop_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    db.delete(p)
    db.commit()
    log_action(db, admin, "offre_supprimee", "property", prop_id, {"reference": p.reference}, request)
    return {"ok": True}


@router.post("/{prop_id}/geocode")
def geocode_property(prop_id: int, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    p.latitude = p.longitude = None
    p.geocode_status = None
    fill_property_geo(p, try_geocode=True)
    db.commit()
    recompute_for_property(db, p)
    if p.geocode_status != "auto":
        raise HTTPException(422, "Géocodage impossible (adresse introuvable ou service indisponible). Saisissez les coordonnées manuellement.")
    return property_out(db, p)


@router.get("/{prop_id}/matches")
def property_matches(prop_id: int, include_eliminated: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Clients adaptés à cette offre (calcul en direct sur toutes les demandes actives)."""
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    weights = get_setting(db, "matching_weights")
    stored = {m.request_id: m for m in db.scalars(select(Match).where(Match.property_id == p.id))}
    out = []
    for r in db.scalars(select(ClientRequest).where(ClientRequest.status == "active", ClientRequest.is_demo == p.is_demo)):
        res = evaluate(r, p, weights)
        if res["eliminated"] and not include_eliminated:
            continue
        m = stored.get(r.id)
        out.append(
            {
                "request": {
                    "id": r.id, "reference": r.reference, "title": r.title, "client_name": r.client_name or (r.company.name if r.company else None),
                    "contact": contact_summary(r.contact), "contact_name": r.contact_name, "email": r.email, "phone": r.phone, "priority": r.priority,
                },
                "match_id": m.id if m else None,
                "status": m.status if m else None,
                **res,
            }
        )
    out.sort(key=lambda x: (x["eliminated"], -x["score"]))
    return out


@router.get("/{prop_id}/pdf")
def property_pdf_route(prop_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Property, prop_id)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    photos = [read_bytes(d.stored_name) for d in db.scalars(select(Document).where(Document.owner_type == "property", Document.owner_id == p.id, Document.kind == "photo", Document.mime_type == "image/jpeg").order_by(Document.position, Document.id).limit(3))]
    pdf = property_pdf(p, photos, get_setting(db, "company_name") or "", {"full_name": user.full_name, "phone": user.phone, "email": user.email})
    log_action(db, user, "fiche_pdf_generee", "property", p.id, None, request)
    name = f"fiche-{(p.reference or p.id)}.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})
