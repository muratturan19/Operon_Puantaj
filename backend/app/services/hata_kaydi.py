# -*- coding: utf-8 -*-
"""
services/hata_kaydi.py — Yakalanmamış hataları hem log'a hem tenant DB'sine yazar.

DB yazımı BEST-EFFORT'tur: hata anında tenant DB'sine erişilemiyor olabilir
(bağlantı kopmuş, migration henüz çalışmamış, oturum yok). Bu durumda kayıt
yalnızca log'a düşer — hata yolunda ikinci bir istisna üretip asıl hatayı
gizlemek kabul edilemez.
"""
from __future__ import annotations

import logging
import traceback
import uuid
from typing import Optional

from sqlmodel import Session

from app.models.hata import HataKaydi

logger = logging.getLogger("operon_puantaj.hata")


def yeni_istek_id() -> str:
    """Kullanıcıya gösterilen takip kodu — DB kaydıyla birebir eşleşir."""
    return f"E-{uuid.uuid4().hex[:8]}"


def kaydet(
    istek_id: str,
    exc: BaseException,
    yol: str,
    metod: str,
    sorgu: Optional[str] = None,
    kullanici: Optional[str] = None,
    tenant_slug: Optional[str] = None,
) -> None:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(
        "%s | %s %s%s | kullanici=%s tenant=%s | %s: %s\n%s",
        istek_id, metod, yol, f"?{sorgu}" if sorgu else "",
        kullanici or "-", tenant_slug or "-",
        type(exc).__name__, exc, tb,
    )

    if not tenant_slug:
        return
    try:
        from app.core.tenant_db import _get_engine  # geç import: dairesel bağımlılık olmasın

        with Session(_get_engine(tenant_slug)) as session:
            session.add(
                HataKaydi(
                    istek_id=istek_id,
                    yol=yol,
                    metod=metod,
                    sorgu=sorgu,
                    kullanici=kullanici,
                    hata_tipi=type(exc).__name__,
                    mesaj=str(exc)[:2000],
                    traceback_metni=tb,
                )
            )
            session.commit()
    except Exception as db_hatasi:  # noqa: BLE001 — asıl hatayı gizlememek için yutuluyor
        logger.warning("%s | hata kaydı DB'ye yazılamadı: %s", istek_id, db_hatasi)
