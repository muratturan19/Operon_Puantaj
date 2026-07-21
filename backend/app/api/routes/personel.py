# -*- coding: utf-8 -*-
"""api/routes/personel.py — Personel CRUD (Puantaj_Brief §10 — import dışında uygulama içi yönetim de var).

`aktif` artık `isten_cikis_tarihi`den türetilir (kullanıcı geri bildirimi,
2026-07-04) — "İşten Çıkar" bir tarih girer, "Geri Al" o tarihi temizler.
Ay bazlı görünürlük (işten çıkan o ay sonuna dek listede kalır, yeni giren
işe başladığı aydan itibaren görünür) frontend'de `utils/personel.ts` ile
uygulanıyor; bu route her zaman TÜM personeli (geçmiş dahil) döner."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import GOREBILIR_MAAS_TUTARI, PERSONEL_YONETEBILIR, PUANTAJ_GOREBILIR
from app.core.security import require_permission
from app.models.personel import Personel
from app.models.rbac import Kullanici, Rol
from app.services.audit import diff_alanlar, log_change

router = APIRouter(prefix="/api/personel", tags=["personel"])


class PersonelCreate(BaseModel):
    ad_soyad: str
    calisma_tipi_id: int
    maas: float
    ng: int = 30
    ise_baslama_tarihi: Optional[date] = None


class PersonelUpdate(BaseModel):
    ad_soyad: Optional[str] = None
    calisma_tipi_id: Optional[int] = None
    maas: Optional[float] = None
    ng: Optional[int] = None
    ise_baslama_tarihi: Optional[date] = None
    isten_cikis_tarihi: Optional[date] = None  # set = işten çıkar, null gönderilmesi = geri al (yeniden aktif)


class PersonelResponse(BaseModel):
    id: int
    ad_soyad: str
    calisma_tipi_id: int
    maas: Optional[float]  # CLAUDE.md §7 — kaynak Excel'de maaş yoksa gorebilir_maas_tutari=false, hiç dönmez
    ng: int
    aktif: bool
    ise_baslama_tarihi: Optional[date]
    isten_cikis_tarihi: Optional[date]


def _maas_gorebilir(session: Session, current_user: Kullanici) -> bool:
    rol = session.get(Rol, current_user.rol_id)
    return bool(rol and rol.izinler.get(GOREBILIR_MAAS_TUTARI, False))


def _to_response(personel: Personel, maas_gorebilir: bool) -> PersonelResponse:
    return PersonelResponse(
        id=personel.id,
        ad_soyad=personel.ad_soyad,
        calisma_tipi_id=personel.calisma_tipi_id,
        maas=personel.maas if maas_gorebilir else None,
        ng=personel.ng,
        aktif=personel.aktif,
        ise_baslama_tarihi=personel.ise_baslama_tarihi,
        isten_cikis_tarihi=personel.isten_cikis_tarihi,
    )


@router.get("", response_model=list[PersonelResponse])
def listele(
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[PersonelResponse]:
    maas_gorebilir = _maas_gorebilir(session, current_user)
    personeller = session.exec(
        select(Personel).where(Personel.sirket_id == current_user.sirket_id).order_by(Personel.id)
    ).all()
    return [_to_response(p, maas_gorebilir) for p in personeller]


@router.post("", response_model=PersonelResponse, status_code=status.HTTP_201_CREATED)
def olustur(
    payload: PersonelCreate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(PERSONEL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> PersonelResponse:
    personel = Personel(sirket_id=current_user.sirket_id, **payload.model_dump())
    session.add(personel)
    session.commit()
    session.refresh(personel)

    log_change(
        session, current_user.sirket_id, current_user.id,
        "Personel", str(personel.id), "create",
        changes=diff_alanlar({}, payload.model_dump()),
        ip_adresi=request.client.host if request.client else None,
    )
    return _to_response(personel, _maas_gorebilir(session, current_user))


@router.put("/{personel_id}", response_model=PersonelResponse)
def guncelle(
    personel_id: int,
    payload: PersonelUpdate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(PERSONEL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> PersonelResponse:
    personel = session.get(Personel, personel_id)
    if personel is None or personel.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı")

    eski = personel.model_dump()
    guncellenecek = payload.model_dump(exclude_unset=True)
    for alan, deger in guncellenecek.items():
        setattr(personel, alan, deger)
    personel.updated_at = datetime.utcnow()
    session.add(personel)
    session.commit()
    session.refresh(personel)

    degisiklikler = diff_alanlar(eski, personel.model_dump())
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "Personel", str(personel.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return _to_response(personel, _maas_gorebilir(session, current_user))
