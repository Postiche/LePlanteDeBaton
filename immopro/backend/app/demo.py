"""Données de démonstration — FICTIVES et marquées `is_demo=True`.

Elles ne doivent jamais être utilisées comme données réelles. Les communes existent, mais les
biens, sociétés, personnes, emails (domaine réservé .test) et numéros (série fictive) sont inventés.
Les coordonnées GPS sont approximatives (centre de commune).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import (
    ClientRequest,
    Company,
    Contact,
    Document,
    EmailDraft,
    ExternalListing,
    Interaction,
    Match,
    Property,
    Visit,
    utcnow,
)
from .services import fill_property_geo, recompute_for_request

PROPS = [
    dict(reference="DEMO-L001", title="[DÉMO] Plateforme logistique XXL", property_type="plateforme_logistique", transaction="location", city="Saint-Priest", postal_code="69800", latitude=45.6967, longitude=4.9442, surface_total=24000, surface_divisible_min=6000, surface_offices=800, surface_storage=23200, clear_height=12, dock_count=24, sectional_doors=4, hgv_access=True, floor_load=5, power_kva=400, parking_spaces=80, condition="Neuf", annual_rent=1_200_000, rent_per_sqm=50, charges=96000, property_tax=110000, fees="Selon barème", availability_note="Disponibilité immédiate"),
    dict(reference="DEMO-L002", title="[DÉMO] Entrepôt avec quais", property_type="entrepot", transaction="location", city="Villepinte", postal_code="93420", latitude=48.962, longitude=2.533, surface_total=8500, surface_offices=450, surface_storage=8050, clear_height=10, dock_count=8, sectional_doors=2, hgv_access=True, floor_load=3, power_kva=250, parking_spaces=35, condition="Bon état", annual_rent=595000, rent_per_sqm=70, available_from=date.today() + timedelta(days=60)),
    dict(reference="DEMO-V003", title="[DÉMO] Local d'activité avec bureaux", property_type="local_activite", transaction="vente", city="Gonesse", postal_code="95500", latitude=48.986, longitude=2.449, surface_total=2200, surface_offices=400, surface_storage=1800, clear_height=7, dock_count=1, sectional_doors=3, hgv_access=True, power_kva=120, parking_spaces=20, condition="Rénové", sale_price=2_350_000, available_from=date.today() + timedelta(days=30)),
    dict(reference="DEMO-L004", title="[DÉMO] Bâtiment industriel embranché", property_type="batiment_industriel", transaction="vente_ou_location", city="Lesquin", postal_code="59810", latitude=50.589, longitude=3.111, surface_total=12000, surface_offices=1000, clear_height=9, dock_count=6, hgv_access=True, floor_load=4, power_kva=1000, parking_spaces=60, sale_price=7_900_000, annual_rent=660000, condition="Bon état"),
    dict(reference="DEMO-L005", title="[DÉMO] Bureaux en parc tertiaire", property_type="bureaux", transaction="location", city="Mérignac", postal_code="33700", latitude=44.842, longitude=-0.645, surface_total=1350, surface_divisible_min=300, surface_offices=1350, parking_spaces=45, condition="Neuf", annual_rent=243000, rent_per_sqm=180, availability_note="Disponibilité immédiate"),
    dict(reference="DEMO-V006", title="[DÉMO] Terrain viabilisé zone logistique", property_type="terrain", transaction="vente", city="Saran", postal_code="45770", latitude=47.95, longitude=1.876, surface_total=35000, land_area=35000, sale_price=2_800_000),
    dict(reference="DEMO-L007", title="[DÉMO] Entrepôt — informations partielles", property_type="entrepot", transaction="location", city="Vitrolles", postal_code="13127", surface_total=5200, annual_rent=390000, description="Fiche volontairement incomplète pour illustrer la gestion des informations manquantes (hauteur, quais, géolocalisation)."),
    dict(reference="DEMO-L008", title="[DÉMO] Messagerie cross-dock", property_type="plateforme_logistique", transaction="location", city="Colomiers", postal_code="31770", latitude=43.611, longitude=1.335, surface_total=6400, clear_height=8, dock_count=30, hgv_access=True, parking_spaces=120, annual_rent=448000, available_from=date.today() + timedelta(days=150)),
]


def seed_demo(db: Session) -> str:
    if db.scalar(select(Property).where(Property.is_demo.is_(True)).limit(1)):
        return "Des données de démonstration existent déjà (utilisez purge-demo pour les supprimer)."
    c_agence = Company(name="[DÉMO] Agence Exemple Immobilier", kind="agence", city="Lyon", phone="01 00 00 00 01", email="contact@agence-exemple.test", is_demo=True)
    c_client1 = Company(name="[DÉMO] Logistique Fictive SAS", kind="client", city="Lyon", is_demo=True)
    c_client2 = Company(name="[DÉMO] Industries Imaginaires", kind="client", city="Lille", is_demo=True)
    c_owner = Company(name="[DÉMO] Foncière Démonstration", kind="proprietaire", is_demo=True)
    db.add_all([c_agence, c_client1, c_client2, c_owner])
    db.flush()
    sales = Contact(kind="commercial", civility="Mme", first_name="Claire", last_name="Exemple", company_id=c_agence.id, job_title="Consultante logistique", email="claire.exemple@agence-exemple.test", phone="01 00 00 00 02", origin="Donnée de démonstration", is_demo=True)
    owner = Contact(kind="proprietaire", civility="M.", first_name="Paul", last_name="Fictif", company_id=c_owner.id, email="paul.fictif@fonciere-demo.test", origin="Donnée de démonstration", is_demo=True)
    cl1 = Contact(kind="client", civility="M.", first_name="Marc", last_name="Démo", company_id=c_client1.id, job_title="Directeur supply chain", email="marc.demo@logistique-fictive.test", phone="06 00 00 00 03", origin="Donnée de démonstration", legal_basis="interet_legitime", is_demo=True)
    cl2 = Contact(kind="client", civility="Mme", first_name="Sophie", last_name="Test", company_id=c_client2.id, job_title="Responsable immobilier", email="sophie.test@industries-imaginaires.test", phone="06 00 00 00 04", origin="Donnée de démonstration", legal_basis="interet_legitime", opposed_to_prospecting=True, is_demo=True)
    db.add_all([sales, owner, cl1, cl2])
    db.flush()
    for i, data in enumerate(PROPS):
        p = Property(**data, is_demo=True, source_kind="manuel", source_name="Démonstration", status="active", sales_contact_id=sales.id, agency_contact_id=sales.id, owner_contact_id=owner.id)
        p.created_at = utcnow() - timedelta(days=3 * i)
        fill_property_geo(p, try_geocode=False)
        db.add(p)
    r1 = ClientRequest(
        reference="DEMO-D001", title="[DÉMO] Entrepôt région lyonnaise", contact_id=cl1.id, company_id=c_client1.id, client_name=c_client1.name,
        property_types=["entrepot", "plateforme_logistique"], transaction="location", departments=["69", "38"], center_label="Lyon",
        center_latitude=45.764, center_longitude=4.8357, radius_km=40, surface_min=5000, surface_max=12000, budget_max=700000,
        min_clear_height=9, min_docks=6, requires_hgv_access=True, desired_date=date.today() + timedelta(days=90), priority="haute",
        imperatives=["transaction", "acces_pl"], is_demo=True, request_date=date.today(),
    )
    r2 = ClientRequest(
        reference="DEMO-D002", title="[DÉMO] Bâtiment industriel Hauts-de-France", contact_id=cl2.id, company_id=c_client2.id, client_name=c_client2.name,
        property_types=["batiment_industriel", "local_activite"], transaction="vente", regions=["Hauts-de-France"], surface_min=8000, surface_max=15000,
        budget_max=8_500_000, min_power_kva=800, priority="normale", imperatives=["localisation"], is_demo=True, request_date=date.today(),
    )
    r3 = ClientRequest(
        reference="DEMO-D003", title="[DÉMO] Entrepôt Île-de-France Nord", client_name="[DÉMO] Prospect sans fiche CRM", contact_name="M. Exemple",
        email="prospect@exemple.test", property_types=["entrepot", "local_activite"], transaction="location", departments=["93", "95", "77"],
        surface_min=2000, surface_max=9000, budget_max=650000, min_clear_height=8, priority="normale", is_demo=True,
    )
    db.add_all([r1, r2, r3])
    db.commit()
    for r in (r1, r2, r3):
        recompute_for_request(db, r)
    m = db.scalar(select(Match).where(Match.request_id == r1.id).order_by(Match.score.desc()))
    db.add(Interaction(kind="appel", subject="[DÉMO] Qualification du besoin", content="Échange fictif de démonstration.", contact_id=cl1.id, request_id=r1.id, is_demo=True, at=utcnow() - timedelta(days=2)))
    db.add(Interaction(kind="relance", subject="[DÉMO] Relancer le client sur la sélection", contact_id=cl1.id, request_id=r1.id, remind_at=utcnow() + timedelta(hours=4), is_demo=True))
    if m:
        db.add(Interaction(kind="note", subject="[DÉMO] Bien pertinent repéré", property_id=m.property_id, request_id=r1.id, match_id=m.id, contact_id=cl1.id, is_demo=True))
    db.commit()
    return "Données de démonstration créées (8 offres, 3 demandes, contacts fictifs)."


def purge_demo(db: Session) -> str:
    demo_props = [p.id for p in db.scalars(select(Property).where(Property.is_demo.is_(True)))]
    demo_reqs = [r.id for r in db.scalars(select(ClientRequest).where(ClientRequest.is_demo.is_(True)))]
    db.execute(delete(Match).where(Match.property_id.in_(demo_props) | Match.request_id.in_(demo_reqs)))
    db.execute(delete(Interaction).where(Interaction.is_demo.is_(True)))
    db.execute(delete(Visit).where(Visit.is_demo.is_(True)))
    db.execute(delete(EmailDraft).where(EmailDraft.request_id.in_(demo_reqs)))
    db.execute(delete(ExternalListing).where(ExternalListing.is_demo.is_(True)))
    db.execute(delete(Document).where(Document.is_demo.is_(True)))
    db.execute(delete(Property).where(Property.is_demo.is_(True)))
    db.execute(delete(ClientRequest).where(ClientRequest.is_demo.is_(True)))
    db.execute(delete(Contact).where(Contact.is_demo.is_(True)))
    db.execute(delete(Company).where(Company.is_demo.is_(True)))
    db.commit()
    return f"Données de démonstration supprimées ({len(demo_props)} offres, {len(demo_reqs)} demandes)."
