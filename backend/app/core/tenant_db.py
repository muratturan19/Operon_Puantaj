# -*- coding: utf-8 -*-
"""
core/tenant_db.py — Çok-kiracılı veritabanı yönlendirme (yalnızca AUTH_MODE=saas).

JWT'deki tenant_slug'a göre ayrı bir "tenant_{slug}_puantaj" Postgres veritabanı
lazy olarak açılır. `create_all` KULLANILMAZ (core/database.py'nin onprem
kararıyla tutarlı) — bunun yerine gerçek Alembic migration zinciri programatik
çalıştırılır; bu sayede seed migration (81f9c9647f37) de otomatik işler ve
Sirket + 3 seed Rol satırı (admin/kullanici/gm) tenant DB'sinde hazır olur.

Desen SaaS_Platform/apps/SRM'in `core/database.py`'sinden (async) sync
SQLModel'e uyarlanmıştır.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Dict, Generator, Set

import psycopg2
from sqlalchemy import Engine, create_engine
from sqlmodel import Session

from app.core.config import get_settings

logger = logging.getLogger("operon_puantaj.tenant_db")

_engines: Dict[str, Engine] = {}
_initialized: Set[str] = set()
_lock = threading.Lock()

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def _sanitize_slug(tenant_slug: str) -> str:
    """DB adına gömülmeden önce tenant_slug'ı doğrula (SQL injection önlemi —
    CREATE DATABASE bind-parameter almaz, adı string interpolation ile yazmak
    zorunludur)."""
    if not _SLUG_RE.match(tenant_slug):
        raise ValueError(f"Geçersiz tenant_slug: {tenant_slug!r}")
    return tenant_slug


def _get_engine(tenant_slug: str) -> Engine:
    if tenant_slug not in _engines:
        settings = get_settings()
        _engines[tenant_slug] = create_engine(
            settings.tenant_db_url(tenant_slug),
            echo=False,
            pool_size=5,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engines[tenant_slug]


def _create_database_if_missing(tenant_slug: str) -> None:
    settings = get_settings()
    db_name = f"tenant_{tenant_slug}_puantaj"

    conn = psycopg2.connect(
        host=settings.tenant_db_host,
        port=settings.tenant_db_port,
        user=settings.tenant_db_user,
        password=settings.tenant_db_password,
        dbname="postgres",
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{db_name}"')
                logger.info("Tenant DB oluşturuldu: %s", db_name)
    finally:
        conn.close()


def _run_migrations(tenant_slug: str) -> None:
    from alembic import command
    from alembic.config import Config

    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent.parent  # .../backend

    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.tenant_db_url(tenant_slug))
    command.upgrade(cfg, "head")
    logger.info("Tenant DB migration'ları çalıştı: tenant_%s_puantaj", tenant_slug)


def ensure_tenant_db(tenant_slug: str) -> None:
    """Tenant DB'si yoksa oluştur ve migration zincirini çalıştır. İdempotent."""
    tenant_slug = _sanitize_slug(tenant_slug)
    if tenant_slug in _initialized:
        return

    with _lock:
        if tenant_slug in _initialized:  # double-check (lock beklerken başka thread halletmiş olabilir)
            return
        _create_database_if_missing(tenant_slug)
        _run_migrations(tenant_slug)
        _initialized.add(tenant_slug)


def get_tenant_session(tenant_slug: str) -> Generator[Session, None, None]:
    ensure_tenant_db(tenant_slug)
    with Session(_get_engine(tenant_slug)) as session:
        yield session
