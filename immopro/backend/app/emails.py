"""Génération d'emails préremplis. Aucun envoi automatique n'est effectué par l'application."""
from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .matching import TYPE_LABELS
from .models import Contact, Property

TEMPLATES = {
    "presentation_bien": "Présentation d'un bien",
    "selection_biens": "Sélection de plusieurs biens",
    "proposition_visite": "Proposition de visite",
    "demande_info_annonceur": "Demande d'informations à un annonceur",
    "relance": "Relance",
    "compte_rendu": "Compte rendu de visite",
}

TRANSACTION_WORDS = {"vente": "à vendre", "location": "à louer", "vente_ou_location": "à vendre ou à louer"}
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def fmt_num(n: float | None, unit: str = "") -> str:
    if n is None:
        return ""
    s = f"{n:,.0f}".replace(",", " ") if abs(n) >= 100 or float(n).is_integer() else f"{n:.1f}".replace(".", ",")
    return f"{s} {unit}".strip()


def fmt_slot(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{DAYS[dt.weekday()]} {dt.day} {MONTHS[dt.month - 1]} {dt.year} à {dt:%H}h{dt:%M}"


def greeting(contact: Contact | None, fallback_name: str | None = None) -> str:
    if contact and contact.last_name:
        civ = contact.civility or ""
        if civ in ("M.", "M", "Monsieur"):
            return f"Bonjour Monsieur {contact.last_name},"
        if civ in ("Mme", "Madame"):
            return f"Bonjour Madame {contact.last_name},"
        return f"Bonjour {' '.join(x for x in [contact.first_name, contact.last_name] if x)},"
    if fallback_name:
        return f"Bonjour {fallback_name},"
    return "Bonjour,"


def property_title(p: Property) -> str:
    t = TYPE_LABELS.get(p.property_type or "", "Bien")
    tr = TRANSACTION_WORDS.get(p.transaction or "", "")
    loc = p.city + (f" ({p.postal_code})" if p.postal_code else "") if p.city else (p.postal_code or "")
    return " ".join(x for x in [t, tr, ("à " + loc) if loc else ""] if x)


def property_lines(p: Property) -> list[str]:
    """Caractéristiques réellement renseignées (aucune valeur absente n'est mentionnée)."""
    lines = []
    if p.surface_total:
        s = f"Surface : {fmt_num(p.surface_total, 'm²')}"
        if p.surface_divisible_min:
            s += f" (divisible à partir de {fmt_num(p.surface_divisible_min, 'm²')})"
        details = []
        if p.surface_storage:
            details.append(f"{fmt_num(p.surface_storage, 'm²')} d'entrepôt/activité")
        if p.surface_offices:
            details.append(f"{fmt_num(p.surface_offices, 'm²')} de bureaux")
        if details:
            s += " dont " + " et ".join(details)
        lines.append(s)
    if p.sale_price:
        lines.append(f"Prix de vente : {fmt_num(p.sale_price, '€')}")
    if p.annual_rent:
        s = f"Loyer : {fmt_num(p.annual_rent, '€')} HT HC / an"
        if p.rent_per_sqm:
            s += f" ({fmt_num(p.rent_per_sqm, '€')}/m²/an)"
        lines.append(s)
    elif p.rent_per_sqm:
        lines.append(f"Loyer : {fmt_num(p.rent_per_sqm, '€')} HT HC /m²/an")
    tech = []
    if p.clear_height:
        tech.append(f"hauteur libre {fmt_num(p.clear_height, 'm')}")
    if p.dock_count:
        tech.append(f"{p.dock_count} quai{'s' if p.dock_count > 1 else ''}")
    if p.sectional_doors:
        tech.append(f"{p.sectional_doors} porte{'s' if p.sectional_doors > 1 else ''} sectionnelle{'s' if p.sectional_doors > 1 else ''}")
    if p.hgv_access:
        tech.append("accès poids lourds")
    if p.floor_load:
        tech.append(f"résistance au sol {fmt_num(p.floor_load, 't/m²')}")
    if p.power_kva:
        tech.append(f"puissance {fmt_num(p.power_kva, 'kVA')}")
    if p.parking_spaces:
        tech.append(f"{p.parking_spaces} places de parking")
    if tech:
        lines.append("Caractéristiques : " + ", ".join(tech))
    if p.available_from:
        lines.append(f"Disponibilité : {p.available_from:%d/%m/%Y}")
    elif p.availability_note:
        lines.append(f"Disponibilité : {p.availability_note}")
    return lines


def property_block(p: Property, fit: list[str] | None = None) -> str:
    head = f"• {property_title(p)}" + (f" — réf. {p.reference}" if p.reference else "")
    body = [head] + [f"  {line}" for line in property_lines(p)]
    if fit:
        body.append("  Adéquation avec votre recherche : " + "; ".join(fit[:4]))
    return "\n".join(body)


def build_email(
    template: str,
    *,
    contact: Contact | None = None,
    recipient_name: str | None = None,
    properties: list[Property] | None = None,
    fits: dict[int, list[str]] | None = None,
    slots: list[str] | None = None,
    request_label: str | None = None,
    sender_name: str | None = None,
    signature: str | None = None,
    listing_url: str | None = None,
    notes: str | None = None,
) -> dict:
    if template not in TEMPLATES:
        raise ValueError("Modèle inconnu")
    props = properties or []
    fits = fits or {}
    hello = greeting(contact, recipient_name)
    sign = signature or ("Bien cordialement,\n" + (sender_name or ""))
    if not sign.lower().startswith(("bien cordialement", "cordialement", "bien à vous")):
        sign = "Bien cordialement,\n\n" + sign
    refs = ", ".join(p.reference for p in props if p.reference)
    slots_txt = "\n".join(f"  – {fmt_slot(s)}" for s in (slots or []))
    p0 = props[0] if props else None

    if template == "presentation_bien":
        subject = f"Proposition : {property_title(p0)}" if p0 else "Proposition de bien"
        if p0 and p0.reference:
            subject += f" (réf. {p0.reference})"
        intro = "Suite à votre recherche" + (f" « {request_label} »" if request_label else "") + ", j'ai le plaisir de vous présenter le bien suivant, qui me semble correspondre à vos critères :"
        blocks = "\n\n".join(property_block(p, fits.get(p.id)) for p in props)
        body = f"{hello}\n\n{intro}\n\n{blocks}\n\nLa fiche détaillée est disponible sur demande. Si ce bien retient votre attention, je vous propose d'organiser une visite : pourriez-vous m'indiquer vos disponibilités ?\n\n{sign}"
    elif template == "selection_biens":
        subject = f"Sélection de {len(props)} biens pour votre recherche" + (f" « {request_label} »" if request_label else "")
        blocks = "\n\n".join(property_block(p, fits.get(p.id)) for p in props)
        body = f"{hello}\n\nComme convenu, voici une sélection de biens correspondant à votre recherche" + (f" « {request_label} »" if request_label else "") + f" :\n\n{blocks}\n\nJe reste à votre disposition pour vous transmettre les fiches détaillées et organiser des visites. N'hésitez pas à me communiquer vos disponibilités.\n\n{sign}"
    elif template == "proposition_visite":
        subject = "Proposition de visite" + (f" – {property_title(p0)}" if p0 else "") + (f" (réf. {refs})" if refs else "")
        slots_part = (
            f"Je vous propose les créneaux suivants :\n{slots_txt}\n\nMerci de me confirmer celui qui vous convient, ou de me communiquer vos disponibilités si aucun ne vous convient."
            if slots
            else "Pourriez-vous me communiquer vos disponibilités pour organiser cette visite ?"
        )
        blocks = "\n\n".join(property_block(p, fits.get(p.id)) for p in props)
        body = f"{hello}\n\nJe vous propose de visiter le bien suivant :\n\n{blocks}\n\n{slots_part}\n\n{sign}"
    elif template == "demande_info_annonceur":
        subject = "Demande d'informations" + (f" – annonce réf. {refs}" if refs else (f" – {property_title(p0)}" if p0 else ""))
        what = property_block(p0) if p0 else ""
        url = f"\nAnnonce consultée : {listing_url}\n" if listing_url else ""
        body = (
            f"{hello}\n\nJe vous contacte au sujet de votre annonce :\n\n{what}\n{url}\n"
            "Je représente un client à la recherche d'un bien de ce type. Pourriez-vous me confirmer la disponibilité du bien et me transmettre :\n"
            "  – la fiche technique complète et le plan ;\n  – les conditions financières (prix ou loyer, charges, taxe foncière, honoraires) ;\n"
            "  – les modalités de collaboration entre confrères, le cas échéant ;\n  – vos disponibilités pour une visite.\n\n"
            f"{sign}"
        )
    elif template == "relance":
        subject = "Relance" + (f" – {property_title(p0)}" if p0 else "") + (f" (réf. {refs})" if refs else "")
        what = ("au sujet " + ("des biens suivants" if len(props) > 1 else "du bien suivant") + " :\n\n" + "\n\n".join(property_block(p) for p in props)) if props else "au sujet de votre recherche immobilière."
        body = f"{hello}\n\nJe me permets de revenir vers vous {what}\n\nAvez-vous pu en prendre connaissance ? Je reste à votre disposition pour tout complément d'information ou pour organiser une visite.\n\n{sign}"
    else:  # compte_rendu
        subject = "Compte rendu de visite" + (f" – {property_title(p0)}" if p0 else "") + (f" (réf. {refs})" if refs else "")
        blocks = "\n\n".join(property_block(p) for p in props)
        body = f"{hello}\n\nVeuillez trouver ci-dessous le compte rendu de notre visite :\n\n{blocks}\n\nPoints observés :\n{notes or '  – [à compléter]'}\n\nProchaines étapes :\n  – [à compléter]\n\n{sign}"
    return {"subject": subject, "body": body}


def build_eml(to: str | None, cc: str | None, subject: str, body: str, sender: str | None, attachments: list[tuple[str, bytes, str]]) -> bytes:
    """Crée un fichier .eml « non envoyé » (X-Unsent: 1) ouvrable comme brouillon dans Outlook,
    le nouvel Outlook, Thunderbird ou Apple Mail. L'envoi reste à l'initiative de l'utilisateur."""
    msg = EmailMessage()
    if to:
        msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if sender:
        msg["From"] = sender
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg["X-Unsent"] = "1"
    msg.set_content(body)
    for name, data, mime in attachments:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    return bytes(msg)
