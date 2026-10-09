"""Services métier partagés : paramètres, sérialisation, doublons, recalcul des correspondances."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect, or_, select
from sqlalchemy.orm import Session

from . import geo
from .matching import DEFAULT_WEIGHTS, evaluate
from .models import AppSetting, ClientRequest, Contact, Match, Property, utcnow

DEFAULT_SETTINGS: dict[str, Any] = {
    "matching_weights": DEFAULT_WEIGHTS,
    "matching_min_score": 40,
    "outlook_enabled": False,
    "outlook_agent_url": "http://127.0.0.1:8765",
    "external_freshness_days": 14,
    # Modèles d'URL de recherche saisis et vérifiés par l'utilisateur (vides par défaut :
    # l'application ne fabrique pas d'URL paramétrée non vérifiée).
    "connector_bureauxlocaux_search_template": "",
    "connector_geolocaux_search_template": "",
    "company_name": "",
    "company_signature": "",
    "map_tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "map_attribution": "© contributeurs OpenStreetMap",
    "retention_months_inactive_contacts": 36,
}


def get_setting(db: Session, key: str) -> Any:
    rec = db.get(AppSetting, key)
    return rec.value if rec is not None else DEFAULT_SETTINGS.get(key)


def all_settings(db: Session) -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)
    for rec in db.scalars(select(AppSetting)):
        out[rec.key] = rec.value
    return out


def set_setting(db: Session, key: str, value: Any) -> None:
    rec = db.get(AppSetting, key)
    if rec is None:
        db.add(AppSetting(key=key, value=value))
    else:
        rec.value = value


# ---------------------------------------------------------------------------
# Sérialisation générique
# ---------------------------------------------------------------------------


def to_dict(obj, exclude: set[str] | None = None) -> dict:
    out = {}
    for col in inspect(obj).mapper.column_attrs:
        if exclude and col.key in exclude:
            continue
        v = getattr(obj, col.key)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[col.key] = v
    return out


def contact_summary(c: Contact | None) -> dict | None:
    if c is None:
        return None
    d = to_dict(c, exclude={"notes"})
    d["display_name"] = contact_display_name(c)
    d["company_name"] = c.company.name if c.company else None
    return d


def contact_display_name(c: Contact | None) -> str:
    if c is None:
        return ""
    name = " ".join(x for x in [c.first_name, c.last_name] if x)
    return name or (c.company.name if c.company else "") or (c.email or "")


def apply_fields(obj, data: dict, allowed: set[str]) -> None:
    for k, v in data.items():
        if k in allowed:
            if isinstance(v, str):
                v = v.strip() or None
            setattr(obj, k, v)


# ---------------------------------------------------------------------------
# Offres : champs dérivés et doublons
# ---------------------------------------------------------------------------


def fill_property_geo(prop: Property, try_geocode: bool = True) -> None:
    if prop.postal_code:
        dept = geo.department_from_postal_code(prop.postal_code)
        if dept:
            prop.department = dept
    if prop.department and not prop.region:
        prop.region = geo.region_from_department(prop.department)
    if prop.latitude is not None and prop.longitude is not None:
        if not prop.geocode_status:
            prop.geocode_status = "manuel"
        return
    if try_geocode and (prop.city or prop.postal_code):
        res = geo.geocode(prop.address, prop.postal_code, prop.city)
        if res:
            prop.latitude, prop.longitude = res["latitude"], res["longitude"]
            prop.geocode_status = "auto"
        else:
            prop.geocode_status = "echec"


def find_property_duplicates(db: Session, data: dict, exclude_id: int | None = None) -> list[dict]:
    """Détecte les doublons probables : même URL source, même référence, ou même localisation + surface proche."""
    conds = []
    if data.get("source_url"):
        conds.append(Property.source_url == data["source_url"])
    if data.get("reference"):
        conds.append(Property.reference == data["reference"])
    if data.get("postal_code") and data.get("surface_total"):
        s = float(data["surface_total"])
        conds.append((Property.postal_code == data["postal_code"]) & Property.surface_total.between(s * 0.97, s * 1.03))
    if not conds:
        return []
    q = select(Property).where(or_(*conds))
    if exclude_id:
        q = q.where(Property.id != exclude_id)
    out = []
    addr = geo.normalize(data.get("address"))
    for p in db.scalars(q.limit(20)):
        reasons = []
        if data.get("source_url") and p.source_url == data["source_url"]:
            reasons.append("même URL source")
        if data.get("reference") and p.reference == data["reference"]:
            reasons.append("même référence")
        if data.get("postal_code") and p.postal_code == data.get("postal_code") and p.surface_total and data.get("surface_total"):
            if abs(p.surface_total - float(data["surface_total"])) <= 0.03 * p.surface_total:
                reasons.append("même code postal et surface proche")
                if addr and geo.normalize(p.address) == addr:
                    reasons.append("même adresse")
        out.append({"id": p.id, "reference": p.reference, "title": p.title, "city": p.city, "surface_total": p.surface_total, "source_name": p.source_name, "reasons": reasons})
    return out


def find_request_duplicates(db: Session, data: dict, exclude_id: int | None = None) -> list[dict]:
    conds = []
    if data.get("reference"):
        conds.append(ClientRequest.reference == data["reference"])
    if data.get("email"):
        conds.append(ClientRequest.email == data["email"])
    if not conds:
        return []
    q = select(ClientRequest).where(or_(*conds), ClientRequest.status == "active")
    if exclude_id:
        q = q.where(ClientRequest.id != exclude_id)
    return [{"id": r.id, "reference": r.reference, "title": r.title, "client_name": r.client_name} for r in db.scalars(q.limit(20))]


# ---------------------------------------------------------------------------
# Correspondances
# ---------------------------------------------------------------------------

ACTIVE_PROPERTY_STATUSES = ("active", "sous_offre")


def _store_match(db: Session, req: ClientRequest, prop: Property, weights, threshold: float, existing: Match | None) -> None:
    res = evaluate(req, prop, weights)
    keep = not res["eliminated"] and res["score"] >= threshold
    if existing is None:
        if keep:
            db.add(
                Match(
                    request_id=req.id,
                    property_id=prop.id,
                    score=res["score"],
                    score_potential=res["score_potential"],
                    eliminated=False,
                    details=res,
                )
            )
        return
    # Correspondance déjà suivie commercialement : on la conserve et on met à jour le score
    if keep or existing.status != "a_contacter" or existing.dismissed:
        existing.score = res["score"]
        existing.score_potential = res["score_potential"]
        existing.eliminated = res["eliminated"]
        existing.details = res
        existing.computed_at = utcnow()
    else:
        db.delete(existing)


def recompute_for_request(db: Session, req: ClientRequest) -> None:
    weights = get_setting(db, "matching_weights")
    threshold = float(get_setting(db, "matching_min_score") or 0)
    existing = {m.property_id: m for m in db.scalars(select(Match).where(Match.request_id == req.id))}
    if req.status != "active":
        for m in existing.values():
            if m.status == "a_contacter" and not m.dismissed:
                db.delete(m)
        db.commit()
        return
    props = db.scalars(select(Property).where(Property.status.in_(ACTIVE_PROPERTY_STATUSES), Property.is_demo == req.is_demo))
    seen = set()
    for p in props:
        seen.add(p.id)
        _store_match(db, req, p, weights, threshold, existing.get(p.id))
    for pid, m in existing.items():
        if pid not in seen and m.status == "a_contacter":
            db.delete(m)
    db.commit()


def recompute_for_property(db: Session, prop: Property) -> None:
    weights = get_setting(db, "matching_weights")
    threshold = float(get_setting(db, "matching_min_score") or 0)
    existing = {m.request_id: m for m in db.scalars(select(Match).where(Match.property_id == prop.id))}
    if prop.status not in ACTIVE_PROPERTY_STATUSES:
        for m in existing.values():
            if m.status == "a_contacter" and not m.dismissed:
                db.delete(m)
        db.commit()
        return
    reqs = db.scalars(select(ClientRequest).where(ClientRequest.status == "active", ClientRequest.is_demo == prop.is_demo))
    seen = set()
    for r in reqs:
        seen.add(r.id)
        _store_match(db, r, prop, weights, threshold, existing.get(r.id))
    for rid, m in existing.items():
        if rid not in seen and m.status == "a_contacter":
            db.delete(m)
    db.commit()


def recompute_all(db: Session) -> int:
    n = 0
    for r in db.scalars(select(ClientRequest)).all():
        recompute_for_request(db, r)
        n += 1
    return n
