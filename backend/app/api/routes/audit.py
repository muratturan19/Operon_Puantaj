# -*- coding: utf-8 -*-
"""api/routes/audit.py — Güvenlik/Denetim günlüğü görüntüleme (salt okunur —
yazma yalnızca services/audit.py üzerinden)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import AUDIT_GOREBILIR, GOREBILIR_MAAS_TUTARI
from app.core.security import require_permission
from app.models.audit import AuditLog
from app.models.rbac import Kullanici

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    aktor_adi: str  # "Sistem" if aktor_kullanici_id is None (ör. otomatik dönem oluşturma)
    entity_tipi: str
    entity_id: str
    aksiyon: str
    changes: dict
    zaman: str


@router.get("", response_model=list[AuditLogResponse])
def listele(
    entity_tipi: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
    # Güvenlik sayfası Personel maaş değişikliklerinin ham eski/yeni değerini
    # içerir (`changes` alanı) — GOREBILIR_MAAS_TUTARI olmadan tüm günlük
    # kapatılır (2026-07-04 kullanıcı kararı: rastlantısal izin eşleşmesine
    # güvenilmesin, bkz. core/security.py::require_permission docstring).
    current_user: Kullanici = Depends(require_permission(AUDIT_GOREBILIR, GOREBILIR_MAAS_TUTARI)),
    session: Session = Depends(get_session),
) -> list[AuditLogResponse]:
    sorgu = select(AuditLog).where(AuditLog.sirket_id == current_user.sirket_id)
    if entity_tipi:
        sorgu = sorgu.where(AuditLog.entity_tipi == entity_tipi)
    if entity_id:
        sorgu = sorgu.where(AuditLog.entity_id == entity_id)
    sorgu = sorgu.order_by(AuditLog.zaman.desc()).limit(limit)
    kayitlar = session.exec(sorgu).all()

    aktor_id_listesi = {k.aktor_kullanici_id for k in kayitlar if k.aktor_kullanici_id is not None}
    aktorler = {
        k.id: k.ad_soyad
        for k in session.exec(select(Kullanici).where(Kullanici.id.in_(aktor_id_listesi))).all()
    } if aktor_id_listesi else {}

    return [
        AuditLogResponse(
            id=k.id,
            aktor_adi=aktorler.get(k.aktor_kullanici_id, "Sistem"),
            entity_tipi=k.entity_tipi,
            entity_id=k.entity_id,
            aksiyon=k.aksiyon,
            changes=k.changes,
            zaman=k.zaman.isoformat(),
        )
        for k in kayitlar
    ]
