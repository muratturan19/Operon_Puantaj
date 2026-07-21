# -*- coding: utf-8 -*-
"""api/routes/tatiller.py — Resmi tatil ekle/çıkar (Pazar zaten otomatik ×2, ayrı kayıt gerekmez)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import PUANTAJ_GOREBILIR, TATIL_YONETEBILIR
from app.core.security import require_permission
from app.models.rbac import Kullanici
from app.models.tatil import Tatil

router = APIRouter(prefix="/api/tatiller", tags=["tatiller"])


class TatilCreate(BaseModel):
    tarih: date
    aciklama: str | None = None


@router.get("", response_model=list[Tatil])
def listele(
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[Tatil]:
    return session.exec(
        select(Tatil).where(Tatil.sirket_id == current_user.sirket_id).order_by(Tatil.tarih)
    ).all()


@router.post("", response_model=Tatil, status_code=status.HTTP_201_CREATED)
def ekle(
    payload: TatilCreate,
    current_user: Kullanici = Depends(require_permission(TATIL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> Tatil:
    tatil = Tatil(sirket_id=current_user.sirket_id, kaynak="ozel", **payload.model_dump())
    session.add(tatil)
    session.commit()
    session.refresh(tatil)
    return tatil


@router.delete("/{tatil_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def sil(
    tatil_id: int,
    current_user: Kullanici = Depends(require_permission(TATIL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> None:
    tatil = session.get(Tatil, tatil_id)
    if tatil is None or tatil.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tatil bulunamadı")
    session.delete(tatil)
    session.commit()
