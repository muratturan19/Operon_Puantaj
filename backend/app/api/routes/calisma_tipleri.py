# -*- coding: utf-8 -*-
"""
api/routes/calisma_tipleri.py — Çalışan Tipi CRUD ("+Ekle" ekranı, CLAUDE.md §7).
Parametrizasyonun TEK mekanizması — değişiklikler audit log'a yazılır (kullanıcı onayı: "değişiklikler kayıt altına alınacak").
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import CALISMA_TIPI_YONETEBILIR, PUANTAJ_GOREBILIR
from app.core.security import get_current_user, require_permission
from app.models.calisma_tipi import CalismaTipi
from app.models.rbac import Kullanici
from app.services.audit import diff_alanlar, log_change

router = APIRouter(prefix="/api/calisma-tipleri", tags=["calisma-tipleri"])


class CalismaTipiCreate(BaseModel):
    kod: str
    ad: str
    gunluk_saat: float
    haftalik_gun: int
    hafta_ici_fm_orani: float = 1.5
    hafta_sonu_fm_orani: float = 2.0
    resmi_tatil_fm_orani: float = 2.0
    hafta_tatili_gunleri: list[int] = [6]


class CalismaTipiUpdate(BaseModel):
    ad: Optional[str] = None
    gunluk_saat: Optional[float] = None
    haftalik_gun: Optional[int] = None
    hafta_ici_fm_orani: Optional[float] = None
    hafta_sonu_fm_orani: Optional[float] = None
    resmi_tatil_fm_orani: Optional[float] = None
    hafta_tatili_gunleri: Optional[list[int]] = None
    aktif: Optional[bool] = None


@router.get("", response_model=list[CalismaTipi])
def listele(
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[CalismaTipi]:
    return session.exec(
        select(CalismaTipi).where(CalismaTipi.sirket_id == current_user.sirket_id).order_by(CalismaTipi.id)
    ).all()


@router.post("", response_model=CalismaTipi, status_code=status.HTTP_201_CREATED)
def olustur(
    payload: CalismaTipiCreate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(CALISMA_TIPI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> CalismaTipi:
    tip = CalismaTipi(sirket_id=current_user.sirket_id, **payload.model_dump())
    session.add(tip)
    session.commit()
    session.refresh(tip)

    log_change(
        session, current_user.sirket_id, current_user.id,
        "CalismaTipi", str(tip.id), "create",
        changes=diff_alanlar({}, payload.model_dump()),
        ip_adresi=request.client.host if request.client else None,
    )
    return tip


@router.put("/{tip_id}", response_model=CalismaTipi)
def guncelle(
    tip_id: int,
    payload: CalismaTipiUpdate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(CALISMA_TIPI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> CalismaTipi:
    tip = session.get(CalismaTipi, tip_id)
    if tip is None or tip.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Çalışma tipi bulunamadı")

    eski = tip.model_dump()
    guncellenecek = payload.model_dump(exclude_unset=True)
    for alan, deger in guncellenecek.items():
        setattr(tip, alan, deger)
    session.add(tip)
    session.commit()
    session.refresh(tip)

    degisiklikler = diff_alanlar(eski, tip.model_dump())
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "CalismaTipi", str(tip.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return tip
