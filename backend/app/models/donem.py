# -*- coding: utf-8 -*-
"""models/donem.py — Dönem (yıl/ay). Excel export hedefi sheet adını da taşır."""
from __future__ import annotations

import calendar
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Donem(SQLModel, table=True):
    __tablename__ = "donem"
    __table_args__ = (UniqueConstraint("sirket_id", "yil", "ay", name="uq_donem_sirket_yil_ay"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    yil: int
    ay: int                                     # 1-12
    excel_sheet_adi: Optional[str] = None        # ör. "HAZİRAN 2026 BANKA" — export hedefi
    # Bu dönemin varsayılan N.G'si — kullanıcı kararı (2026-07-06): "kişi bazında
    # Ç.GÜN değişmiyor, ay ay komple değişebiliyor ama aynı ay içinde herkes
    # aynı" — önceden Personel.ng kişi bazında sabitti ve ay değişse de
    # güncellenmiyordu. Artık dönem oluşturulurken takvim gün sayısına göre
    # otomatik hesaplanır (bkz. donemler.py::getir_veya_olustur), kişi bazlı
    # istisnalar PersonelDonemAyar tablosundan gelir.
    ng: int = Field(default_factory=lambda: 30)

    @staticmethod
    def takvim_gun_sayisi(yil: int, ay: int) -> int:
        return calendar.monthrange(yil, ay)[1]
