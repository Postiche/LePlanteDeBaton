"""Référentiel géographique français (départements → régions), distances et géocodage."""
from __future__ import annotations

import logging
import math
import re
import unicodedata

import httpx

from .config import get_settings

log = logging.getLogger(__name__)

REGIONS: dict[str, list[str]] = {
    "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "Bretagne": ["22", "29", "35", "56"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Corse": ["2A", "2B"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
    "Guadeloupe": ["971"],
    "Martinique": ["972"],
    "Guyane": ["973"],
    "La Réunion": ["974"],
    "Mayotte": ["976"],
}
DEPT_TO_REGION = {d: r for r, ds in REGIONS.items() for d in ds}


def normalize(text: str | None) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    t = re.sub(r"\bsaint\b", "st", t)
    t = re.sub(r"\bsainte\b", "ste", t)
    return t


def department_from_postal_code(cp: str | None) -> str | None:
    if not cp:
        return None
    cp = cp.strip().replace(" ", "")
    if not re.fullmatch(r"\d{5}", cp):
        return None
    if cp.startswith("97"):
        return cp[:3]
    if cp.startswith("20"):
        # Corse : 200xx/201xx → 2A, 202xx/206xx → 2B
        return "2A" if int(cp) < 20200 else "2B"
    return cp[:2]


def region_from_department(dept: str | None) -> str | None:
    return DEPT_TO_REGION.get(dept or "")


def normalize_region(name: str | None) -> str | None:
    n = normalize(name)
    for r in REGIONS:
        if normalize(r) == n:
            return r
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geocode(address: str | None, postal_code: str | None, city: str | None) -> dict | None:
    """Géocode une adresse via le service public configuré (Géoplateforme IGN).

    Retourne None si le service est désactivé, injoignable ou si le résultat est peu fiable.
    Aucune coordonnée n'est jamais inventée.
    """
    s = get_settings()
    if not s.geocoder_enabled:
        return None
    q = " ".join(x for x in [address, postal_code, city] if x)
    if len(q) < 3:
        return None
    params = {"q": q, "limit": 1}
    if postal_code:
        params["postcode"] = postal_code
    try:
        r = httpx.get(s.geocoder_url, params=params, timeout=8.0)
        r.raise_for_status()
        feats = r.json().get("features") or []
    except Exception as exc:  # réseau, JSON…
        log.warning("Géocodage indisponible : %s", exc)
        return None
    if not feats:
        return None
    f = feats[0]
    score = (f.get("properties") or {}).get("score", 0)
    if score < 0.5:
        return None
    lon, lat = f["geometry"]["coordinates"]
    props = f.get("properties") or {}
    return {"latitude": lat, "longitude": lon, "label": props.get("label"), "score": score, "city": props.get("city"), "postcode": props.get("postcode")}
