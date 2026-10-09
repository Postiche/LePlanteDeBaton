from __future__ import annotations

from datetime import date, datetime

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from .models import (
    COMPANY_KINDS,
    CONTACT_KINDS,
    IMPERATIVE_KEYS,
    INTERACTION_KINDS,
    PIPELINE_STATUSES,
    PRIORITIES,
    PROPERTY_STATUSES,
    PROPERTY_TYPES,
    REQUEST_STATUSES,
    ROLES,
    TRANSACTIONS,
    VISIT_STATUSES,
)


import re

_EMAIL_RE = re.compile(r"^[^@\s<>,;]{1,64}@[^@\s<>,;]{1,255}\.[A-Za-z0-9-]{2,63}$")


def _check_email(v: str) -> str:
    v = v.strip()
    if not _EMAIL_RE.match(v):
        raise ValueError("adresse email invalide")
    return v


# Validation syntaxique simple (les domaines réservés .test/.example sont acceptés pour la démo)
EmailStr = Annotated[str, AfterValidator(_check_email)]


def _in(value, allowed, label):
    if value in (None, ""):
        return None
    if value not in allowed:
        raise ValueError(f"{label} invalide : {value}")
    return value


class Loose(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class LoginIn(Loose):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordIn(Loose):
    current_password: str
    new_password: str


class ResetIn(Loose):
    token: str = Field(min_length=10, max_length=200)
    new_password: str


class UserIn(Loose):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._@-]+$")
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    role: str = "collaborateur"
    password: str | None = None

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        return _in(v, ROLES, "Rôle")


class UserUpdate(Loose):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
    email_signature: str | None = None

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        return _in(v, ROLES, "Rôle")


class ProfileUpdate(Loose):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    email_signature: str | None = Field(None, max_length=2000)


class PropertyIn(Loose):
    reference: str | None = Field(None, max_length=60)
    title: str | None = Field(None, max_length=200)
    property_type: str | None = None
    transaction: str | None = None
    status: str | None = None
    address: str | None = Field(None, max_length=300)
    postal_code: str | None = Field(None, pattern=r"^(\d{5})?$")
    city: str | None = Field(None, max_length=120)
    department: str | None = Field(None, max_length=3)
    region: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    surface_total: float | None = Field(None, ge=0)
    surface_divisible_min: float | None = Field(None, ge=0)
    surface_offices: float | None = Field(None, ge=0)
    surface_storage: float | None = Field(None, ge=0)
    land_area: float | None = Field(None, ge=0)
    clear_height: float | None = Field(None, ge=0, le=100)
    dock_count: int | None = Field(None, ge=0)
    sectional_doors: int | None = Field(None, ge=0)
    hgv_access: bool | None = None
    floor_load: float | None = Field(None, ge=0)
    power_kva: float | None = Field(None, ge=0)
    parking_spaces: int | None = Field(None, ge=0)
    condition: str | None = None
    available_from: date | None = None
    availability_note: str | None = None
    sale_price: float | None = Field(None, ge=0)
    annual_rent: float | None = Field(None, ge=0)
    rent_per_sqm: float | None = Field(None, ge=0)
    charges: float | None = Field(None, ge=0)
    property_tax: float | None = Field(None, ge=0)
    fees: str | None = None
    description: str | None = Field(None, max_length=20000)
    owner_contact_id: int | None = None
    agency_contact_id: int | None = None
    sales_contact_id: int | None = None
    assigned_user_id: int | None = None
    source_kind: str | None = None
    source_name: str | None = None
    source_url: str | None = Field(None, max_length=600)
    source_ref: str | None = None

    @field_validator("property_type")
    @classmethod
    def _t(cls, v):
        return _in(v, PROPERTY_TYPES, "Type de bien")

    @field_validator("transaction")
    @classmethod
    def _tr(cls, v):
        return _in(v, TRANSACTIONS, "Transaction")

    @field_validator("status")
    @classmethod
    def _st(cls, v):
        return _in(v, PROPERTY_STATUSES, "Statut")

    @field_validator("source_url")
    @classmethod
    def _url(cls, v):
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("L'URL source doit commencer par http(s)://")
        return v or None

    @field_validator("postal_code", mode="before")
    @classmethod
    def _cp(cls, v):
        return (str(v).strip() or None) if v is not None else None


class RequestIn(Loose):
    reference: str | None = None
    title: str | None = Field(None, max_length=200)
    contact_id: int | None = None
    company_id: int | None = None
    client_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    property_types: list[str] | None = None
    transaction: str | None = None
    cities: list[str] | None = None
    postal_codes: list[str] | None = None
    departments: list[str] | None = None
    regions: list[str] | None = None
    center_label: str | None = None
    center_latitude: float | None = Field(None, ge=-90, le=90)
    center_longitude: float | None = Field(None, ge=-180, le=180)
    radius_km: float | None = Field(None, ge=0, le=1000)
    surface_min: float | None = Field(None, ge=0)
    surface_max: float | None = Field(None, ge=0)
    budget_max: float | None = Field(None, ge=0)
    budget_per_sqm_max: float | None = Field(None, ge=0)
    min_clear_height: float | None = Field(None, ge=0)
    min_docks: int | None = Field(None, ge=0)
    requires_hgv_access: bool | None = None
    min_floor_load: float | None = Field(None, ge=0)
    min_power_kva: float | None = Field(None, ge=0)
    min_parking: int | None = Field(None, ge=0)
    other_constraints: str | None = None
    desired_date: date | None = None
    priority: str | None = None
    status: str | None = None
    imperatives: list[str] | None = None
    comments: str | None = Field(None, max_length=20000)
    request_date: date | None = None
    assigned_user_id: int | None = None
    source_kind: str | None = None
    source_name: str | None = None

    @field_validator("property_types")
    @classmethod
    def _types(cls, v):
        for t in v or []:
            _in(t, PROPERTY_TYPES, "Type de bien")
        return v

    @field_validator("imperatives")
    @classmethod
    def _imp(cls, v):
        for t in v or []:
            _in(t, IMPERATIVE_KEYS, "Critère impératif")
        return v

    @field_validator("transaction")
    @classmethod
    def _tr(cls, v):
        return _in(v, TRANSACTIONS, "Transaction")

    @field_validator("priority")
    @classmethod
    def _pr(cls, v):
        return _in(v, PRIORITIES, "Priorité")

    @field_validator("status")
    @classmethod
    def _st(cls, v):
        return _in(v, REQUEST_STATUSES, "Statut")

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return v or None

    @field_validator("departments")
    @classmethod
    def _depts(cls, v):
        return [d.strip().upper().zfill(2) if d.strip().isdigit() else d.strip().upper() for d in v or [] if d.strip()]


class CompanyIn(Loose):
    name: str = Field(min_length=1, max_length=200)
    kind: str = "client"
    siren: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    website: str | None = None
    notes: str | None = None

    @field_validator("kind")
    @classmethod
    def _k(cls, v):
        return _in(v, COMPANY_KINDS, "Catégorie")

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return v or None


class ContactIn(Loose):
    kind: str = "client"
    civility: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_id: int | None = None
    job_title: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    mobile: str | None = None
    address: str | None = None
    origin: str | None = None
    legal_basis: str | None = None
    opposed_to_prospecting: bool = False
    is_public_listing_contact: bool = False
    notes: str | None = None

    @field_validator("kind")
    @classmethod
    def _k(cls, v):
        return _in(v, CONTACT_KINDS, "Catégorie")

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return v or None


from datetime import timezone as _tz


def to_utc_naive(v):
    """Horodatages : convertis en UTC sans fuseau (convention de stockage)."""
    if isinstance(v, datetime) and v.tzinfo is not None:
        return v.astimezone(_tz.utc).replace(tzinfo=None)
    return v


def wall_clock(v):
    """Créneaux de visite : heure locale « murale » conservée telle que saisie."""
    if isinstance(v, datetime) and v.tzinfo is not None:
        return v.replace(tzinfo=None)
    return v


class InteractionIn(Loose):
    kind: str = "note"
    at: datetime | None = None
    subject: str | None = None
    content: str | None = None
    contact_id: int | None = None
    company_id: int | None = None
    property_id: int | None = None
    request_id: int | None = None
    match_id: int | None = None
    remind_at: datetime | None = None
    done: bool = False

    @field_validator("kind")
    @classmethod
    def _k(cls, v):
        return _in(v, INTERACTION_KINDS, "Type d'interaction")

    @field_validator("at", "remind_at")
    @classmethod
    def _utc(cls, v):
        return to_utc_naive(v)


class MatchUpdate(Loose):
    status: str | None = None
    dismissed: bool | None = None
    note: str | None = None

    @field_validator("status")
    @classmethod
    def _s(cls, v):
        return _in(v, PIPELINE_STATUSES, "Statut")


class VisitIn(Loose):
    property_id: int
    request_id: int | None = None
    contact_id: int | None = None
    match_id: int | None = None
    proposed_slots: list[datetime] = Field(default_factory=list, max_length=10)
    notes: str | None = None

    @field_validator("proposed_slots")
    @classmethod
    def _wc(cls, v):
        return [wall_clock(x) for x in v]


class VisitUpdate(Loose):
    status: str | None = None
    confirmed_slot: datetime | None = None
    proposed_slots: list[datetime] | None = None
    notes: str | None = None
    report: str | None = None

    @field_validator("confirmed_slot")
    @classmethod
    def _wc1(cls, v):
        return wall_clock(v)

    @field_validator("proposed_slots")
    @classmethod
    def _wc2(cls, v):
        return [wall_clock(x) for x in v] if v is not None else v

    @field_validator("status")
    @classmethod
    def _s(cls, v):
        return _in(v, VISIT_STATUSES, "Statut")


class ComposeIn(Loose):
    template: str
    contact_id: int | None = None
    request_id: int | None = None
    property_ids: list[int] = Field(default_factory=list, max_length=30)
    match_id: int | None = None
    visit_id: int | None = None
    slots: list[str] = Field(default_factory=list)
    listing_url: str | None = None
    to_email: str | None = None
    recipient_name: str | None = None
    notes: str | None = None


class DraftIn(Loose):
    template: str
    to_email: str | None = None
    cc: str | None = None
    subject: str = Field(max_length=300)
    body: str = Field(max_length=50000)
    contact_id: int | None = None
    request_id: int | None = None
    property_ids: list[int] | None = None
    match_id: int | None = None
    visit_id: int | None = None


class DraftStatusIn(Loose):
    status: str
    confirm_sent: bool = False


class EmlIn(Loose):
    to_email: str | None = None
    cc: str | None = None
    subject: str
    body: str
    attach_property_ids: list[int] = Field(default_factory=list, max_length=10)
    draft_id: int | None = None


class ExternalListingIn(Loose):
    url: str = Field(max_length=600)
    title: str | None = None
    property_type: str | None = None
    transaction: str | None = None
    city: str | None = None
    postal_code: str | None = None
    surface: float | None = Field(None, ge=0)
    price: float | None = Field(None, ge=0)
    price_kind: str | None = None
    features: str | None = None
    advertiser_name: str | None = None
    advertiser_phone: str | None = None
    advertiser_email: str | None = None
    consulted_at: datetime | None = None
    search_id: int | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, v):
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL invalide")
        return v

    @field_validator("property_type")
    @classmethod
    def _t(cls, v):
        return _in(v, PROPERTY_TYPES, "Type de bien")

    @field_validator("transaction")
    @classmethod
    def _tr(cls, v):
        return _in(v, TRANSACTIONS, "Transaction")

    @field_validator("price_kind")
    @classmethod
    def _pk(cls, v):
        return _in(v, ("vente", "loyer_annuel", "loyer_m2_an"), "Nature du prix")


class DossierIn(Loose):
    property_ids: list[int] = Field(min_length=1, max_length=30)
    request_id: int | None = None
    client_label: str | None = None
    intro: str | None = None
