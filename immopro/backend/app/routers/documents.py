from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..models import ClientRequest, Company, Contact, Document, Property, User, Visit
from ..security import get_current_user, require_writer
from ..services import to_dict
from ..storage import file_path, save_upload

router = APIRouter(prefix="/api", tags=["documents"])

OWNERS = {"property": Property, "request": ClientRequest, "contact": Contact, "company": Company, "visit": Visit}


@router.get("/documents")
def list_documents(owner_type: str, owner_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [to_dict(d) for d in db.scalars(select(Document).where(Document.owner_type == owner_type, Document.owner_id == owner_id).order_by(Document.kind.desc(), Document.position, Document.id))]


@router.post("/documents")
async def upload_document(
    request: Request,
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    caption: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_writer),
):
    model = OWNERS.get(owner_type)
    if model is None:
        raise HTTPException(400, "Type de rattachement invalide.")
    owner = db.get(model, owner_id)
    if owner is None:
        raise HTTPException(404, "Élément de rattachement introuvable.")
    stored = await save_upload(file)
    pos = db.scalar(select(func.coalesce(func.max(Document.position), 0)).where(Document.owner_type == owner_type, Document.owner_id == owner_id)) or 0
    d = Document(
        owner_type=owner_type,
        owner_id=owner_id,
        kind=stored.kind,
        original_name=stored.original_name,
        stored_name=stored.stored_name,
        mime_type=stored.mime_type,
        size=stored.size,
        sha256=stored.sha256,
        caption=caption,
        position=pos + 1,
        uploaded_by=user.id,
        is_demo=getattr(owner, "is_demo", False),
    )
    db.add(d)
    db.commit()
    log_action(db, user, "document_ajoute", owner_type, owner_id, {"document": d.id, "nom": d.original_name}, request)
    return to_dict(d)


@router.patch("/documents/{doc_id}")
def update_document(doc_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Document introuvable.")
    if "caption" in payload:
        d.caption = (payload["caption"] or "")[:200] or None
    if "position" in payload:
        d.position = int(payload["position"])
    db.commit()
    return to_dict(d)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Document introuvable.")
    path = file_path(d.stored_name)
    db.delete(d)
    db.commit()
    if path.exists():
        path.unlink()
    log_action(db, user, "document_supprime", d.owner_type, d.owner_id, {"nom": d.original_name}, request)
    return {"ok": True}


@router.get("/files/{doc_id}")
def download_file(doc_id: int, download: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Téléchargement authentifié uniquement. Les images s'affichent en ligne, le reste en pièce jointe."""
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Fichier introuvable.")
    path = file_path(d.stored_name)
    if not path.exists():
        raise HTTPException(404, "Fichier introuvable sur le disque.")
    inline = d.mime_type in ("image/jpeg", "image/png", "image/webp", "application/pdf") and not download
    return FileResponse(
        path,
        media_type=d.mime_type,
        filename=d.original_name,
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"},
    )
