"""Moteur de matching bidirectionnel offres ↔ demandes.

Principes :
- score explicable sur 100, ventilé par groupe de critères pondérés (pondérations configurables) ;
- un critère non exprimé par le client est « non contraint » et rapporte tous ses points ;
- une information absente de l'offre est « manquante » : elle ne rapporte aucun point dans le
  score, mais le « score potentiel » indique ce que l'offre obtiendrait si elle était favorable.
  Une information manquante n'est jamais considérée comme validée ;
- un critère n'est éliminatoire que s'il a été explicitement déclaré impératif ET qu'il est
  effectivement non satisfait (jamais sur une information manquante).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from .geo import department_from_postal_code, haversine_km, normalize, region_from_department

DEFAULT_WEIGHTS: dict[str, float] = {
    "localisation": 30,
    "surface": 25,
    "budget": 20,
    "typologie": 10,
    "technique": 10,
    "disponibilite": 5,
}
GROUP_LABELS = {
    "localisation": "Localisation",
    "surface": "Surface",
    "budget": "Budget",
    "typologie": "Typologie et transaction",
    "technique": "Caractéristiques techniques",
    "disponibilite": "Disponibilité",
}
TYPE_LABELS = {
    "entrepot": "Entrepôt",
    "plateforme_logistique": "Plateforme logistique",
    "local_activite": "Local d'activité",
    "batiment_industriel": "Bâtiment industriel",
    "bureaux": "Bureaux",
    "terrain": "Terrain",
    "commerce": "Commerce",
    "autre": "Autre",
}
# Familles de biens proches (correspondance partielle)
TYPE_FAMILIES = [
    {"entrepot", "plateforme_logistique", "local_activite", "batiment_industriel"},
    {"bureaux", "local_activite"},
    {"commerce", "local_activite"},
]


def normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    w = {k: float((weights or {}).get(k, v)) for k, v in DEFAULT_WEIGHTS.items()}
    w = {k: max(0.0, v) for k, v in w.items()}
    total = sum(w.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v * 100.0 / total for k, v in w.items()}


@dataclass
class Check:
    key: str  # clé utilisée pour les critères impératifs
    label: str
    constrained: bool
    ratio: float | None = None  # None = information manquante côté offre
    message: str = ""

    @property
    def status(self) -> str:
        if not self.constrained:
            return "non_contraint"
        if self.ratio is None:
            return "manquant"
        if self.ratio >= 0.999:
            return "ok"
        if self.ratio > 0:
            return "partiel"
        return "ecart"


@dataclass
class GroupResult:
    group: str
    label: str
    weight: float
    earned: float = 0.0
    potential: float = 0.0
    checks: list[dict] = field(default_factory=list)


def _g(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _fmt(n: float | None, unit: str = "") -> str:
    if n is None:
        return "?"
    s = f"{n:,.0f}".replace(",", " ") if abs(n) >= 100 else (f"{n:.2f}".rstrip("0").rstrip("."))
    return f"{s} {unit}".strip()


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# Évaluation par groupe
# ---------------------------------------------------------------------------


def _check_location(req, prop) -> list[Check]:
    cities = [normalize(c) for c in (_g(req, "cities") or []) if c]
    cps = [c.strip() for c in (_g(req, "postal_codes") or []) if c]
    depts = [str(d).strip().upper().zfill(2) for d in (_g(req, "departments") or []) if d]
    regions = [normalize(r) for r in (_g(req, "regions") or []) if r]
    clat, clon, radius = _g(req, "center_latitude"), _g(req, "center_longitude"), _g(req, "radius_km")
    has_radius = clat is not None and clon is not None and radius
    if not (cities or cps or depts or regions or has_radius):
        return [Check("localisation", "Localisation", False, message="Aucun critère de localisation exprimé.")]

    p_city = normalize(_g(prop, "city"))
    p_cp = (_g(prop, "postal_code") or "").strip()
    p_dept = _g(prop, "department") or department_from_postal_code(p_cp)
    p_region = _g(prop, "region") or region_from_department(p_dept)
    plat, plon = _g(prop, "latitude"), _g(prop, "longitude")

    best = 0.0
    reasons: list[str] = []
    evaluable = False

    if has_radius:
        if plat is not None and plon is not None:
            evaluable = True
            d = haversine_km(clat, clon, plat, plon)
            r = float(radius)
            ratio = 1.0 if d <= r else _clip(1 - (d - r) / r)
            best = max(best, ratio)
            where = _g(req, "center_label") or "le centre de recherche"
            reasons.append(f"à {d:.1f} km de {where} (rayon {r:.0f} km)")
        else:
            reasons.append("coordonnées GPS absentes : distance non calculable")

    if p_city or p_cp or p_dept:
        if cities or cps or depts or regions:
            evaluable = True
        if p_city and p_city in cities:
            best = 1.0
            reasons.append(f"commune demandée ({_g(prop, 'city')})")
        if p_cp and p_cp in cps:
            best = 1.0
            reasons.append(f"code postal demandé ({p_cp})")
        if p_dept and p_dept in depts:
            best = 1.0
            reasons.append(f"département demandé ({p_dept})")
        if p_region and normalize(p_region) in regions:
            best = max(best, 1.0)
            reasons.append(f"région demandée ({p_region})")
        if best < 1.0:
            # Proximité administrative : même département ou même région que les lieux demandés
            req_depts = set(depts) | {department_from_postal_code(c) for c in cps if department_from_postal_code(c)}
            req_regions = {region_from_department(d) for d in req_depts if region_from_department(d)} | {
                r for r in (_g(req, "regions") or [])
            }
            if p_dept and p_dept in req_depts and best < 0.7:
                best = 0.7
                reasons.append(f"même département ({p_dept}) qu'un lieu demandé")
            elif p_region and p_region in req_regions and best < 0.4:
                best = 0.4
                reasons.append(f"même région ({p_region}) qu'un lieu demandé")

    if not evaluable:
        return [Check("localisation", "Localisation", True, None, "Localisation de l'offre incomplète : " + ("; ".join(reasons) or "à vérifier"))]
    if best == 0 and not reasons:
        reasons.append(f"hors zone ({_g(prop, 'city') or p_cp or p_dept})")
    elif best == 0:
        reasons.insert(0, "hors zone")
    return [Check("localisation", "Localisation", True, best, "; ".join(reasons))]


def _effective_surface(req, prop) -> tuple[float | None, bool]:
    total = _g(prop, "surface_total")
    smin, smax = _g(req, "surface_min"), _g(req, "surface_max")
    div = _g(prop, "surface_divisible_min")
    if total is None:
        return None, False
    if smax and total > smax and div and div <= smax:
        return max(div, smin or div), True
    return total, False


def _check_surface(req, prop) -> list[Check]:
    smin, smax = _g(req, "surface_min"), _g(req, "surface_max")
    if not smin and not smax:
        return [Check("surface", "Surface", False, message="Aucune surface exprimée.")]
    total = _g(prop, "surface_total")
    if total is None:
        return [Check("surface", "Surface", True, None, "Surface de l'offre non renseignée.")]
    div = _g(prop, "surface_divisible_min")
    wanted = f"{_fmt(smin, 'm²') if smin else '—'} à {_fmt(smax, 'm²') if smax else '—'}"
    if smin and total < smin:
        gap = (smin - total) / smin
        return [Check("surface", "Surface", True, _clip(1 - gap / 0.3), f"{_fmt(total, 'm²')} : inférieure de {gap:.0%} au minimum demandé ({wanted})")]
    if smax and total > smax:
        if div and div <= smax:
            return [Check("surface", "Surface", True, 1.0, f"{_fmt(total, 'm²')} divisibles à partir de {_fmt(div, 'm²')} (demande {wanted})")]
        gap = (total - smax) / smax
        return [Check("surface", "Surface", True, _clip(1 - gap / 0.5), f"{_fmt(total, 'm²')} : supérieure de {gap:.0%} au maximum demandé ({wanted})")]
    return [Check("surface", "Surface", True, 1.0, f"{_fmt(total, 'm²')} dans la fourchette demandée ({wanted})")]


def _price_for(req, prop) -> tuple[float | None, float | None, str, str]:
    """Retourne (prix total comparable, prix au m², nature, note)."""
    trans = _g(req, "transaction") or _g(prop, "transaction")
    surface, divided = _effective_surface(req, prop)
    total = _g(prop, "surface_total")
    note = ""
    if trans == "vente" or (trans == "vente_ou_location" and _g(prop, "sale_price")):
        price = _g(prop, "sale_price")
        per = price / total if price and total else None
        if price and divided and per and surface:
            price, note = per * surface, f" (estimation proportionnelle pour {_fmt(surface, 'm²')})"
        return price, per, "prix de vente", note
    rent = _g(prop, "annual_rent")
    per = _g(prop, "rent_per_sqm") or (rent / total if rent and total else None)
    if divided and per and surface:
        return per * surface, per, "loyer annuel", f" (estimation pour {_fmt(surface, 'm²')})"
    if rent is None and per and total:
        return per * total, per, "loyer annuel", " (calculé : loyer/m² × surface)"
    return rent, per, "loyer annuel", note


def _check_budget(req, prop) -> list[Check]:
    bmax, bsqm = _g(req, "budget_max"), _g(req, "budget_per_sqm_max")
    if not bmax and not bsqm:
        return [Check("budget", "Budget", False, message="Aucun budget exprimé.")]
    price, per, kind, note = _price_for(req, prop)
    checks = []
    if bmax:
        if price is None:
            checks.append(Check("budget", "Budget global", True, None, f"{kind.capitalize()} non renseigné."))
        elif price <= bmax:
            checks.append(Check("budget", "Budget global", True, 1.0, f"{kind.capitalize()} {_fmt(price, '€')}{note} ≤ budget {_fmt(bmax, '€')}"))
        else:
            gap = (price - bmax) / bmax
            checks.append(Check("budget", "Budget global", True, _clip(1 - gap / 0.25), f"{kind.capitalize()} {_fmt(price, '€')}{note} dépasse le budget de {gap:.0%} ({_fmt(bmax, '€')})"))
    if bsqm:
        if per is None:
            checks.append(Check("budget", "Budget au m²", True, None, "Prix au m² non calculable."))
        elif per <= bsqm:
            checks.append(Check("budget", "Budget au m²", True, 1.0, f"{_fmt(per, '€/m²')} ≤ {_fmt(bsqm, '€/m²')}"))
        else:
            gap = (per - bsqm) / bsqm
            checks.append(Check("budget", "Budget au m²", True, _clip(1 - gap / 0.25), f"{_fmt(per, '€/m²')} dépasse de {gap:.0%} le maximum ({_fmt(bsqm, '€/m²')})"))
    return checks


def _check_typology(req, prop) -> list[Check]:
    checks = []
    types = [t for t in (_g(req, "property_types") or []) if t]
    ptype = _g(prop, "property_type")
    if not types:
        checks.append(Check("typologie", "Type de bien", False, message="Tous types acceptés."))
    elif not ptype:
        checks.append(Check("typologie", "Type de bien", True, None, "Type de bien non renseigné."))
    elif ptype in types:
        checks.append(Check("typologie", "Type de bien", True, 1.0, f"{TYPE_LABELS.get(ptype, ptype)} recherché"))
    elif any(ptype in fam and set(types) & fam for fam in TYPE_FAMILIES):
        checks.append(Check("typologie", "Type de bien", True, 0.5, f"{TYPE_LABELS.get(ptype, ptype)} : type proche de la recherche"))
    else:
        checks.append(Check("typologie", "Type de bien", True, 0.0, f"{TYPE_LABELS.get(ptype, ptype)} : type non recherché"))

    rt, pt = _g(req, "transaction"), _g(prop, "transaction")
    if not rt or rt == "vente_ou_location":
        checks.append(Check("transaction", "Transaction", False, message="Vente ou location acceptée."))
    elif not pt:
        checks.append(Check("transaction", "Transaction", True, None, "Type de transaction de l'offre non renseigné."))
    elif pt == rt or pt == "vente_ou_location":
        checks.append(Check("transaction", "Transaction", True, 1.0, f"{rt.capitalize()} possible"))
    else:
        checks.append(Check("transaction", "Transaction", True, 0.0, f"Offre en {pt}, demande en {rt}"))
    return checks


def _min_check(key, label, wanted, have, unit, tolerance=0.3) -> Check:
    if wanted in (None, 0, ""):
        return Check(key, label, False)
    if have is None:
        return Check(key, label, True, None, f"{label} non renseigné(e) (minimum demandé {_fmt(wanted, unit)})")
    if have >= wanted:
        return Check(key, label, True, 1.0, f"{label} {_fmt(have, unit)} ≥ {_fmt(wanted, unit)}")
    gap = (wanted - have) / wanted
    return Check(key, label, True, _clip(1 - gap / tolerance), f"{label} {_fmt(have, unit)} < {_fmt(wanted, unit)} demandé(e)s")


def _check_technical(req, prop) -> list[Check]:
    checks = [
        _min_check("hauteur_libre", "Hauteur libre", _g(req, "min_clear_height"), _g(prop, "clear_height"), "m"),
        _min_check("quais", "Quais", _g(req, "min_docks"), _g(prop, "dock_count"), "", tolerance=1.0),
        _min_check("resistance_sol", "Résistance au sol", _g(req, "min_floor_load"), _g(prop, "floor_load"), "t/m²"),
        _min_check("puissance", "Puissance électrique", _g(req, "min_power_kva"), _g(prop, "power_kva"), "kVA"),
        _min_check("parking", "Places de parking", _g(req, "min_parking"), _g(prop, "parking_spaces"), "", tolerance=1.0),
    ]
    if _g(req, "requires_hgv_access"):
        hgv = _g(prop, "hgv_access")
        if hgv is None:
            checks.append(Check("acces_pl", "Accès poids lourds", True, None, "Accès poids lourds non renseigné"))
        else:
            checks.append(Check("acces_pl", "Accès poids lourds", True, 1.0 if hgv else 0.0, "Accès poids lourds " + ("disponible" if hgv else "absent")))
    else:
        checks.append(Check("acces_pl", "Accès poids lourds", False))
    return checks


def _check_availability(req, prop, today: date | None = None) -> list[Check]:
    wanted = _g(req, "desired_date")
    if not wanted:
        return [Check("disponibilite", "Disponibilité", False, message="Pas de date souhaitée.")]
    if isinstance(wanted, str):
        wanted = date.fromisoformat(wanted)
    avail = _g(prop, "available_from")
    if isinstance(avail, str):
        avail = date.fromisoformat(avail)
    if avail is None:
        note = (_g(prop, "availability_note") or "").lower()
        if "immédiat" in note or "immediat" in note:
            avail = today or date.today()
        else:
            return [Check("disponibilite", "Disponibilité", True, None, "Date de disponibilité non renseignée")]
    if avail <= wanted:
        return [Check("disponibilite", "Disponibilité", True, 1.0, f"Disponible le {avail:%d/%m/%Y} (souhaité {wanted:%d/%m/%Y})")]
    delay = (avail - wanted).days
    return [Check("disponibilite", "Disponibilité", True, _clip(1 - delay / 180), f"Disponible {delay} jours après la date souhaitée")]


EVALUATORS = {
    "localisation": _check_location,
    "surface": _check_surface,
    "budget": _check_budget,
    "typologie": _check_typology,
    "technique": _check_technical,
    "disponibilite": _check_availability,
}


def evaluate(req, prop, weights: dict[str, float] | None = None) -> dict:
    """Calcule le score explicable d'un couple (demande, offre)."""
    w = normalize_weights(weights)
    imperatives = set(_g(req, "imperatives") or [])
    groups: list[GroupResult] = []
    eliminated_by: list[str] = []
    missing: list[str] = []
    satisfied: list[str] = []
    gaps: list[str] = []

    for gkey, fn in EVALUATORS.items():
        checks = fn(req, prop)
        g = GroupResult(gkey, GROUP_LABELS[gkey], round(w[gkey], 2))
        constrained = [c for c in checks if c.constrained]
        if not constrained:
            g.earned = g.potential = w[gkey]
        else:
            g.earned = w[gkey] * sum(c.ratio or 0.0 for c in constrained) / len(constrained)
            g.potential = w[gkey] * sum(1.0 if c.ratio is None else c.ratio for c in constrained) / len(constrained)
        for c in checks:
            imp = c.key in imperatives
            d = asdict(c) | {"status": c.status, "imperative": imp}
            g.checks.append(d)
            if c.status == "manquant":
                missing.append(c.message or c.label)
            elif c.status == "ok":
                satisfied.append(c.message or c.label)
            elif c.status in ("partiel", "ecart"):
                gaps.append(c.message or c.label)
                if imp:
                    eliminated_by.append(f"{c.label} (impératif) : {c.message}")
        groups.append(g)

    score = round(sum(g.earned for g in groups), 1)
    potential = round(sum(g.potential for g in groups), 1)
    return {
        "score": score,
        "score_potential": potential,
        "eliminated": bool(eliminated_by),
        "eliminated_by": eliminated_by,
        "satisfied": satisfied,
        "gaps": gaps,
        "missing": missing,
        "groups": [asdict(g) | {"earned": round(g.earned, 1), "potential": round(g.potential, 1)} for g in groups],
    }
