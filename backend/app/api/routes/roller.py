# -*- coding: utf-8 -*-
"""api/routes/roller.py — Rol/izin yönetimi (genişletilebilir — sabit 2/3 rol değil, CLAUDE.md §7)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import KULLANICI_YONETEBILIR, PUANTAJ_GOREBILIR
from app.core.security import require_permission
from app.models.rbac import Kullanici, Rol
from app.services.audit import diff_alanlar, log_change

router = APIRouter(prefix="/api/roller", tags=["roller"])


class RolCreate(BaseModel):
    kod: str
    ad: str
    izinler: dict[str, bool] = {}


class RolUpdate(BaseModel):
    ad: Optional[str] = None
    izinler: Optional[dict[str, bool]] = None


@router.get("", response_model=list[Rol])
def listele(
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[Rol]:
    return session.exec(select(Rol).where(Rol.sirket_id == current_user.sirket_id)).all()


@router.post("", response_model=Rol, status_code=status.HTTP_201_CREATED)
def olustur(
    payload: RolCreate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(KULLANICI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Rol:
    rol = Rol(sirket_id=current_user.sirket_id, sistem_varsayilani=False, **payload.model_dump())
    session.add(rol)
    session.commit()
    session.refresh(rol)

    log_change(
        session, current_user.sirket_id, current_user.id,
        "Rol", str(rol.id), "create",
        changes=diff_alanlar({}, payload.model_dump()),
        ip_adresi=request.client.host if request.client else None,
    )
    return rol


@router.put("/{rol_id}", response_model=Rol)
def guncelle(
    rol_id: int,
    payload: RolUpdate,
    request: Request,
    current_user: Kullanici = Depends(require_permission(KULLANICI_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Rol:
    rol = session.get(Rol, rol_id)
    if rol is None or rol.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı")

    eski = rol.model_dump()
    guncellenecek = payload.model_dump(exclude_unset=True)
    for alan, deger in guncellenecek.items():
        setattr(rol, alan, deger)
    session.add(rol)
    session.commit()
    session.refresh(rol)

    degisiklikler = diff_alanlar(eski, rol.model_dump())
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "Rol", str(rol.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return rol
