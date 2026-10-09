import io

from PIL import Image

PROP = {
    "reference": "R-100", "title": "Entrepôt test", "property_type": "entrepot", "transaction": "location",
    "city": "Saint-Priest", "postal_code": "69800", "latitude": 45.69, "longitude": 4.94,
    "surface_total": 6000, "annual_rent": 360000, "clear_height": 10, "dock_count": 6, "hgv_access": True,
}
REQ = {
    "title": "Recherche Lyon", "client_name": "Client Test", "email": "client@exemple.test",
    "property_types": ["entrepot"], "transaction": "location", "departments": ["69"],
    "surface_min": 5000, "surface_max": 8000, "budget_max": 400000, "min_clear_height": 9, "imperatives": ["transaction"],
}


def test_full_matching_flow(auth_client):
    c = auth_client
    p = c.post("/api/properties", json=PROP).json()
    assert p["department"] == "69" and p["region"] == "Auvergne-Rhône-Alpes"
    r = c.post("/api/requests", json=REQ).json()
    assert r["match_count"] == 1
    live = c.get(f"/api/requests/{r['id']}/matches").json()
    assert live[0]["score"] == 100 and live[0]["property"]["id"] == p["id"]
    clients = c.get(f"/api/properties/{p['id']}/matches").json()
    assert clients[0]["request"]["id"] == r["id"]
    # Modification -> recalcul automatique
    c.put(f"/api/properties/{p['id']}", json={"transaction": "vente"})
    assert c.get(f"/api/requests/{r['id']}").json()["match_count"] == 0  # impératif transaction non satisfait
    assert c.get(f"/api/requests/{r['id']}/matches", params={"include_eliminated": True}).json()[0]["eliminated"] is True
    c.put(f"/api/properties/{p['id']}", json={"transaction": "location"})
    matches = c.get("/api/matches").json()
    assert matches["total"] == 1
    mid = matches["items"][0]["id"]
    # Archivage -> la correspondance non suivie disparaît
    c.post(f"/api/properties/{p['id']}/archive")
    assert c.get("/api/matches").json()["total"] == 0
    c.post(f"/api/properties/{p['id']}/restore")
    mid = c.get("/api/matches").json()["items"][0]["id"]
    assert c.patch(f"/api/matches/{mid}", json={"status": "contacte", "note": "Appel"}).json()["status"] == "contacte"
    tl = c.get("/api/timeline", params={"request_id": r["id"]}).json()
    assert any(i["kind"] == "statut" for i in tl)


def test_duplicate_detection(auth_client):
    auth_client.post("/api/properties", json=PROP)
    r = auth_client.post("/api/properties", json=PROP | {"reference": "AUTRE", "surface_total": 6050})
    assert r.status_code == 409
    assert r.json()["detail"]["duplicates"]
    assert auth_client.post("/api/properties?force=true", json=PROP | {"reference": "AUTRE"}).status_code == 200


def test_email_never_marked_sent_without_confirmation(auth_client):
    c = auth_client
    p = c.post("/api/properties", json=PROP).json()
    r = c.post("/api/requests", json=REQ).json()
    mid = c.get("/api/matches").json()["items"][0]["id"]
    comp = c.post("/api/emails/compose", json={"template": "presentation_bien", "match_id": mid}).json()
    assert comp["to_email"] == "client@exemple.test"
    assert "R-100" in comp["subject"] and "Surface : 6\u202f000 m²" in comp["body"]
    assert "Prix de vente" not in comp["body"]  # aucune donnée absente n'est inventée
    d = c.post("/api/emails/drafts", json={"template": "presentation_bien", "to_email": comp["to_email"], "subject": comp["subject"], "body": comp["body"], "match_id": mid, "request_id": r["id"], "property_ids": [p["id"]]}).json()
    assert c.get(f"/api/matches/{mid}").json()["status"] == "email_prepare"
    assert c.post(f"/api/emails/drafts/{d['id']}/status", json={"status": "ouvert_messagerie"}).json()["status"] == "ouvert_messagerie"
    assert c.get(f"/api/matches/{mid}").json()["status"] == "email_prepare"  # mailto != envoyé
    assert c.post(f"/api/emails/drafts/{d['id']}/status", json={"status": "envoye_confirme"}).status_code == 400
    assert c.post(f"/api/emails/drafts/{d['id']}/status", json={"status": "envoye_confirme", "confirm_sent": True}).status_code == 200
    assert c.get(f"/api/matches/{mid}").json()["status"] == "contacte"
    eml = c.post("/api/emails/eml", json={"to_email": "a@exemple.test", "subject": "S", "body": "B", "attach_property_ids": [p["id"]]})
    assert eml.status_code == 200 and b"X-Unsent: 1" in eml.content and b"application/pdf" in eml.content


def test_all_templates_compose(auth_client):
    p = auth_client.post("/api/properties", json=PROP).json()
    for t in auth_client.get("/api/emails/templates").json():
        res = auth_client.post("/api/emails/compose", json={"template": t["key"], "property_ids": [p["id"]], "slots": ["2030-01-15T10:00:00"]})
        assert res.status_code == 200, t
        assert res.json()["subject"]


def test_visit_confirmation_requires_explicit_slot(auth_client):
    c = auth_client
    p = c.post("/api/properties", json=PROP).json()
    v = c.post("/api/visits", json={"property_id": p["id"], "proposed_slots": ["2030-01-15T10:00:00", "2030-01-16T14:00:00"]}).json()
    assert v["status"] == "proposee"
    assert c.patch(f"/api/visits/{v['id']}", json={"status": "confirmee"}).status_code == 400
    ok = c.patch(f"/api/visits/{v['id']}", json={"status": "confirmee", "confirmed_slot": "2030-01-16T14:00:00"})
    assert ok.status_code == 200 and ok.json()["status"] == "confirmee"


def test_pdf_and_dossier(auth_client):
    c = auth_client
    p = c.post("/api/properties", json=PROP).json()
    img = io.BytesIO()
    Image.new("RGB", (800, 500), (20, 60, 120)).save(img, "JPEG")
    up = c.post("/api/documents", data={"owner_type": "property", "owner_id": str(p["id"])}, files={"file": ("photo.jpg", img.getvalue(), "image/jpeg")})
    assert up.status_code == 200 and up.json()["kind"] == "photo"
    pdf = c.get(f"/api/properties/{p['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    dos = c.post("/api/pdf/dossier", json={"property_ids": [p["id"]], "client_label": "Client"})
    assert dos.status_code == 200 and dos.content.startswith(b"%PDF")


def test_file_download_requires_auth_and_strips_exif(auth_client, client):
    c = auth_client
    p = c.post("/api/properties", json=PROP).json()
    img = Image.new("RGB", (100, 100))
    exif = img.getexif()
    exif[0x8825] = {2: (45.0, 0.0, 0.0)}  # GPSInfo
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    doc = c.post("/api/documents", data={"owner_type": "property", "owner_id": str(p["id"])}, files={"file": ("g.jpg", buf.getvalue(), "image/jpeg")}).json()
    got = c.get(f"/api/files/{doc['id']}")
    assert got.status_code == 200
    assert not Image.open(io.BytesIO(got.content)).getexif()
    c.cookies.clear()
    assert c.get(f"/api/files/{doc['id']}").status_code == 401


def test_upload_rejects_spoofed_and_macro_files(auth_client):
    p = auth_client.post("/api/properties", json=PROP).json()
    bad = auth_client.post("/api/documents", data={"owner_type": "property", "owner_id": str(p["id"])}, files={"file": ("x.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")})
    assert bad.status_code == 400
    exe = auth_client.post("/api/documents", data={"owner_type": "property", "owner_id": str(p["id"])}, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert exe.status_code == 400
    import zipfile

    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("word/document.xml", "<x/>")
        zf.writestr("word/vbaProject.bin", "macro")
    mac = auth_client.post("/api/documents", data={"owner_type": "property", "owner_id": str(p["id"])}, files={"file": ("m.docx", z.getvalue(), "application/octet-stream")})
    assert mac.status_code == 400


def test_dashboard_and_exports(auth_client):
    auth_client.post("/api/properties", json=PROP | {"description": "=HYPERLINK(\"x\")"})
    auth_client.post("/api/requests", json=REQ)
    d = auth_client.get("/api/dashboard").json()
    assert d["kpis"]["offres"] == 1 and d["kpis"]["demandes_actives"] == 1 and d["kpis"]["correspondances"] == 1
    csv = auth_client.get("/api/exports/offres.csv")
    assert csv.status_code == 200 and "'=HYPERLINK" in csv.content.decode("utf-8-sig")
    assert auth_client.get("/api/exports/demandes.xlsx").status_code == 200


def test_settings_weights_and_outlook_url(auth_client):
    r = auth_client.put("/api/settings", json={"matching_weights": {"localisation": 50, "surface": 25, "budget": 25, "typologie": 0, "technique": 0, "disponibilite": 0}})
    assert r.status_code == 200
    assert auth_client.put("/api/settings", json={"outlook_agent_url": "http://exemple.com:8765"}).status_code == 400


def test_contact_rgpd(auth_client):
    c = auth_client.post("/api/contacts", json={"first_name": "Jean", "last_name": "Test", "email": "jean@exemple.test", "origin": "Salon"}).json()
    assert auth_client.get(f"/api/contacts/{c['id']}/export").json()["contact"]["email"] == "jean@exemple.test"
    auth_client.delete(f"/api/contacts/{c['id']}")
    got = auth_client.get(f"/api/contacts/{c['id']}").json()
    assert got["email"] is None and got["opposed_to_prospecting"] is True


def test_demo_data_separated(auth_client):
    from app.db import SessionLocal
    from app.demo import purge_demo, seed_demo

    with SessionLocal() as db:
        seed_demo(db)
    assert auth_client.get("/api/properties", params={"demo": "real"}).json()["total"] == 0
    demo = auth_client.get("/api/properties", params={"demo": "demo"}).json()
    assert demo["total"] == 8 and all(p["is_demo"] for p in demo["items"])
    assert auth_client.get("/api/matches").json()["total"] > 0
    with SessionLocal() as db:
        purge_demo(db)
    assert auth_client.get("/api/properties", params={"demo": "all"}).json()["total"] == 0
