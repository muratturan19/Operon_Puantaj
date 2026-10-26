# -*- coding: utf-8 -*-
"""models/personel.py — Personel, bir ÇalışanTipi'ne atanır.

`aktif` artık ayrı bir sütun DEĞİL — kullanıcı geri bildirimi (2026-07-04):
"giriş çıkışlar çok olur, değişiklik yapılan gün itibarı ile geçerli olmalı"
(elle işaretlenen bir bayrak yerine tarihe dayalı, gerçek işe giriş/çıkış
tarihleri). `aktif` artık `isten_cikis_tarihi`'nden türetilir — iki ayrı
kaynağın (bayrak + tarih) birbirinden sapma riski ortadan kalkar.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc


class Personel(SQLModel, table=True):
    __tablename__ = "personel"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    ad_soyad: str
    calisma_tipi_id: int = Field(foreign_key="calisma_tipi.id")
    maas: float
    ng: int = 30                                    # N.G — kişi bazında Excel'den gelir
    excel_kaynak_satir: Optional[int] = None          # BANKA sayfasındaki orijinal satır no (round-trip eşleme)
    ise_baslama_tarihi: Optional[date] = None         # None = takip başlamadan önce zaten işe alınmış
    isten_cikis_tarihi: Optional[date] = None         # son çalışılan gün (dahil); None = hâlâ çalışıyor
    created_at: datetime = Field(default_factory=simdi_utc)
    updated_at: Optional[datetime] = None

    @property
    def aktif(self) -> bool:
        return self.isten_cikis_tarihi is None
