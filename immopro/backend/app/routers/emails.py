from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..db import get_db
from ..emails import TEMPLATES, build_email, build_eml
from ..matching import evaluate
from ..models import ClientRequest, Contact, Document, EmailDraft, Interaction, Match, Property, User, Visit, utcnow
from ..pdfgen import property_pdf
from ..schemas import ComposeIn, DraftIn, DraftStatusIn, EmlIn
from ..security import get_current_user, require_writer
from ..services import contact_display_name, get_setting, to_dict
from ..storage import read_bytes

router = APIRouter(prefix="/api/emails", tags=["emails"])

STATUS_LABELS = {
    "brouillon": "Brouillon enregistré",
    "ouvert_messagerie": "Ouvert dans la messagerie (non envoyé)",
    "brouillon_outlook": "Brouillon Outlook créé (non envoyé)",
    "eml_telecharge": "Fichier .eml téléchargé (non envoyé)",
    "envoye_confirme": "Envoi confirmé par l'utilisateur",
}


@router.get("/templates")
def templates(user: User = Depends(get_current_user)):
    return [{"key": k, "label": v} for k, v in TEMPLATES.items()]


@router.post("/compose")
def compose(payload: ComposeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.template not in TEMPLATES:
        raise HTTPException(400, "Modèle inconnu.")
    warnings: list[str] = []
    contact = db.get(Contact, payload.contact_id) if payload.contact_id else None
    req = db.get(ClientRequest, payload.request_id) if payload.request_id else None
    match = db.get(Match, payload.match_id) if payload.match_id else None
    if match:
        req = req or match.request
        if match.property_id not in payload.property_ids:
            payload.property_ids.insert(0, match.property_id)
    if req and not contact and req.contact_id:
        contact = req.contact
    props = [p for p in (db.get(Property, i) for i in payload.property_ids) if p is not None]
    slots = list(payload.slots)
    if payload.visit_id:
        v = db.get(Visit, payload.visit_id)
        if v:
            slots = slots or list(v.proposed_slots or [])
            if v.property_id not in [p.id for p in props]:
                props.insert(0, v.property)
            contact = contact or v.contact
    fits = {}
    if req:
        weights = get_setting(db, "matching_weights")
        for p in props:
            fits[p.id] = evaluate(req, p, weights)["satisfied"]
    to = payload.to_email or (contact.email if contact else None) or (req.email if req else None)
    recipient = payload.recipient_name or (req.contact_name if req and not contact else None)
    if not to:
        warnings.append("Aucune adresse email connue pour ce destinataire : complétez le champ « À ».")
    if contact and contact.opposed_to_prospecting:
        warnings.append("Ce contact s'est opposé à la prospection commerciale : n'envoyez ce message que s'il répond à une demande de sa part.")
    if req and payload.template in ("presentation_bien", "selection_biens") and not props:
        warnings.append("Aucun bien sélectionné.")
    signature = user.email_signature or "\n".join(x for x in [user.full_name, get_setting(db, "company_name"), user.phone, user.email] if x)
    out = build_email(
        payload.template,
        contact=contact,
        recipient_name=recipient,
        properties=props,
        fits=fits,
        slots=slots,
        request_label=(req.title or req.reference) if req else None,
        sender_name=user.full_name,
        signature=signature,
        listing_url=payload.listing_url or (props[0].source_url if props and props[0].source_kind == "externe" else None),
        notes=payload.notes,
    )
    return out | {
        "to_email": to,
        "contact_id": contact.id if contact else None,
        "recipient_label": contact_display_name(contact) if contact else recipient,
        "request_id": req.id if req else None,
        "property_ids": [p.id for p in props],
        "match_id": match.id if match else None,
        "visit_id": payload.visit_id,
        "warnings": warnings,
    }


@router.get("/drafts")
def list_drafts(contact_id: int | None = None, request_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = []
    if contact_id:
        conds.append(EmailDraft.contact_id == contact_id)
    if request_id:
        conds.append(EmailDraft.request_id == request_id)
    return [to_dict(d) | {"status_label": STATUS_LABELS.get(d.status, d.status)} for d in db.scalars(select(EmailDraft).where(*conds).order_by(EmailDraft.updated_at.desc()).limit(200))]


@router.post("/drafts")
def save_draft(payload: DraftIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    d = EmailDraft(**payload.model_dump(), status="brouillon", user_id=user.id)
    db.add(d)
    if d.match_id:
        m = db.get(Match, d.match_id)
        if m and m.status == "a_contacter":
            m.status = "email_prepare"
            m.status_updated_at = utcnow()
    db.flush()
    db.add(Interaction(kind="email_prepare", subject=d.subject, contact_id=d.contact_id, request_id=d.request_id, match_id=d.match_id, property_id=(d.property_ids or [None])[0], user_id=user.id))
    db.commit()
    log_action(db, user, "email_prepare", "email", d.id, None, request)
    return to_dict(d) | {"status_label": STATUS_LABELS[d.status]}


@router.put("/drafts/{did}")
def update_draft(did: int, payload: DraftIn, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    d = db.get(EmailDraft, did)
    if d is None:
        raise HTTPException(404, "Brouillon introuvable.")
    if d.status == "envoye_confirme":
        raise HTTPException(400, "Cet email a été marqué comme envoyé : il n'est plus modifiable.")
    for k, v in payload.model_dump().items():
        setattr(d, k, v)
    db.commit()
    return to_dict(d) | {"status_label": STATUS_LABELS.get(d.status)}


@router.post("/drafts/{did}/status")
def draft_status(did: int, payload: DraftStatusIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Ouvrir via mailto, créer un brouillon Outlook ou télécharger un .eml NE vaut PAS envoi.
    Le statut « envoyé » n'est enregistré que sur confirmation explicite de l'utilisateur."""
    d = db.get(EmailDraft, did)
    if d is None:
        raise HTTPException(404, "Brouillon introuvable.")
    if payload.status not in STATUS_LABELS:
        raise HTTPException(400, "Statut inconnu.")
    if payload.status == "envoye_confirme":
        if not payload.confirm_sent:
            raise HTTPException(400, "Confirmez explicitement que vous avez envoyé ce message depuis votre messagerie.")
        d.sent_confirmed_at = utcnow()
        db.add(Interaction(kind="email_envoye", subject=d.subject, content=d.body[:2000], contact_id=d.contact_id, request_id=d.request_id, match_id=d.match_id, property_id=(d.property_ids or [None])[0], user_id=user.id))
        if d.match_id:
            m = db.get(Match, d.match_id)
            if m and m.status in ("a_contacter", "email_prepare"):
                m.status = "visite_proposee" if d.template == "proposition_visite" else "contacte"
                m.status_updated_at = utcnow()
    elif d.status == "envoye_confirme":
        raise HTTPException(400, "Email déjà marqué comme envoyé.")
    d.status = payload.status
    db.commit()
    log_action(db, user, "email_statut", "email", d.id, {"status": d.status}, request)
    return to_dict(d) | {"status_label": STATUS_LABELS[d.status]}


@router.post("/eml")
def download_eml(payload: EmlIn, request: Request, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Fichier .eml non envoyé, avec fiches PDF en pièces jointes : alternative universelle à Outlook."""
    attachments = []
    company = get_setting(db, "company_name") or ""
    for pid in payload.attach_property_ids:
        p = db.get(Property, pid)
        if p is None:
            continue
        photos = [read_bytes(doc.stored_name) for doc in db.scalars(select(Document).where(Document.owner_type == "property", Document.owner_id == p.id, Document.kind == "photo", Document.mime_type == "image/jpeg").limit(3))]
        pdf = property_pdf(p, photos, company, {"full_name": user.full_name, "phone": user.phone, "email": user.email})
        attachments.append((f"fiche-{p.reference or p.id}.pdf".replace("/", "-"), pdf, "application/pdf"))
    data = build_eml(payload.to_email, payload.cc, payload.subject, payload.body, user.email, attachments)
    if payload.draft_id:
        d = db.get(EmailDraft, payload.draft_id)
        if d and d.status != "envoye_confirme":
            d.status = "eml_telecharge"
            db.commit()
    log_action(db, user, "eml_genere", "email", payload.draft_id, None, request)
    return Response(data, media_type="message/rfc822", headers={"Content-Disposition": 'attachment; filename="brouillon.eml"', "Cache-Control": "no-store"})


@router.get("/attachments/{pid}")
def attachment_base64(pid: int, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    """Fiche PDF encodée en base64, transmise par le navigateur à l'agent Outlook local."""
    import base64

    p = db.get(Property, pid)
    if p is None:
        raise HTTPException(404, "Offre introuvable.")
    photos = [read_bytes(doc.stored_name) for doc in db.scalars(select(Document).where(Document.owner_type == "property", Document.owner_id == p.id, Document.kind == "photo", Document.mime_type == "image/jpeg").limit(3))]
    pdf = property_pdf(p, photos, get_setting(db, "company_name") or "", {"full_name": user.full_name, "phone": user.phone, "email": user.email})
    return {"filename": f"fiche-{p.reference or p.id}.pdf".replace("/", "-"), "content_base64": base64.b64encode(pdf).decode()}
