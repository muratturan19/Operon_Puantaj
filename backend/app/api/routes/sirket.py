# -*- coding: utf-8 -*-
"""api/routes/sirket.py — Şirket geneli ayarlar (Faz 1: Raporlu ödeme politikası).

Kullanıcı kararı (2026-07-04): Raporlu'nun maaş etkisi çalışan tipinden
bağımsız, şirket genelinde tek bir ayar — bu route o ayarın okunup
değiştirilmesini sağlar. Değişiklikler audit log'a yazılır (CLAUDE.md §7 —
"parametre sayfası ... değişiklikler kayıt altına alınacak")."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlmodel import Session

from app.core.database import get_session
from app.core.permissions import SIRKET_AYARLARINI_YONETEBILIR
from app.core.security import require_permission
from app.models.rbac import Kullanici
from app.models.sirket import Sirket
from app.services.audit import diff_alanlar, log_change
from app.services.payroll_calc import RAPORLU_POLITIKALARI

router = APIRouter(prefix="/api/sirket", tags=["sirket"])


class SirketResponse(BaseModel):
    id: int
    ad: str
    raporlu_politikasi: str
    raporlu_esik_gun: int


class SirketUpdate(BaseModel):
    raporlu_politikasi: Optional[str] = None
    raporlu_esik_gun: Optional[int] = None

    @field_validator("raporlu_politikasi")
    @classmethod
    def _gecerli_politika(cls, deger: Optional[str]) -> Optional[str]:
        if deger is not None and deger not in RAPORLU_POLITIKALARI:
            raise ValueError(f"bilinmeyen raporlu_politikasi: {deger!r}")
        return deger

    @field_validator("raporlu_esik_gun")
    @classmethod
    def _negatif_olmayan_esik(cls, deger: Optional[int]) -> Optional[int]:
        if deger is not None and deger < 0:
            raise ValueError("raporlu_esik_gun negatif olamaz")
        return deger


def _sirket_getir(session: Session, current_user: Kullanici) -> Sirket:
    sirket = session.get(Sirket, current_user.sirket_id)
    if sirket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Şirket bulunamadı")
    return sirket


@router.get("", response_model=SirketResponse)
def getir(
    current_user: Kullanici = Depends(require_permission(SIRKET_AYARLARINI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Sirket:
    return _sirket_getir(session, current_user)


@router.put("", response_model=SirketResponse)
def guncelle(
    payload: SirketUpdate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(SIRKET_AYARLARINI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Sirket:
    sirket = _sirket_getir(session, current_user)

    eski = sirket.model_dump()
    guncellenecek = payload.model_dump(exclude_unset=True)
    for alan, deger in guncellenecek.items():
        setattr(sirket, alan, deger)
    session.add(sirket)
    session.commit()
    session.refresh(sirket)

    degisiklikler = diff_alanlar(eski, sirket.model_dump())
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "Sirket", str(sirket.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return sirket
