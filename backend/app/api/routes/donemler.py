# -*- coding: utf-8 -*-
"""api/routes/donemler.py — Dönem (yıl/ay) CRUD."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import PUANTAJ_GIREBILIR, PUANTAJ_GOREBILIR
from app.core.security import require_permission
from app.models.donem import Donem
from app.models.rbac import Kullanici

router = APIRouter(prefix="/api/donemler", tags=["donemler"])


class DonemCreate(BaseModel):
    yil: int
    ay: int
    excel_sheet_adi: Optional[str] = None


@router.get("", response_model=list[Donem])
def listele(
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[Donem]:
    return session.exec(
        select(Donem).where(Donem.sirket_id == current_user.sirket_id).order_by(Donem.yil, Donem.ay)
    ).all()


@router.post("", response_model=Donem)
def getir_veya_olustur(
    payload: DonemCreate,
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GIREBILIR)),
    session: Session = Depends(get_session),
) -> Donem:
    """Get-or-create — kullanıcı geri bildirimi (2026-07-04): dönem seçici 12 ayı
    da göstermeli (ör. haziranda çalışırken temmuz sonuna yıllık izin girmek
    isteyebilir). Frontend henüz Excel'i içe aktarılmamış bir ayı seçince bu
    uç nokta o ayı sessizce oluşturur — 409 ile kullanıcıyı şaşırtmaz."""
    mevcut = session.exec(
        select(Donem).where(
            Donem.sirket_id == current_user.sirket_id,
            Donem.yil == payload.yil,
            Donem.ay == payload.ay,
        )
    ).first()
    if mevcut:
        return mevcut

    # N.G varsayılanı — kullanıcı kararı (2026-07-06): ayın takvim gün sayısı
    # (Haziran→30, Temmuz→31, Şubat→28/29), kişi bazlı istisnalar ayrı tutulur.
    donem = Donem(
        sirket_id=current_user.sirket_id,
        ng=Donem.takvim_gun_sayisi(payload.yil, payload.ay),
        **payload.model_dump(),
    )
    session.add(donem)
    session.commit()
    session.refresh(donem)
    return donem
