"""Imports de fichiers avec étape obligatoire de vérification humaine."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..importers import extract
from ..models import ClientRequest, Contact, Document, ImportBatch, Property, User, utcnow
from ..schemas import PropertyIn, RequestIn
from ..security import get_current_user, require_writer
from ..services import fill_property_geo, find_property_duplicates, find_request_duplicates, recompute_for_property, recompute_for_request, to_dict
from ..storage import read_bytes, save_upload

router = APIRouter(prefix="/api/imports", tags=["imports"])

CONTACT_FIELDS = {"owner_name", "agency_name", "sales_name", "contact_email", "contact_phone"}


def batch_out(b: ImportBatch) -> dict:
    return to_dict(b)


@router.get("")
def list_batches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        {k: v for k, v in batch_out(b).items() if k != "rows"} | {"row_count": len(b.rows or [])}
        for b in db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(100))
    ]


@router.post("")
async def create_batch(request: Request, target: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_writer)):
    if target not in ("property", "request"):
        raise HTTPException(400, "Cible invalide.")
    stored = await save_upload(file, allowed_ext={".xlsx", ".csv", ".pdf", ".docx", ".txt"})
    doc = Document(owner_type="import", owner_id=None, kind="document", original_name=stored.original_name, stored_name=stored.stored_name, mime_type=stored.mime_type, size=stored.size, sha256=stored.sha256, uploaded_by=user.id)
    db.add(doc)
    db.flush()
    kind = stored.ext.lstrip(".")
    try:
        rows, warnings = extract(kind, read_bytes(stored.stored_name), target)
    except Exception as exc:  # fichier mal formé
        rows, warnings = [], [f"Lecture impossible : {exc}"]
    if len(rows) > 2000:
        warnings.append("Seules les 2000 premières lignes ont été retenues.")
        rows = rows[:2000]
    for row in rows:
        data = row["data"]
        row["duplicates"] = find_property_duplicates(db, data) if target == "property" else find_request_duplicates(db, data)
        row["action"] = "ignorer" if row["duplicates"] else "creer"
        if not data:
            row["action"] = "ignorer"
            row["warnings"].append("Aucune donnée reconnue sur cette ligne.")
    b = ImportBatch(target=target, source_name=stored.original_name, file_kind=kind, document_id=doc.id, rows=rows, warnings=warnings, created_by=user.id)
    db.add(b)
    db.commit()
    doc.owner_id = b.id
    db.commit()
    log_action(db, user, "import_analyse", "import", b.id, {"fichier": stored.original_name, "lignes": len(rows)}, request)
    return batch_out(b)


@router.get("/{bid}")
def get_batch(bid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.get(ImportBatch, bid)
    if b is None:
        raise HTTPException(404, "Import introuvable.")
    return batch_out(b)


@router.put("/{bid}/rows")
def update_rows(bid: int, rows: list[dict], db: Session = Depends(get_db), user: User = Depends(require_writer)):
    b = db.get(ImportBatch, bid)
    if b is None or b.status != "a_valider":
        raise HTTPException(400, "Import non modifiable.")
    b.rows = rows
    db.commit()
    return batch_out(b)


def _contact_for(db: Session, kind: str, name: str | None, email: str | None, phone: str | None, origin: str) -> int | None:
    if not (name or email):
        return None
    if email:
        c = db.scalar(select(Contact).where(Contact.email == email))
        if c:
            return c.id
    parts = (name or "").split()
    c = Contact(kind=kind, last_name=parts[-1] if parts else None, first_name=" ".join(parts[:-1]) or None, email=email, phone=phone, origin=origin, legal_basis="interet_legitime")
    db.add(c)
    db.flush()
    return c.id


@router.post("/{bid}/commit")
def commit_batch(bid: int, request: Request, rows: list[dict] | None = None, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Enregistre les lignes validées par l'utilisateur (action « creer » ou « fusionner »)."""
    b = db.get(ImportBatch, bid)
    if b is None or b.status != "a_valider":
        raise HTTPException(400, "Import déjà traité ou introuvable.")
    if rows is not None:
        b.rows = rows
    created, merged, errors = [], [], []
    origin = f"Import « {b.source_name} » du {utcnow():%d/%m/%Y}"
    for row in b.rows or []:
        action = row.get("action")
        if action not in ("creer", "fusionner"):
            continue
        data = dict(row.get("data") or {})
        contacts = {k: data.pop(k, None) for k in CONTACT_FIELDS}
        try:
            schema = PropertyIn if b.target == "property" else RequestIn
            clean = schema.model_validate(data).model_dump(exclude_unset=True)
        except ValidationError as exc:
            errors.append({"row_number": row.get("row_number"), "error": "; ".join(e["msg"] for e in exc.errors())})
            continue
        if b.target == "property":
            if action == "fusionner" and row.get("merge_into"):
                p = db.get(Property, int(row["merge_into"]))
                if p is None:
                    errors.append({"row_number": row.get("row_number"), "error": "Offre cible introuvable."})
                    continue
                # Fusion prudente : on ne complète que les champs vides de la fiche existante
                for k, v in clean.items():
                    if getattr(p, k, None) in (None, "") and v not in (None, ""):
                        setattr(p, k, v)
                merged.append(p.id)
            else:
                p = Property(**clean, source_kind="import", created_by=user.id)
                p.source_name = p.source_name or b.source_name
                p.status = p.status or "active"
                if contacts.get("owner_name"):
                    p.owner_contact_id = _contact_for(db, "proprietaire", contacts["owner_name"], None, None, origin)
                if contacts.get("agency_name") or contacts.get("contact_email"):
                    p.agency_contact_id = _contact_for(db, "agence", contacts.get("agency_name"), contacts.get("contact_email"), contacts.get("contact_phone"), origin)
                if contacts.get("sales_name"):
                    p.sales_contact_id = _contact_for(db, "commercial", contacts["sales_name"], None, None, origin)
                db.add(p)
                created.append(p)
            fill_property_geo(p)
        else:
            r = ClientRequest(**clean, source_kind="import", source_name=b.source_name, created_by=user.id)
            r.status = r.status or "active"
            r.priority = r.priority or "normale"
            db.add(r)
            created.append(r)
    b.status = "valide"
    b.validated_at = utcnow()
    db.commit()
    for obj in created:
        if isinstance(obj, Property):
            recompute_for_property(db, obj)
        else:
            recompute_for_request(db, obj)
    for pid in merged:
        recompute_for_property(db, db.get(Property, pid))
    log_action(db, user, "import_valide", "import", b.id, {"crees": len(created), "fusionnes": len(merged), "erreurs": len(errors)}, request)
    return {"created": [o.id for o in created], "merged": merged, "errors": errors}


@router.post("/{bid}/cancel")
def cancel_batch(bid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    b = db.get(ImportBatch, bid)
    if b is None:
        raise HTTPException(404, "Import introuvable.")
    b.status = "annule"
    db.commit()
    log_action(db, user, "import_annule", "import", b.id, None, request)
    return {"ok": True}


__all__ = ["router", "Path"]
