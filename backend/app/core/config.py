# -*- coding: utf-8 -*-
"""
core/config.py — Operon Puantaj uygulama ayarları

.env dosyasından okunur; Pydantic v2 Settings kullanılır.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")

    # Veritabanı — PostgreSQL, SaaS ve on-prem'de aynı motor (CLAUDE.md §8.2)
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/operon_puantaj",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")

    # Auth — yerel kullanıcı adı/şifre + JWT (Faz 1, varsayılan). Portal SSO Faz 2 (§8.8),
    # AUTH_MODE=saas ile aktifleşir — core/database.py ve core/security.py bu değere göre
    # onprem/saas dependency implementasyonlarından birini import zamanında seçer.
    auth_mode: str = Field(default="onprem", alias="AUTH_MODE")  # "onprem" | "saas"
    secret_key: str = Field(default="CHANGE-ME-IN-PRODUCTION", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Portal SSO (yalnızca AUTH_MODE=saas'ta kullanılır) — CLAUDE.md §4.2/6
    portal_url: str = Field(default="https://portal.kolektif360.com", alias="PORTAL_URL")
    portal_issuer: str = Field(default="https://portal.kolektif360.com", alias="PORTAL_ISSUER")
    portal_app_slug: str = Field(default="puantaj", alias="PORTAL_APP_SLUG")

    # Tenant-DB admin bağlantısı (yalnızca AUTH_MODE=saas'ta kullanılır) — her tenant için
    # ayrı bir "tenant_{slug}_puantaj" veritabanı bu bağlantı üzerinden lazy oluşturulur.
    tenant_db_host: str = Field(default="localhost", alias="DATABASE_HOST")
    tenant_db_port: int = Field(default=5432, alias="DATABASE_PORT")
    tenant_db_user: str = Field(default="postgres", alias="DATABASE_USER")
    tenant_db_password: str = Field(default="postgres", alias="DATABASE_PASSWORD")

    def tenant_db_url(self, tenant_slug: str) -> str:
        return (
            f"postgresql+psycopg2://{self.tenant_db_user}:{self.tenant_db_password}"
            f"@{self.tenant_db_host}:{self.tenant_db_port}/tenant_{tenant_slug}_puantaj"
        )

    # Sunucu
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
