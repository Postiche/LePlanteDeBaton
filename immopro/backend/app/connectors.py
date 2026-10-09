"""Connecteurs de recherche externe : BureauxLocaux et Geolocaux.

État vérifié lors du développement : aucune API publique officielle documentée n'a pu être
identifiée ni testée pour ces deux plateformes, et leurs conditions d'utilisation n'autorisent
pas a priori l'extraction automatisée. En conséquence :

- aucune requête automatisée n'est envoyée vers ces sites (pas de scraping, pas de
  contournement de captcha, d'authentification ou de limitation) ;
- l'application ne fabrique pas d'URL de recherche paramétrée dont la syntaxe n'a pas été
  vérifiée : elle propose le lien vers la plateforme + un récapitulatif des critères à saisir.
  Si l'utilisateur a lui-même vérifié la syntaxe d'URL d'une recherche sur la plateforme, il
  peut l'enregistrer comme modèle dans les Paramètres (variables {ville}, {code_postal},
  {departement}, {surface_min}, {surface_max}, {budget_max}, {transaction}) ;
- les annonces trouvées par l'utilisateur sont importées manuellement (URL + champs), puis
  validées avant enregistrement en base ;
- un connecteur « API » pourra être branché si la plateforme fournit un accès officiel
  (partenariat, flux autorisé) : voir `fetch_listings`.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from .matching import TYPE_LABELS


class ConnectorNotConfigured(Exception):
    pass


@dataclass
class Connector:
    key: str
    name: str
    base_url: str
    setting_key: str

    def supported_template_vars(self) -> list[str]:
        return ["ville", "code_postal", "departement", "surface_min", "surface_max", "budget_max", "transaction", "type"]

    def criteria_summary(self, req) -> list[dict]:
        """Critères de la demande à reporter manuellement sur la plateforme."""
        items = []
        if req.transaction:
            items.append({"label": "Transaction", "value": {"vente": "Achat", "location": "Location", "vente_ou_location": "Achat ou location"}[req.transaction]})
        if req.property_types:
            items.append({"label": "Type de bien", "value": ", ".join(TYPE_LABELS.get(t, t) for t in req.property_types)})
        loc = (req.cities or []) + (req.postal_codes or []) + [f"Dépt {d}" for d in (req.departments or [])] + (req.regions or [])
        if loc:
            items.append({"label": "Localisation", "value": ", ".join(loc)})
        if req.center_label and req.radius_km:
            items.append({"label": "Rayon", "value": f"{req.radius_km:.0f} km autour de {req.center_label}"})
        if req.surface_min or req.surface_max:
            items.append({"label": "Surface", "value": f"{req.surface_min or '—'} à {req.surface_max or '—'} m²"})
        if req.budget_max:
            items.append({"label": "Budget max", "value": f"{req.budget_max:,.0f} €".replace(",", " ")})
        return items

    def search_link(self, req, template: str | None) -> dict:
        """Retourne un lien de recherche.

        Sans modèle vérifié par l'utilisateur, seul le lien vers la page d'accueil de la
        plateforme est proposé (aucun paramètre n'est inventé).
        """
        if not template:
            return {
                "url": self.base_url,
                "parametrized": False,
                "note": "Lien vers la plateforme : reportez les critères ci-dessous dans son moteur de recherche. "
                "Vous pouvez enregistrer un modèle d'URL vérifié dans Paramètres › Connecteurs.",
            }
        values = {
            "ville": (req.cities or [""])[0],
            "code_postal": (req.postal_codes or [""])[0],
            "departement": (req.departments or [""])[0],
            "surface_min": f"{req.surface_min:.0f}" if req.surface_min else "",
            "surface_max": f"{req.surface_max:.0f}" if req.surface_max else "",
            "budget_max": f"{req.budget_max:.0f}" if req.budget_max else "",
            "transaction": req.transaction or "",
            "type": (req.property_types or [""])[0],
        }
        url = template
        used = []
        for k, v in values.items():
            token = "{" + k + "}"
            if token in url:
                url = url.replace(token, quote(str(v), safe=""))
                if v:
                    used.append(k)
        if not (url == self.base_url or url.startswith(self.base_url + "/")):
            return {"url": self.base_url, "parametrized": False, "note": "Modèle d'URL ignoré : il ne pointe pas vers " + self.base_url}
        return {
            "url": url,
            "parametrized": True,
            "applied": used,
            "note": "Modèle d'URL défini par l'utilisateur dans les Paramètres. Critères appliqués : " + (", ".join(used) or "aucun"),
        }

    def fetch_listings(self, req) -> list[dict]:
        raise ConnectorNotConfigured(
            f"Recherche automatique {self.name} non disponible : aucune API officielle ni flux autorisé n'est configuré."
        )


CONNECTORS: dict[str, Connector] = {
    "bureauxlocaux": Connector("bureauxlocaux", "BureauxLocaux", "https://www.bureauxlocaux.com", "connector_bureauxlocaux_search_template"),
    "geolocaux": Connector("geolocaux", "Geolocaux", "https://www.geolocaux.com", "connector_geolocaux_search_template"),
}


def source_from_url(url: str) -> str:
    u = (url or "").lower()
    if "bureauxlocaux.com" in u:
        return "bureauxlocaux"
    if "geolocaux.com" in u:
        return "geolocaux"
    return "autre"
