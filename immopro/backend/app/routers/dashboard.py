from __future__ import annotations

from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..matching import TYPE_LABELS
from ..models import PIPELINE_LABELS, PIPELINE_STATUSES, AuditLog, ClientRequest, Interaction, Match, Property, User, Visit, utcnow
from ..security import get_current_user
from .crm import interaction_out

router = APIRouter(prefix="/api/dashboard", tags=["tableau de bord"])


@router.get("")
def dashboard(days: int = Query(30, ge=1, le=365), demo: str = "all", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    since = utcnow() - timedelta(days=days)

    def dflt(model):
        if demo == "real":
            return [model.is_demo.is_(False)]
        if demo == "demo":
            return [model.is_demo.is_(True)]
        return []

    def count(model, *conds):
        return db.scalar(select(func.count()).select_from(model).where(*conds, *dflt(model))) or 0

    active_props = (Property.status.in_(("active", "sous_offre")),)
    match_q = select(Match).join(Property, Match.property_id == Property.id).where(Match.eliminated.is_(False), Match.dismissed.is_(False), *dflt(Property))
    matches = list(db.scalars(match_q))
    by_status = Counter(m.status for m in matches)

    props = list(db.scalars(select(Property).where(*active_props, *dflt(Property))))
    by_type = Counter(p.property_type or "non_renseigne" for p in props)
    by_trans = Counter(p.transaction or "non_renseigne" for p in props)

    # Nouveaux biens par semaine sur la période
    weeks: dict[str, int] = {}
    start = since - timedelta(days=since.weekday())
    cur = start
    while cur <= utcnow():
        weeks[cur.strftime("%Y-%m-%d")] = 0
        cur += timedelta(days=7)
    for (created,) in db.execute(select(Property.created_at).where(Property.created_at >= since, *dflt(Property))):
        wk = (created - timedelta(days=created.weekday())).strftime("%Y-%m-%d")
        if wk in weeks:
            weeks[wk] += 1

    reminders = list(
        db.scalars(
            select(Interaction).where(Interaction.remind_at.is_not(None), Interaction.done.is_(False), Interaction.remind_at <= utcnow() + timedelta(days=1)).order_by(Interaction.remind_at).limit(20)
        )
    )
    recent = list(db.scalars(select(Interaction).order_by(Interaction.at.desc()).limit(15)))
    top = sorted((m for m in matches if m.status == "a_contacter"), key=lambda m: -m.score)[:8]

    return {
        "period_days": days,
        "kpis": {
            "offres": count(Property, *active_props),
            "demandes": count(ClientRequest),
            "nouveaux_biens": count(Property, Property.created_at >= since),
            "demandes_actives": count(ClientRequest, ClientRequest.status == "active"),
            "correspondances": len(matches),
            "visites_proposees": count(Visit, Visit.status == "proposee"),
            "visites_confirmees": count(Visit, Visit.status == "confirmee"),
            "relances": len(reminders),
        },
        "matches_by_status": [{"key": s, "label": PIPELINE_LABELS[s], "count": by_status.get(s, 0)} for s in PIPELINE_STATUSES],
        "properties_by_type": [{"key": k, "label": TYPE_LABELS.get(k, "Non renseigné"), "count": v} for k, v in by_type.most_common()],
        "properties_by_transaction": [{"key": k, "label": {"vente": "Vente", "location": "Location", "vente_ou_location": "Vente ou location"}.get(k, "Non renseigné"), "count": v} for k, v in by_trans.most_common()],
        "new_properties_by_week": [{"week": k, "count": v} for k, v in weeks.items()],
        "reminders": [interaction_out(db, i) for i in reminders],
        "recent_activity": [interaction_out(db, i) for i in recent],
        "top_matches": [
            {"id": m.id, "score": m.score, "property": {"id": m.property.id, "reference": m.property.reference, "title": m.property.title, "city": m.property.city}, "request": {"id": m.request.id, "title": m.request.title, "client_name": m.request.client_name}}
            for m in top
        ],
        "last_logins": [
            {"at": a.at.isoformat(), "username": a.username} for a in db.scalars(select(AuditLog).where(AuditLog.action == "connexion").order_by(AuditLog.at.desc()).limit(5))
        ] if user.role == "admin" else [],
    }
