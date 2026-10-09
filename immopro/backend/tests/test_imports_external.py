import io

from app.importers import extract_property_from_text, extract_request_from_text, parse_number

from .test_flows import PROP, REQ


def test_parse_number_french_formats():
    assert parse_number("1 200,50 €") == 1200.5
    assert parse_number("12.000 m²") == 12000
    assert parse_number("450 k€") == 450000
    assert parse_number("") is None and parse_number("n.c.") is None


def test_csv_import_requires_validation(auth_client):
    csv = "Référence;Type de bien;Transaction;Ville;Code postal;Surface totale;Loyer annuel;Hauteur libre;Quais;Accès PL;Colonne inconnue\n" \
          "IMP-1;Entrepôt;Location;Saint-Priest;69800;6 000;360 000 €;10,5;6;oui;x\n" \
          "IMP-2;Bureaux;Vente;Lyon;69003;;;;;;\n"
    b = auth_client.post("/api/imports", data={"target": "property"}, files={"file": ("offres.csv", csv.encode("cp1252"), "text/csv")}).json()
    assert b["status"] == "a_valider"
    assert any("Colonne inconnue" in w for w in b["warnings"])
    row = b["rows"][0]["data"]
    assert row == row | {"reference": "IMP-1", "property_type": "entrepot", "transaction": "location", "surface_total": 6000.0, "annual_rent": 360000.0, "clear_height": 10.5, "dock_count": 6, "hgv_access": True}
    assert "surface_total" not in b["rows"][1]["data"]  # valeur absente non inventée
    # Rien n'est enregistré avant validation
    assert auth_client.get("/api/properties").json()["total"] == 0
    res = auth_client.post(f"/api/imports/{b['id']}/commit").json()
    assert len(res["created"]) == 2
    props = auth_client.get("/api/properties").json()["items"]
    assert {p["source_kind"] for p in props} == {"import"}
    # Ré-import : doublons détectés, ignorés par défaut
    b2 = auth_client.post("/api/imports", data={"target": "property"}, files={"file": ("offres.csv", csv.encode("cp1252"), "text/csv")}).json()
    assert all(r["action"] == "ignorer" and r["duplicates"] for r in b2["rows"])


def test_xlsx_request_import(auth_client):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Client", "Email", "Type de bien", "Transaction", "Départements", "Surface min", "Surface max", "Budget max", "Critères impératifs"])
    ws.append(["ACME", "achats@acme.test", "entrepôt, logistique", "location", "69; 38", 4000, 9000, 500000, "surface et localisation"])
    buf = io.BytesIO()
    wb.save(buf)
    b = auth_client.post("/api/imports", data={"target": "request"}, files={"file": ("demandes.xlsx", buf.getvalue(), "application/octet-stream")}).json()
    d = b["rows"][0]["data"]
    assert d["departments"] == ["69", "38"] and set(d["property_types"]) == {"entrepot", "plateforme_logistique"}
    assert set(d["imperatives"]) == {"surface", "localisation"}
    assert auth_client.post(f"/api/imports/{b['id']}/commit").json()["created"]


def test_text_extraction_property():
    text = """Entrepôt logistique à louer
    Réf. : ENT-2045
    ZAC des Exemples 69800 Saint-Priest
    Surface totale de 12 500 m² divisible à partir de 4 000 m²
    dont 600 m² de bureaux. Hauteur libre 11,5 m. 14 quais, 2 portes sectionnelles.
    Accès poids lourds. Loyer : 562 500 € HT HC / an. Taxe foncière : 48 000 €
    Contact : agence@exemple.test - 04 00 00 00 00"""
    d = extract_property_from_text(text)["data"]
    assert d["reference"] == "ENT-2045"
    assert d["surface_total"] == 12500 and d["surface_divisible_min"] == 4000 and d["surface_offices"] == 600
    assert d["clear_height"] == 11.5 and d["dock_count"] == 14 and d["sectional_doors"] == 2
    assert d["hgv_access"] is True and d["annual_rent"] == 562500 and d["property_tax"] == 48000
    assert d["postal_code"] == "69800" and d["city"].startswith("Saint-Priest")
    assert d["transaction"] == "location" and d["property_type"] == "plateforme_logistique"
    assert "sale_price" not in d and "power_kva" not in d


def test_text_extraction_request():
    d = extract_request_from_text("Recherche entrepôt en location entre 3 000 et 5 000 m², budget 300 k€, hauteur 8 m, 4 quais, département 69, rayon de 30 km autour de Lyon. Impératif : surface")["data"]
    assert d["surface_min"] == 3000 and d["surface_max"] == 5000 and d["budget_max"] == 300000
    assert d["min_docks"] == 4 and d["departments"] == ["69"] and d["radius_km"] == 30 and d["imperatives"] == ["surface"]


def test_pdf_and_docx_import(auth_client):
    from docx import Document as Docx
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    cv = canvas.Canvas(buf)
    cv.drawString(50, 800, "Local d'activite a vendre - 95500 Gonesse")
    cv.drawString(50, 780, "Surface totale 2 200 m2 - Prix : 2 350 000 EUR")
    cv.save()
    b = auth_client.post("/api/imports", data={"target": "property"}, files={"file": ("fiche.pdf", buf.getvalue(), "application/pdf")}).json()
    d = b["rows"][0]["data"]
    assert d["surface_total"] == 2200 and d["sale_price"] == 2350000 and d["transaction"] == "vente"
    doc = Docx()
    doc.add_paragraph("Bureaux à louer, surface 800 m², loyer 120 000 € HT HC / an")
    out = io.BytesIO()
    doc.save(out)
    b = auth_client.post("/api/imports", data={"target": "property"}, files={"file": ("fiche.docx", out.getvalue(), "application/octet-stream")}).json()
    assert b["rows"][0]["data"]["annual_rent"] == 120000


def test_multisource_search_does_not_fabricate(auth_client):
    auth_client.post("/api/properties", json=PROP)
    r = auth_client.post("/api/requests", json=REQ).json()
    res = auth_client.post(f"/api/external/search/{r['id']}").json()
    assert len(res["internal"]) == 1
    for s in res["sources"]:
        assert s["results"] == [] and s["automatic"] is False
        assert s["link"]["url"] in ("https://www.bureauxlocaux.com", "https://www.geolocaux.com")
        assert s["link"]["parametrized"] is False
        assert any(c["label"] == "Surface" for c in s["criteria"])
    assert auth_client.get("/api/external/searches").json()[0]["request_id"] == r["id"]


def test_user_defined_template_and_manual_listing(auth_client):
    assert auth_client.put("/api/settings", json={"connector_geolocaux_search_template": "https://evil.example/{ville}"}).status_code == 400
    assert auth_client.put("/api/settings", json={"connector_geolocaux_search_template": "https://www.geolocaux.com.evil.example/{ville}"}).status_code == 400
    assert auth_client.put("/api/settings", json={"connector_geolocaux_search_template": "https://www.geolocaux.com/recherche?cp={code_postal}&smin={surface_min}"}).status_code == 200
    r = auth_client.post("/api/requests", json=REQ | {"postal_codes": ["69800"]}).json()
    res = auth_client.post(f"/api/external/search/{r['id']}").json()
    geo = next(s for s in res["sources"] if s["key"] == "geolocaux")
    assert geo["link"]["parametrized"] and geo["link"]["url"].endswith("cp=69800&smin=5000")
    listing = {"url": "https://www.geolocaux.com/annonce/exemple-123", "title": "Entrepôt", "property_type": "entrepot", "transaction": "location", "city": "Saint-Priest", "postal_code": "69800", "surface": 6000, "price": 330000, "price_kind": "loyer_annuel", "advertiser_name": "Agence X"}
    l = auth_client.post("/api/external/listings", json=listing).json()
    assert l["source"] == "geolocaux" and l["fresh"]
    assert auth_client.post("/api/external/listings", json=listing).status_code == 409
    res = auth_client.post(f"/api/external/search/{r['id']}").json()
    assert res["external_listings"][0]["match"]["score"] > 50
    p = auth_client.post(f"/api/external/listings/{l['id']}/to-property", json={"title": "Entrepôt", "property_type": "entrepot", "transaction": "location", "city": "Saint-Priest", "postal_code": "69800", "surface_total": 6000, "annual_rent": 330000}).json()
    assert p["source_kind"] == "externe" and p["source_url"] == listing["url"] and p["source_name"] == "Geolocaux"
    assert p["agency_contact"]["is_public_listing_contact"] is True
