# -*- coding: utf-8 -*-
"""
core/database.py — PostgreSQL engine + oturum yönetimi.

Şema değişiklikleri Alembic migration'ları ile yapılır (`alembic upgrade head`).
Bu modül yalnızca engine/session sağlar — create_all() burada YOK
(MQ_v3'teki create_all + elle ALTER TABLE sürüklenmesi bilinçli olarak tekrarlanmıyor).

AUTH_MODE=saas'ta `get_session`, tek global engine yerine JWT'deki tenant_slug'a
göre yönlendirilen per-tenant bir session'a bağlanır (bkz. core/tenant_db.py,
core/auth_context.py). Hangi implementasyonun kullanılacağı import zamanında,
`settings.auth_mode`'a göre seçilir — mevcut route dosyaları değişmeden
`from app.core.database import get_session` kullanmaya devam eder.
"""
from __future__ import annotations

import logging
from typing import Generator
from urllib.parse import urlparse

from fastapi import Depends
from sqlmodel import Session, create_engine

from app.core.auth_context import get_tenant_context
from app.core.config import get_settings
from app.core.tenant_db import get_tenant_session

logger = logging.getLogger("operon_puantaj.database")

_settings = get_settings()


def _create_engine():
    # Güvenlik: bağlantı dizesindeki kullanıcı adı/şifreyi asla loglama.
    try:
        parsed = urlparse(_settings.database_url)
        logger.info(
            "DB bağlantısı: %s://%s%s/%s",
            parsed.scheme,
            parsed.hostname or "?",
            f":{parsed.port}" if parsed.port else "",
            (parsed.path or "").lstrip("/") or "?",
        )
    except Exception:
        logger.info("DB bağlantısı kuruluyor (URL gizli)")

    return create_engine(
        _settings.database_url,
        echo=False,
        pool_size=_settings.db_pool_size,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine = _create_engine()


def get_session_onprem() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_session_saas(ctx: dict = Depends(get_tenant_context)) -> Generator[Session, None, None]:
    yield from get_tenant_session(ctx["tenant_slug"])


get_session = get_session_saas if _settings.auth_mode == "saas" else get_session_onprem
