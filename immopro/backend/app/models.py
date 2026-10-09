"""Modèle de données.

Conventions :
- toutes les dates sont stockées en UTC « naïf » (voir `utcnow`) ;
- `is_demo` sépare strictement les données de démonstration des données réelles ;
- une valeur NULL signifie « information non renseignée », jamais « zéro » ni « non ».
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Comptes, sessions, sécurité
# ---------------------------------------------------------------------------

ROLES = ("admin", "collaborateur", "lecteur")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="collaborateur")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    email_signature: Mapped[str | None] = mapped_column(Text)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship()


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(Integer)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    username: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JSON)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------

COMPANY_KINDS = ("client", "proprietaire", "agence", "partenaire", "autre")
CONTACT_KINDS = ("client", "proprietaire", "agence", "commercial", "partenaire", "annonceur", "autre")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="client")
    siren: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(300))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), default="client", index=True)
    civility: Mapped[str | None] = mapped_column(String(10))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    job_title: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    mobile: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(300))
    # RGPD : provenance du contact, base légale, opposition à la prospection
    origin: Mapped[str | None] = mapped_column(String(200))
    legal_basis: Mapped[str | None] = mapped_column(String(60))
    opposed_to_prospecting: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public_listing_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    company: Mapped[Company | None] = relationship()


# ---------------------------------------------------------------------------
# Offres immobilières
# ---------------------------------------------------------------------------

PROPERTY_TYPES = (
    "entrepot",
    "plateforme_logistique",
    "local_activite",
    "batiment_industriel",
    "bureaux",
    "terrain",
    "commerce",
    "autre",
)
TRANSACTIONS = ("vente", "location", "vente_ou_location")
PROPERTY_STATUSES = ("active", "sous_offre", "vendue_louee", "archivee")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(60), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    property_type: Mapped[str | None] = mapped_column(String(40), index=True)
    transaction: Mapped[str | None] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    address: Mapped[str | None] = mapped_column(String(300))
    postal_code: Mapped[str | None] = mapped_column(String(10), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    department: Mapped[str | None] = mapped_column(String(3), index=True)
    region: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geocode_status: Mapped[str | None] = mapped_column(String(20))  # manuel | auto | echec | None

    surface_total: Mapped[float | None] = mapped_column(Float)
    surface_divisible_min: Mapped[float | None] = mapped_column(Float)
    surface_offices: Mapped[float | None] = mapped_column(Float)
    surface_storage: Mapped[float | None] = mapped_column(Float)
    land_area: Mapped[float | None] = mapped_column(Float)
    clear_height: Mapped[float | None] = mapped_column(Float)
    dock_count: Mapped[int | None] = mapped_column(Integer)
    sectional_doors: Mapped[int | None] = mapped_column(Integer)
    hgv_access: Mapped[bool | None] = mapped_column(Boolean)
    floor_load: Mapped[float | None] = mapped_column(Float)  # t/m²
    power_kva: Mapped[float | None] = mapped_column(Float)
    parking_spaces: Mapped[int | None] = mapped_column(Integer)
    condition: Mapped[str | None] = mapped_column(String(60))
    available_from: Mapped[date | None] = mapped_column(Date)
    availability_note: Mapped[str | None] = mapped_column(String(200))

    sale_price: Mapped[float | None] = mapped_column(Float)
    annual_rent: Mapped[float | None] = mapped_column(Float)
    rent_per_sqm: Mapped[float | None] = mapped_column(Float)
    charges: Mapped[float | None] = mapped_column(Float)
    property_tax: Mapped[float | None] = mapped_column(Float)
    fees: Mapped[str | None] = mapped_column(String(200))

    description: Mapped[str | None] = mapped_column(Text)
    owner_contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    agency_contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    sales_contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Provenance (obligatoire pour la traçabilité et la détection de doublons)
    source_kind: Mapped[str] = mapped_column(String(20), default="manuel")  # manuel | import | externe
    source_name: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(600), index=True)
    source_ref: Mapped[str | None] = mapped_column(String(120))
    source_consulted_at: Mapped[datetime | None] = mapped_column(DateTime)

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner_contact: Mapped[Contact | None] = relationship(foreign_keys=[owner_contact_id])
    agency_contact: Mapped[Contact | None] = relationship(foreign_keys=[agency_contact_id])
    sales_contact: Mapped[Contact | None] = relationship(foreign_keys=[sales_contact_id])


# ---------------------------------------------------------------------------
# Demandes clients
# ---------------------------------------------------------------------------

REQUEST_STATUSES = ("active", "en_pause", "satisfaite", "abandonnee")
PRIORITIES = ("basse", "normale", "haute", "urgente")
# Critères pouvant être déclarés impératifs (éliminatoires)
IMPERATIVE_KEYS = (
    "localisation",
    "surface",
    "budget",
    "typologie",
    "transaction",
    "hauteur_libre",
    "quais",
    "acces_pl",
    "resistance_sol",
    "puissance",
    "parking",
    "disponibilite",
)


class ClientRequest(Base):
    __tablename__ = "client_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(60), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    # Champs libres si le client n'est pas (encore) dans le CRM
    client_name: Mapped[str | None] = mapped_column(String(200))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))

    property_types: Mapped[list | None] = mapped_column(JSON)
    transaction: Mapped[str | None] = mapped_column(String(20))
    cities: Mapped[list | None] = mapped_column(JSON)
    postal_codes: Mapped[list | None] = mapped_column(JSON)
    departments: Mapped[list | None] = mapped_column(JSON)
    regions: Mapped[list | None] = mapped_column(JSON)
    center_label: Mapped[str | None] = mapped_column(String(200))
    center_latitude: Mapped[float | None] = mapped_column(Float)
    center_longitude: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[float | None] = mapped_column(Float)

    surface_min: Mapped[float | None] = mapped_column(Float)
    surface_max: Mapped[float | None] = mapped_column(Float)
    budget_max: Mapped[float | None] = mapped_column(Float)  # prix (vente) ou loyer annuel HT HC (location)
    budget_per_sqm_max: Mapped[float | None] = mapped_column(Float)

    min_clear_height: Mapped[float | None] = mapped_column(Float)
    min_docks: Mapped[int | None] = mapped_column(Integer)
    requires_hgv_access: Mapped[bool | None] = mapped_column(Boolean)
    min_floor_load: Mapped[float | None] = mapped_column(Float)
    min_power_kva: Mapped[float | None] = mapped_column(Float)
    min_parking: Mapped[int | None] = mapped_column(Integer)
    other_constraints: Mapped[str | None] = mapped_column(Text)

    desired_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(20), default="normale")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    imperatives: Mapped[list | None] = mapped_column(JSON)  # sous-ensemble de IMPERATIVE_KEYS
    comments: Mapped[str | None] = mapped_column(Text)
    request_date: Mapped[date | None] = mapped_column(Date)

    source_kind: Mapped[str] = mapped_column(String(20), default="manuel")
    source_name: Mapped[str | None] = mapped_column(String(200))
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    contact: Mapped[Contact | None] = relationship()
    company: Mapped[Company | None] = relationship()


# ---------------------------------------------------------------------------
# Correspondances, suivi commercial
# ---------------------------------------------------------------------------

PIPELINE_STATUSES = (
    "a_contacter",
    "email_prepare",
    "contacte",
    "en_attente",
    "visite_proposee",
    "visite_confirmee",
    "visite_effectuee",
    "negociation",
    "sans_suite",
)
PIPELINE_LABELS = {
    "a_contacter": "À contacter",
    "email_prepare": "Email préparé",
    "contacte": "Contacté",
    "en_attente": "En attente de réponse",
    "visite_proposee": "Visite proposée",
    "visite_confirmee": "Visite confirmée",
    "visite_effectuee": "Visite effectuée",
    "negociation": "Négociation",
    "sans_suite": "Sans suite",
}


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("request_id", "property_id", name="uq_match_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("client_requests.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float, index=True)
    score_potential: Mapped[float] = mapped_column(Float)
    eliminated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="a_contacter", index=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    request: Mapped[ClientRequest] = relationship()
    property: Mapped[Property] = relationship()


INTERACTION_KINDS = ("appel", "email_prepare", "email_envoye", "rendez_vous", "visite", "note", "relance", "compte_rendu", "statut")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), default="note")
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    subject: Mapped[str | None] = mapped_column(String(250))
    content: Mapped[str | None] = mapped_column(Text)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("client_requests.id", ondelete="SET NULL"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="SET NULL"))
    remind_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int | None] = mapped_column(Integer)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


VISIT_STATUSES = ("proposee", "confirmee", "effectuee", "annulee")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("client_requests.id", ondelete="SET NULL"))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="SET NULL"))
    proposed_slots: Mapped[list | None] = mapped_column(JSON)  # liste ISO datetimes
    confirmed_slot: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="proposee", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    report: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    user_id: Mapped[int | None] = mapped_column(Integer)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    property: Mapped[Property] = relationship()
    contact: Mapped[Contact | None] = relationship()
    request: Mapped[ClientRequest | None] = relationship()


EMAIL_STATUSES = ("brouillon", "ouvert_messagerie", "brouillon_outlook", "eml_telecharge", "envoye_confirme")


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    template: Mapped[str] = mapped_column(String(40))
    to_email: Mapped[str | None] = mapped_column(String(300))
    cc: Mapped[str | None] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="brouillon")
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    request_id: Mapped[int | None] = mapped_column(ForeignKey("client_requests.id", ondelete="SET NULL"))
    property_ids: Mapped[list | None] = mapped_column(JSON)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="SET NULL"))
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    sent_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    user_id: Mapped[int | None] = mapped_column(Integer)


# ---------------------------------------------------------------------------
# Fichiers, imports, recherches externes
# ---------------------------------------------------------------------------


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(30), index=True)  # property | request | contact | company | import | visit
    owner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="document")  # photo | document
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    caption: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(20))  # property | request
    source_name: Mapped[str] = mapped_column(String(255))
    file_kind: Mapped[str] = mapped_column(String(20))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="a_valider")  # a_valider | valide | annule
    rows: Mapped[list | None] = mapped_column(JSON)
    warnings: Mapped[list | None] = mapped_column(JSON)
    created_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)


class ExternalSearch(Base):
    __tablename__ = "external_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("client_requests.id", ondelete="SET NULL"), index=True)
    criteria: Mapped[dict | None] = mapped_column(JSON)
    results_summary: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer)


class ExternalListing(Base):
    """Annonce externe saisie/importée manuellement ou issue d'un flux autorisé."""

    __tablename__ = "external_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)  # bureauxlocaux | geolocaux | autre
    url: Mapped[str] = mapped_column(String(600), index=True)
    title: Mapped[str | None] = mapped_column(String(300))
    property_type: Mapped[str | None] = mapped_column(String(40))
    transaction: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    surface: Mapped[float | None] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float)
    price_kind: Mapped[str | None] = mapped_column(String(20))  # vente | loyer_annuel | loyer_m2_an
    features: Mapped[str | None] = mapped_column(Text)
    advertiser_name: Mapped[str | None] = mapped_column(String(200))
    advertiser_phone: Mapped[str | None] = mapped_column(String(40))
    advertiser_email: Mapped[str | None] = mapped_column(String(200))
    consulted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    still_online: Mapped[bool | None] = mapped_column(Boolean)
    search_id: Mapped[int | None] = mapped_column(ForeignKey("external_searches.id", ondelete="SET NULL"))
    imported_property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(Integer)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
