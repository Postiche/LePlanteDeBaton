"""Paramètres, journal d'audit, exports, sauvegardes et dossiers PDF."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import backup
from ..audit import log_action
from ..config import get_settings
from ..db import get_db
from ..matching import DEFAULT_WEIGHTS, normalize_weights
from ..models import AuditLog, ClientRequest, Company, Contact, Document, Match, Property, User
from ..pdfgen import dossier_pdf
from ..schemas import DossierIn
from ..security import get_current_user, require_admin
from ..services import DEFAULT_SETTINGS, all_settings, get_setting, recompute_all, set_setting, to_dict
from ..storage import read_bytes

router = APIRouter(prefix="/api", tags=["administration"])

PUBLIC_SETTING_KEYS = {"matching_weights", "matching_min_score", "outlook_enabled", "outlook_agent_url", "external_freshness_days", "company_name", "map_tile_url", "map_attribution", "connector_bureauxlocaux_search_template", "connector_geolocaux_search_template", "retention_months_inactive_contacts", "company_signature"}


@router.get("/settings")
def get_settings_route(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = all_settings(db)
    return {k: v for k, v in s.items() if k in PUBLIC_SETTING_KEYS} | {"app_env": get_settings().app_env}


@router.put("/settings")
def update_settings(payload: dict, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    changed = []
    recompute = False
    for k, v in payload.items():
        if k not in PUBLIC_SETTING_KEYS:
            continue
        if k == "matching_weights":
            if not isinstance(v, dict) or set(v) - set(DEFAULT_WEIGHTS):
                raise HTTPException(400, "Pondérations invalides.")
            try:
                v = {kk: float(vv) for kk, vv in v.items()}
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, "Pondérations invalides.") from exc
            if any(x < 0 for x in v.values()) or sum(v.values()) <= 0:
                raise HTTPException(400, "Les pondérations doivent être positives et non toutes nulles.")
            recompute = True
        if k == "matching_min_score":
            v = max(0.0, min(100.0, float(v)))
            recompute = True
        if k == "outlook_agent_url" and v and not str(v).startswith(("http://127.0.0.1", "http://localhost")):
            raise HTTPException(400, "L'agent Outlook doit être local (http://127.0.0.1:port) : il ne doit jamais être exposé sur Internet.")
        if k.startswith("connector_") and v:
            from ..connectors import CONNECTORS

            base = CONNECTORS[k.split("_")[1]].base_url
            if not (v == base or str(v).startswith(base + "/")):
                raise HTTPException(400, f"Le modèle doit commencer par {base}/")
        if k == "map_tile_url" and v and not str(v).startswith("https://"):
            raise HTTPException(400, "L'URL des tuiles doit être en HTTPS.")
        set_setting(db, k, v)
        changed.append(k)
    db.commit()
    log_action(db, admin, "parametres_modifies", "settings", None, {"cles": changed}, request)
    if recompute:
        recompute_all(db)
    return get_settings_route(db, admin) | {"normalized_weights": normalize_weights(get_setting(db, "matching_weights"))}


@router.get("/settings/defaults")
def defaults(user: User = Depends(get_current_user)):
    return {k: v for k, v in DEFAULT_SETTINGS.items() if k in PUBLIC_SETTING_KEYS}


@router.get("/audit")
def audit(limit: int = Query(200, le=1000), action: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    conds = [AuditLog.action == action] if action else []
    return [to_dict(a) for a in db.scalars(select(AuditLog).where(*conds).order_by(AuditLog.at.desc()).limit(limit))]


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

EXPORTS = {
    "offres": (Property, None),
    "demandes": (ClientRequest, None),
    "contacts": (Contact, {"notes"}),
    "entreprises": (Company, None),
    "correspondances": (Match, {"details"}),
}


def _cell(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, dict):
        return str(v)
    return v


@router.get("/exports/{name}.{fmt}")
def export(name: str, fmt: str, request: Request, demo: str = "all", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if name not in EXPORTS or fmt not in ("csv", "xlsx"):
        raise HTTPException(404, "Export inconnu.")
    if user.role == "lecteur" and name in ("contacts",):
        raise HTTPException(403, "Export des contacts réservé aux collaborateurs.")
    model, excl = EXPORTS[name]
    conds = []
    if hasattr(model, "is_demo"):
        if demo == "real":
            conds.append(model.is_demo.is_(False))
        elif demo == "demo":
            conds.append(model.is_demo.is_(True))
    rows = [to_dict(o, exclude=excl) for o in db.scalars(select(model).where(*conds))]
    headers = list(rows[0].keys()) if rows else [c.key for c in model.__table__.columns if not excl or c.key not in excl]
    log_action(db, user, "export", name, None, {"format": fmt, "lignes": len(rows)}, request)
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(headers)
        for r in rows:
            w.writerow([_safe_csv(_cell(r.get(h))) for h in headers])
        data = ("﻿" + buf.getvalue()).encode("utf-8")
        media = "text/csv; charset=utf-8"
    else:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = name[:30]
        ws.append(headers)
        for r in rows:
            ws.append([_safe_csv(_cell(r.get(h))) for h in headers])
        out = io.BytesIO()
        wb.save(out)
        data = out.getvalue()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"', "Cache-Control": "no-store"})


def _safe_csv(v):
    """Neutralise l'injection de formules dans les tableurs."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


# ---------------------------------------------------------------------------
# Sauvegardes
# ---------------------------------------------------------------------------


@router.get("/backups")
def backups(admin: User = Depends(require_admin)):
    return {"backups": backup.list_backups(), "interval_hours": get_settings().backup_interval_hours, "keep": get_settings().backup_keep}


@router.post("/backups")
def make_backup(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    path = backup.create_backup("manuel")
    log_action(db, admin, "sauvegarde_manuelle", None, None, {"fichier": path.name}, request)
    return {"name": path.name}


@router.get("/backups/{name}")
def download_backup(name: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    bdir = Path(get_settings().backup_dir).resolve()
    p = (bdir / Path(name).name).resolve()
    if bdir not in p.parents or not p.exists() or not p.name.startswith("immopro-"):
        raise HTTPException(404, "Sauvegarde introuvable.")
    log_action(db, admin, "sauvegarde_telechargee", None, None, {"fichier": p.name}, request)
    return FileResponse(p, media_type="application/zip", filename=p.name, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Dossier PDF multi-biens
# ---------------------------------------------------------------------------


@router.post("/pdf/dossier")
def dossier(payload: DossierIn, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = []
    for pid in payload.property_ids:
        p = db.get(Property, pid)
        if p is None:
            continue
        photos = [read_bytes(d.stored_name) for d in db.scalars(select(Document).where(Document.owner_type == "property", Document.owner_id == p.id, Document.kind == "photo", Document.mime_type == "image/jpeg").order_by(Document.position).limit(3))]
        items.append((p, photos))
    if not items:
        raise HTTPException(400, "Aucun bien valide sélectionné.")
    label = payload.client_label
    if not label and payload.request_id:
        r = db.get(ClientRequest, payload.request_id)
        label = (r.client_name or (r.company.name if r and r.company else None) or r.title) if r else None
    pdf = dossier_pdf(items, label or "notre client", get_setting(db, "company_name") or "", {"full_name": user.full_name, "phone": user.phone, "email": user.email}, payload.intro)
    log_action(db, user, "dossier_pdf_genere", "request", payload.request_id, {"biens": [p.id for p, _ in items]}, request)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="dossier-biens.pdf"', "Cache-Control": "no-store"})
