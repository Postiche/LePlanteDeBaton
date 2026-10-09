"""Fiches PDF commerciales et dossiers multi-biens (ReportLab)."""
from __future__ import annotations

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .emails import TRANSACTION_WORDS, fmt_num, property_title
from .matching import TYPE_LABELS
from .models import Contact, Property

NAVY = colors.HexColor("#0B1F3A")
TEAL = colors.HexColor("#14B8A6")
GREY = colors.HexColor("#F1F4F8")
TEXT = colors.HexColor("#1F2937")

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_styles["Heading1"], textColor=NAVY, fontSize=18, leading=22, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=_styles["Heading2"], textColor=NAVY, fontSize=12.5, leading=16, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("body", parent=_styles["BodyText"], textColor=TEXT, fontSize=9.5, leading=13, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10, textColor=colors.HexColor("#6B7280"))
TAG = ParagraphStyle("tag", parent=BODY, textColor=TEAL, fontSize=10, leading=12)


def _p(text: str, style=BODY) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _characteristics(p: Property) -> list[tuple[str, str]]:
    rows = [
        ("Référence", p.reference or ""),
        ("Type de bien", TYPE_LABELS.get(p.property_type or "", "")),
        ("Transaction", {"vente": "Vente", "location": "Location", "vente_ou_location": "Vente ou location"}.get(p.transaction or "", "")),
        ("Surface totale", fmt_num(p.surface_total, "m²")),
        ("Divisible à partir de", fmt_num(p.surface_divisible_min, "m²")),
        ("Entrepôt / activité", fmt_num(p.surface_storage, "m²")),
        ("Bureaux", fmt_num(p.surface_offices, "m²")),
        ("Terrain", fmt_num(p.land_area, "m²")),
        ("Hauteur libre", fmt_num(p.clear_height, "m")),
        ("Quais", str(p.dock_count) if p.dock_count is not None else ""),
        ("Portes sectionnelles", str(p.sectional_doors) if p.sectional_doors is not None else ""),
        ("Accès poids lourds", {True: "Oui", False: "Non"}.get(p.hgv_access, "")),
        ("Résistance au sol", fmt_num(p.floor_load, "t/m²")),
        ("Puissance électrique", fmt_num(p.power_kva, "kVA")),
        ("Parking", f"{p.parking_spaces} places" if p.parking_spaces is not None else ""),
        ("État", p.condition or ""),
        ("Disponibilité", p.available_from.strftime("%d/%m/%Y") if p.available_from else (p.availability_note or "")),
        ("Prix de vente", fmt_num(p.sale_price, "€")),
        ("Loyer annuel", (fmt_num(p.annual_rent, "€") + " HT HC") if p.annual_rent else ""),
        ("Loyer au m²", (fmt_num(p.rent_per_sqm, "€") + " HT HC/m²/an") if p.rent_per_sqm else ""),
        ("Charges", fmt_num(p.charges, "€")),
        ("Taxe foncière", fmt_num(p.property_tax, "€")),
        ("Honoraires", p.fees or ""),
    ]
    return [(k, v) for k, v in rows if v]


def _contact_lines(c: Contact | None, user_contact: dict | None) -> list[str]:
    if c is not None:
        name = " ".join(x for x in [c.first_name, c.last_name] if x)
        return [x for x in [name, c.job_title, c.company.name if c.company else None, c.phone or c.mobile, c.email] if x]
    if user_contact:
        return [x for x in [user_contact.get("full_name"), user_contact.get("phone"), user_contact.get("email")] if x]
    return []


def property_story(p: Property, photos: list[bytes], company_name: str, user_contact: dict | None) -> list:
    story: list = []
    story.append(_p(company_name or "Fiche commerciale", TAG))
    story.append(_p(p.title or property_title(p), H1))
    loc = ", ".join(x for x in [p.address, " ".join(x for x in [p.postal_code, p.city] if x)] if x)
    if loc:
        story.append(_p(loc, BODY))
    story.append(Spacer(1, 4 * mm))

    imgs = []
    for data in photos[:3]:
        try:
            img = Image(io.BytesIO(data))
            ratio = img.imageHeight / float(img.imageWidth)
            w = 170 * mm if not imgs and len(photos) == 1 else 84 * mm
            img.drawWidth, img.drawHeight = w, min(w * ratio, 70 * mm)
            imgs.append(img)
        except Exception:
            continue
    if imgs:
        if len(imgs) == 1:
            story.append(imgs[0])
        else:
            story.append(Table([imgs[:2]], colWidths=[86 * mm, 86 * mm]))
            if len(imgs) > 2:
                story.append(Spacer(1, 2 * mm))
                story.append(Table([[imgs[2]]], colWidths=[172 * mm]))
        story.append(Spacer(1, 4 * mm))

    rows = _characteristics(p)
    if rows:
        story.append(_p("Caractéristiques", H2))
        half = (len(rows) + 1) // 2
        left, right = rows[:half], rows[half:]
        data = []
        for i in range(half):
            l = left[i]
            r = right[i] if i < len(right) else ("", "")
            data.append([_p(l[0], SMALL), _p(l[1]), _p(r[0], SMALL), _p(r[1])])
        t = Table(data, colWidths=[34 * mm, 52 * mm, 34 * mm, 52 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), GREY),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(t)
    if p.description:
        story.append(_p("Description", H2))
        story.append(_p(p.description[:3000]))
    if p.latitude is not None and p.longitude is not None:
        story.append(_p("Localisation", H2))
        story.append(_p(f"Coordonnées GPS : {p.latitude:.5f}, {p.longitude:.5f}"))
    contact = _contact_lines(p.sales_contact, user_contact)
    if contact:
        story.append(KeepTogether([_p("Votre contact", H2), _p("\n".join(contact))]))
    return story


def _on_page(canvas, doc, footer: str):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, A4[1] - 9 * mm, A4[0], 1 * mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(18 * mm, 10 * mm, footer)
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build(story: list, title: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title=title)
    footer = f"Document non contractuel — informations communiquées sous réserve d'exactitude — édité le {date.today():%d/%m/%Y}"
    doc.build(story, onFirstPage=lambda c, d: _on_page(c, d, footer), onLaterPages=lambda c, d: _on_page(c, d, footer))
    return buf.getvalue()


def property_pdf(p: Property, photos: list[bytes], company_name: str = "", user_contact: dict | None = None) -> bytes:
    return _build(property_story(p, photos, company_name, user_contact), p.title or property_title(p))


def dossier_pdf(
    items: list[tuple[Property, list[bytes]]],
    client_label: str,
    company_name: str = "",
    user_contact: dict | None = None,
    intro: str | None = None,
) -> bytes:
    story: list = [Spacer(1, 30 * mm), _p(company_name or "Dossier de biens", TAG), _p(f"Sélection de biens pour {client_label}", H1)]
    story.append(_p(f"{len(items)} bien(s) — {date.today():%d/%m/%Y}", BODY))
    if intro:
        story.append(Spacer(1, 6 * mm))
        story.append(_p(intro))
    story.append(Spacer(1, 8 * mm))
    head = [_p("Réf.", SMALL), _p("Bien", SMALL), _p("Surface", SMALL), _p("Prix / loyer", SMALL)]
    rows = [head]
    for p, _ in items:
        price = fmt_num(p.sale_price, "€") if p.sale_price else ((fmt_num(p.annual_rent, "€") + " /an") if p.annual_rent else "")
        rows.append([_p(p.reference or ""), _p(p.title or property_title(p)), _p(fmt_num(p.surface_total, "m²")), _p(price)])
    t = Table(rows, colWidths=[24 * mm, 88 * mm, 28 * mm, 34 * mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREY), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB"))]))
    story.append(t)
    for p, photos in items:
        story.append(PageBreak())
        story.extend(property_story(p, photos, company_name, user_contact))
    return _build(story, f"Dossier {client_label}")


__all__ = ["property_pdf", "dossier_pdf", "TRANSACTION_WORDS"]
