"""Configuration chargée exclusivement depuis l'environnement (ou un fichier .env).

Aucun secret n'est codé en dur : voir `.env.example`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field("development", description="development | test | production")
    app_name: str = "ImmoPro Entreprise"
    secret_key: str = ""
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'immopro.db').as_posix()}"
    public_base_url: str = "http://localhost:5173"

    # Sessions et sécurité
    cookie_secure: bool = True
    session_idle_minutes: int = 480
    session_max_hours: int = 168
    login_max_attempts: int = 5
    login_lock_minutes: int = 15
    reset_token_minutes: int = 30
    trust_proxy_headers: bool = False

    # Fichiers
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    max_upload_mb: int = 25
    frontend_dist: Path = BASE_DIR.parent / "frontend" / "dist"

    # Sauvegardes
    backup_dir: Path = BASE_DIR / "data" / "backups"
    backup_interval_hours: int = 24
    backup_keep: int = 14

    # Géocodage (Géoplateforme IGN / Base Adresse Nationale). Désactivable.
    geocoder_enabled: bool = True
    geocoder_url: str = "https://data.geopf.fr/geocodage/search"

    # Intégration Outlook locale facultative (agent Windows sur 127.0.0.1)
    outlook_agent_default_url: str = "http://127.0.0.1:8765"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def session_cookie_name(self) -> str:
        # Le préfixe __Host- impose Secure + Path=/ + pas de Domain.
        return "__Host-immopro_session" if self.cookie_secure else "immopro_session"

    @property
    def csrf_cookie_name(self) -> str:
        return "__Host-immopro_csrf" if self.cookie_secure else "immopro_csrf"

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.app_env == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY doit contenir au moins 32 caractères en production.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE doit être true en production (HTTPS obligatoire).")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
