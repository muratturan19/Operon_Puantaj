# -*- coding: utf-8 -*-
"""
services/audit.py — Append-only denetim kaydı yazıcı.

Desen `E:\\Mira\\MQ_v3\\backend\\app\\utils\\audit_logger.py`'den doğrulandı.
Bu modül dışında AuditLog tablosuna asla UPDATE/DELETE yapılmaz.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlmodel import Session

from app.models.audit import AuditLog

# Bu alanlar hiçbir zaman "değişiklik" olarak loglanmaz — ya gürültü (created_at hiç
# değişmez) ya da zaten AuditLog'un kendi üst-seviye alanlarında var (aktor, zaman).
_GURULTU_ALANLARI = {"id", "created_at", "updated_at", "created_by_id", "updated_by_id"}


def log_change(
    session: Session,
    sirket_id: int,
    aktor_kullanici_id: Optional[int],
    entity_tipi: str,
    entity_id: str,
    aksiyon: str,
    changes: dict[str, dict[str, Any]] | None = None,
    ip_adresi: Optional[str] = None,
) -> AuditLog:
    kayit = AuditLog(
        sirket_id=sirket_id,
        aktor_kullanici_id=aktor_kullanici_id,
        entity_tipi=entity_tipi,
        entity_id=str(entity_id),
        aksiyon=aksiyon,
        changes=changes or {},
        ip_adresi=ip_adresi,
    )
    session.add(kayit)
    session.commit()
    session.refresh(kayit)
    return kayit


def _json_guvenli(deger: Any) -> Any:
    """datetime/date gibi JSON-serialize edilemeyen tipleri metne çevirir."""
    if isinstance(deger, (datetime, date)):
        return deger.isoformat()
    return deger


def diff_alanlar(
    eski: dict[str, Any],
    yeni: dict[str, Any],
    haric: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    İki alan sözlüğü arasındaki farkı `{"alan": {"old": ..., "new": ...}}` biçiminde
    üretir. Gürültü alanları (id, created_at, updated_at, ...) varsayılan olarak
    dışlanır — model_dump()'ın tamamı doğrudan geçirilebilir, temizlik burada olur.
    """
    disla = _GURULTU_ALANLARI | (haric or set())
    degisiklikler: dict[str, dict[str, Any]] = {}
    # Union of keys: silme işleminde (yeni={}) de "ne silindi" bilgisi kaybolmasın diye
    # yalnızca yeni.items() değil, eski'deki alanlar da taranır.
    for alan in eski.keys() | yeni.keys():
        if alan in disla:
            continue
        eski_deger = eski.get(alan)
        yeni_deger = yeni.get(alan)
        if eski_deger != yeni_deger:
            degisiklikler[alan] = {"old": _json_guvenli(eski_deger), "new": _json_guvenli(yeni_deger)}
    return degisiklikler
