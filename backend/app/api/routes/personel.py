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
from app.models.personel_maas_gecmisi import PersonelMaasGecmisi
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
    # `maas` BİLİNÇLİ OLARAK yok — kullanıcı sorusu (2026-07-06): "maaşlara zam
    # gelince onu sisteme nasıl alacağız?" Serbestçe düzenlenebilir tek bir
    # `maas` alanı, geçmiş dönemlerin bordrosunu SESSİZCE bozuyordu (ozet()/export
    # her zaman güncel değeri okuyordu). Artık TÜM maaş değişiklikleri
    # `POST /{id}/zam` üzerinden, etkin olduğu (yıl,ay) belirtilerek yapılmak
    # zorunda — bkz. personel_maas_gecmisi.py.
    ad_soyad: Optional[str] = None
    calisma_tipi_id: Optional[int] = None
    ng: Optional[int] = None
    ise_baslama_tarihi: Optional[date] = None
    isten_cikis_tarihi: Optional[date] = None  # set = işten çıkar, null gönderilmesi = geri al (yeniden aktif)


class ZamGir(BaseModel):
    yil: int
    ay: int
    maas: float


class MaasGecmisiKaydi(BaseModel):
    id: int
    yil: int
    ay: int
    maas: float
    created_at: datetime


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


@router.get("/{personel_id}/maas-gecmisi", response_model=list[MaasGecmisiKaydi])
def maas_gecmisi(
    personel_id: int,
    current_user: Kullanici = Depends(require_permission(PERSONEL_YONETEBILIR, GOREBILIR_MAAS_TUTARI)),
    session: Session = Depends(get_session),
) -> list[PersonelMaasGecmisi]:
    personel = session.get(Personel, personel_id)
    if personel is None or personel.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı")
    return session.exec(
        select(PersonelMaasGecmisi)
        .where(PersonelMaasGecmisi.personel_id == personel_id)
        .order_by(PersonelMaasGecmisi.yil.desc(), PersonelMaasGecmisi.ay.desc())
    ).all()


@router.post("/{personel_id}/zam", response_model=PersonelResponse, status_code=status.HTTP_201_CREATED)
def zam_gir(
    personel_id: int,
    payload: ZamGir,
    request: Request,
    current_user: Kullanici = Depends(require_permission(PERSONEL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> PersonelResponse:
    """Etkin-tarihli maaş değişikliği — girildiği (yıl,ay)'dan itibaren bir sonraki
    zamma kadar geçerli olur, GEÇMİŞ dönemlerin hesabını ETKİLEMEZ (bkz.
    personel_filtre.py::efektif_maas). İlk kez zam giriliyorsa, o ana kadarki
    maaşı geçmiş dönemler için sabitleyen bir "taban" kayıt da otomatik eklenir
    — aksi halde geçmiş dönemler de yanlışlıkla yeni maaşı görürdü."""
    personel = session.get(Personel, personel_id)
    if personel is None or personel.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı")

    hic_kaydi_yok = session.exec(
        select(PersonelMaasGecmisi).where(PersonelMaasGecmisi.personel_id == personel_id)
    ).first() is None

    if hic_kaydi_yok:
        if personel.ise_baslama_tarihi:
            taban_yil, taban_ay = personel.ise_baslama_tarihi.year, personel.ise_baslama_tarihi.month
        else:
            taban_yil, taban_ay = 2000, 1
        if (taban_yil, taban_ay) >= (payload.yil, payload.ay):
            taban_ay = payload.ay - 1
            taban_yil = payload.yil
            if taban_ay < 1:
                taban_ay = 12
                taban_yil -= 1
        session.add(PersonelMaasGecmisi(
            personel_id=personel_id, yil=taban_yil, ay=taban_ay,
            maas=personel.maas, created_by_id=current_user.id,
        ))

    mevcut_kayit = session.exec(
        select(PersonelMaasGecmisi).where(
            PersonelMaasGecmisi.personel_id == personel_id,
            PersonelMaasGecmisi.yil == payload.yil,
            PersonelMaasGecmisi.ay == payload.ay,
        )
    ).first()
    if mevcut_kayit is not None:
        # Aynı (yıl,ay) için düzeltme — iki farklı değer anlamsız olurdu, üzerine yazılır.
        mevcut_kayit.maas = payload.maas
        mevcut_kayit.created_by_id = current_user.id
        mevcut_kayit.created_at = datetime.utcnow()
        session.add(mevcut_kayit)
    else:
        session.add(PersonelMaasGecmisi(
            personel_id=personel_id, yil=payload.yil, ay=payload.ay,
            maas=payload.maas, created_by_id=current_user.id,
        ))

    eski_maas = personel.maas
    # `Personel.maas` "güncel" değeri olarak senkron tutulur (yeni personel/hiç
    # zam girilmemiş kişiler için efektif_maas()'ın düştüğü fallback budur).
    personel.maas = payload.maas
    personel.updated_at = datetime.utcnow()
    session.add(personel)
    session.commit()
    session.refresh(personel)

    log_change(
        session, current_user.sirket_id, current_user.id,
        "Personel", str(personel.id), "zam",
        changes={
            "maas": {"old": eski_maas, "new": payload.maas},
            "efektif_donem": {"old": None, "new": f"{payload.yil}-{payload.ay:02d}"},
        },
        ip_adresi=request.client.host if request.client else None,
    )
    return _to_response(personel, _maas_gorebilir(session, current_user))
