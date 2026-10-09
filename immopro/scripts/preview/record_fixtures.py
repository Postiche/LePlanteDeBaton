"""Enregistre les réponses de l'API sur une base de démonstration FICTIVE pour l'aperçu HTML autonome.

Usage (depuis immopro/backend, environnement Python du projet) :
    python ../scripts/preview/record_fixtures.py ../frontend/src/preview/fixtures.json
"""
import json
import os
import sys
import tempfile
from pathlib import Path

out = Path(sys.argv[1]).resolve()
tmp = Path(tempfile.mkdtemp(prefix="immopro-preview-"))
os.environ.update({
    "APP_ENV": "test", "DATABASE_URL": f"sqlite:///{(tmp / 'p.db').as_posix()}", "COOKIE_SECURE": "false",
    "UPLOAD_DIR": str(tmp / "up"), "BACKUP_DIR": str(tmp / "bk"), "GEOCODER_ENABLED": "false",
    "SECRET_KEY": "preview-only-preview-only-preview-only-0000", "FRONTEND_DIST": str(tmp / "nodist"),
})
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, get_engine  # noqa: E402
from app.demo import seed_demo  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import set_setting  # noqa: E402

PWD = "Apercu-Demo-2026!"
Base.metadata.create_all(get_engine())
with SessionLocal() as db:
    db.add(User(username="demo", full_name="Utilisateur Démo", role="admin", email="vous@exemple.test", phone="01 00 00 00 09", password_hash=hash_password(PWD)))
    set_setting(db, "company_name", "Votre société (démo)")
    db.commit()
    seed_demo(db)

from app.main import create_app  # noqa: E402

c = TestClient(create_app())
c.post("/api/auth/login", json={"username": "demo", "password": PWD})
c.headers["X-CSRF-Token"] = c.get("/api/auth/me").json()["csrf_token"]
G = lambda p, **params: c.get(p, params=params).json()  # noqa: E731

R = {}
for p in ["/api/auth/me", "/api/settings", "/api/dashboard", "/api/properties/map", "/api/emails/templates", "/api/emails/drafts",
          "/api/external/listings", "/api/external/connectors", "/api/imports", "/api/users", "/api/users/directory", "/api/backups", "/api/audit"]:
    R[p] = G(p)
R["/api/auth/me"]["csrf_token"] = "apercu"
R["/api/properties"] = G("/api/properties", status="toutes", page_size=500)
R["/api/requests"] = G("/api/requests", status="toutes", page_size=500)
R["/api/matches"] = G("/api/matches", page_size=500)
R["/api/contacts"] = G("/api/contacts")
R["/api/companies"] = G("/api/companies")
R["/api/visits"] = G("/api/visits")
R["/api/interactions?reminders"] = G("/api/interactions", reminders=True)
props = [p["id"] for p in R["/api/properties"]["items"]]
reqs = [r["id"] for r in R["/api/requests"]["items"]]
for pid in props:
    R[f"/api/properties/{pid}"] = G(f"/api/properties/{pid}")
    R[f"/api/properties/{pid}/matches"] = G(f"/api/properties/{pid}/matches")
    R[f"/api/properties/{pid}/matches#elim"] = G(f"/api/properties/{pid}/matches", include_eliminated=True)
    R[f"/api/timeline?property_id={pid}"] = G("/api/timeline", property_id=pid)
for rid in reqs:
    R[f"/api/requests/{rid}"] = G(f"/api/requests/{rid}")
    R[f"/api/requests/{rid}/matches"] = G(f"/api/requests/{rid}/matches")
    R[f"/api/requests/{rid}/matches#elim"] = G(f"/api/requests/{rid}/matches", include_eliminated=True)
    R[f"/api/timeline?request_id={rid}"] = G("/api/timeline", request_id=rid)
    R[f"POST /api/external/search/{rid}"] = c.post(f"/api/external/search/{rid}").json()
for ct in R["/api/contacts"]:
    R[f"/api/contacts/{ct['id']}"] = G(f"/api/contacts/{ct['id']}")
    R[f"/api/contacts/{ct['id']}/timeline"] = G(f"/api/contacts/{ct['id']}/timeline")
for co in R["/api/companies"]:
    R[f"/api/companies/{co['id']}"] = G(f"/api/companies/{co['id']}")
for m in R["/api/matches"]["items"]:
    R[f"/api/matches/{m['id']}"] = m

# Emails préremplis : chaque modèle pour chaque couple (demande, bien), pour chaque bien seul, chaque contact seul
templates = [t["key"] for t in R["/api/emails/templates"]]
compose = {}
def rec(body):
    key = "|".join([body["template"], ",".join(map(str, body.get("property_ids", []))), str(body.get("request_id") or ""), str(body.get("contact_id") or "")])
    compose[key] = c.post("/api/emails/compose", json=body).json()
for t in templates:
    rec({"template": t})
    for pid in props:
        rec({"template": t, "property_ids": [pid]})
        for rid in reqs:
            rec({"template": t, "property_ids": [pid], "request_id": rid})
    for rid in reqs:
        rec({"template": t, "request_id": rid})
        ids = [m["property"]["id"] for m in R[f"/api/requests/{rid}/matches"]][:3]
        if ids:
            rec({"template": t, "property_ids": ids, "request_id": rid})
    for ct in R["/api/contacts"]:
        rec({"template": t, "contact_id": ct["id"]})
match_index = {m["id"]: [m["request"]["id"], m["property"]["id"]] for m in R["/api/matches"]["items"]}
out.write_text(json.dumps({"routes": R, "compose": compose, "match_index": match_index}, ensure_ascii=False), encoding="utf-8")
print(f"{len(R)} réponses, {len(compose)} emails → {out} ({out.stat().st_size // 1024} Ko)")
