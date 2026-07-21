# -*- coding: utf-8 -*-
"""
api/routes/setup.py — Kurulum Sihirbazı (CLAUDE.md §8.7).

Auth GEREKTİRMEZ (henüz hiç kullanıcı yokken çağrılır). "Kurulum tamamlandı mı"
sorusu, o şirkette en az bir Kullanici satırı var mı diye bakılarak cevaplanır —
ayrı bir bayrak/tablo gerekmez. `POST /complete` yalnızca hiç kullanıcı yokken
çalışır; sonrasında 409 döner (tekrar çalıştırılamaz, admin panelden yönetim var).
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import GOREBILIR_MAAS_TUTARI
from app.core.security import create_access_token, hash_password
from app.models.rbac import Kullanici, Rol
from app.models.sirket import Sirket

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupStatus(BaseModel):
    kurulum_tamamlandi: bool
    sirket_adi: Optional[str] = None


class AdminHesabi(BaseModel):
    kullanici_adi: str
    ad_soyad: str
    parola: str = Field(min_length=6)


class SetupCompleteRequest(BaseModel):
    sirket_adi: str
    mod: Literal["tek", "cok"]
    admin: AdminHesabi
    kullanici_maas_gorebilir: bool = False  # yalnızca mod="cok" iken anlamlı


class SetupCompleteResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _mevcut_sirket(session: Session) -> Sirket:
    sirket = session.exec(select(Sirket)).first()
    if sirket is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şirket kaydı bulunamadı — migration'lar çalıştırılmamış olabilir",
        )
    return sirket


@router.get("/status", response_model=SetupStatus)
def durum(session: Session = Depends(get_session)) -> SetupStatus:
    sirket = _mevcut_sirket(session)
    kullanici_var = session.exec(
        select(Kullanici).where(Kullanici.sirket_id == sirket.id)
    ).first()
    return SetupStatus(kurulum_tamamlandi=kullanici_var is not None, sirket_adi=sirket.ad)


@router.post("/complete", response_model=SetupCompleteResponse, status_code=status.HTTP_201_CREATED)
def tamamla(payload: SetupCompleteRequest, session: Session = Depends(get_session)) -> SetupCompleteResponse:
    sirket = _mevcut_sirket(session)

    mevcut = session.exec(select(Kullanici).where(Kullanici.sirket_id == sirket.id)).first()
    if mevcut is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kurulum zaten tamamlanmış")

    sirket.ad = payload.sirket_adi
    session.add(sirket)

    # Çok Kullanıcı modunda Admin'in "Kullanıcı rolü maaş görsün mü?" kararı role işlenir.
    # Tek Kullanıcı modunda bu ayarın hiçbir etkisi yok (sadece Admin hesabı açılır, o
    # zaten her şeyi görür) — yine de tutarlılık için role yazılır.
    kullanici_rolu = session.exec(
        select(Rol).where(Rol.sirket_id == sirket.id, Rol.kod == "kullanici")
    ).first()
    if kullanici_rolu is not None:
        kullanici_rolu.izinler = {
            **kullanici_rolu.izinler,
            GOREBILIR_MAAS_TUTARI: payload.kullanici_maas_gorebilir,
        }
        session.add(kullanici_rolu)

    admin_rolu = session.exec(
        select(Rol).where(Rol.sirket_id == sirket.id, Rol.kod == "admin")
    ).first()
    if admin_rolu is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin rolü bulunamadı — seed migration eksik olabilir",
        )

    admin_kullanici = Kullanici(
        sirket_id=sirket.id,
        kullanici_adi=payload.admin.kullanici_adi,
        ad_soyad=payload.admin.ad_soyad,
        hashed_password=hash_password(payload.admin.parola),
        rol_id=admin_rolu.id,
    )
    session.add(admin_kullanici)
    session.commit()
    session.refresh(admin_kullanici)

    return SetupCompleteResponse(access_token=create_access_token(admin_kullanici))
