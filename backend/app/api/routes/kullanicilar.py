# -*- coding: utf-8 -*-
"""api/routes/kullanicilar.py — Kullanıcı CRUD + parola değiştirme."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import KULLANICI_YONETEBILIR
from app.core.security import get_current_user, hash_password, require_permission
from app.models.rbac import Kullanici, Rol
from app.services.audit import diff_alanlar, log_change

router = APIRouter(prefix="/api/kullanicilar", tags=["kullanicilar"])


class KullaniciCreate(BaseModel):
    kullanici_adi: str
    ad_soyad: str
    email: Optional[str] = None
    parola: str
    rol_id: int


class KullaniciUpdate(BaseModel):
    ad_soyad: Optional[str] = None
    email: Optional[str] = None
    rol_id: Optional[int] = None
    aktif: Optional[bool] = None


class ParolaDegistir(BaseModel):
    yeni_parola: str


class KullaniciResponse(BaseModel):
    id: int
    kullanici_adi: str
    ad_soyad: str
    email: Optional[str]
    rol_id: int
    aktif: bool


@router.get("", response_model=list[KullaniciResponse])
def listele(
    current_user: Kullanici = Depends(require_permission(KULLANICI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> list[Kullanici]:
    return session.exec(
        select(Kullanici).where(Kullanici.sirket_id == current_user.sirket_id).order_by(Kullanici.id)
    ).all()


@router.post("", response_model=KullaniciResponse, status_code=status.HTTP_201_CREATED)
def olustur(
    payload: KullaniciCreate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(KULLANICI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Kullanici:
    mevcut = session.exec(
        select(Kullanici).where(Kullanici.kullanici_adi == payload.kullanici_adi)
    ).first()
    if mevcut:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu kullanıcı adı kullanımda")

    yeni = Kullanici(
        sirket_id=current_user.sirket_id,
        kullanici_adi=payload.kullanici_adi,
        ad_soyad=payload.ad_soyad,
        email=payload.email,
        hashed_password=hash_password(payload.parola),
        rol_id=payload.rol_id,
    )
    session.add(yeni)
    session.commit()
    session.refresh(yeni)

    log_change(
        session, current_user.sirket_id, current_user.id,
        "Kullanici", str(yeni.id), "create",
        changes=diff_alanlar({}, {"kullanici_adi": payload.kullanici_adi, "rol_id": payload.rol_id}),
        ip_adresi=request.client.host if request.client else None,
    )
    return yeni


@router.put("/{kullanici_id}", response_model=KullaniciResponse)
def guncelle(
    kullanici_id: int,
    payload: KullaniciUpdate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(KULLANICI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Kullanici:
    hedef = session.get(Kullanici, kullanici_id)
    if hedef is None or hedef.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")

    eski = hedef.model_dump(exclude={"hashed_password"})
    guncellenecek = payload.model_dump(exclude_unset=True)
    for alan, deger in guncellenecek.items():
        setattr(hedef, alan, deger)
    session.add(hedef)
    session.commit()
    session.refresh(hedef)

    degisiklikler = diff_alanlar(eski, hedef.model_dump(exclude={"hashed_password"}))
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "Kullanici", str(hedef.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return hedef


@router.post("/{kullanici_id}/parola-degistir", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def parola_degistir(
    kullanici_id: int,
    payload: ParolaDegistir,
    current_user: Kullanici = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """Kendi parolasını değiştirebilir; başkasınınkini yalnızca KULLANICI_YONETEBILIR izniyle."""
    hedef = session.get(Kullanici, kullanici_id)
    if hedef is None or hedef.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")

    if hedef.id != current_user.id:
        rol = session.get(Rol, current_user.rol_id)
        if not rol or not rol.izinler.get(KULLANICI_YONETEBILIR, False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için yetkiniz yok")

    hedef.hashed_password = hash_password(payload.yeni_parola)
    session.add(hedef)
    session.commit()
