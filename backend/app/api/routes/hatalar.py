# -*- coding: utf-8 -*-
"""api/routes/hatalar.py — Sunucu hata kayıtları (salt okunur).

Yazma yalnızca services/hata_kaydi.py üzerinden, global exception handler'dan
yapılır. Bu uç nokta müşteriye "E-xxxxxxxx" takip kodunu sorup kaydı tek
hamlede bulabilmek içindir.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import AUDIT_GOREBILIR
from app.core.security import require_permission
from app.models.hata import HataKaydi
from app.models.rbac import Kullanici

router = APIRouter(prefix="/api/hatalar", tags=["hatalar"])


class HataKaydiResponse(BaseModel):
    id: int
    istek_id: str
    zaman: str
    yol: str
    metod: str
    sorgu: Optional[str] = None
    kullanici: Optional[str] = None
    hata_tipi: str
    mesaj: str
    traceback_metni: Optional[str] = None


@router.get("", response_model=list[HataKaydiResponse])
def listele(
    istek_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    current_user: Kullanici = Depends(require_permission(AUDIT_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[HataKaydiResponse]:
    sorgu = select(HataKaydi)
    if istek_id:
        sorgu = sorgu.where(HataKaydi.istek_id == istek_id)
    sorgu = sorgu.order_by(HataKaydi.zaman.desc()).limit(limit)
    return [
        HataKaydiResponse(
            id=k.id,
            istek_id=k.istek_id,
            zaman=k.zaman.isoformat(),
            yol=k.yol,
            metod=k.metod,
            sorgu=k.sorgu,
            kullanici=k.kullanici,
            hata_tipi=k.hata_tipi,
            mesaj=k.mesaj,
            traceback_metni=k.traceback_metni,
        )
        for k in session.exec(sorgu).all()
    ]
