# -*- coding: utf-8 -*-
"""
models/personel_donem_ayar.py — Kişi bazlı N.G istisnası, SADECE ilgili dönem için.

Kullanıcı kararı (2026-07-06): N.G varsayılan olarak dönemin takvim gün sayısı
(`Donem.ng`) — ama bir kişi için özel bir ay istisna gerekebilir (ör. ay ortasında
özel bir anlaşma). Bu satır varsa o (personel, dönem) çifti için `Donem.ng` yerine
buradaki değer kullanılır; yoksa dönemin varsayılanına dönülür. Kayıt kalıcı DEĞİL
her ay silinip yeniden girilmez — sadece o dönem için geçerlidir, başka bir döneme
sızmaz (bkz. app/services/personel_filtre.py::efektif_ng).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.core.zaman import simdi_utc


class PersonelDonemAyar(SQLModel, table=True):
    __tablename__ = "personel_donem_ayar"
    __table_args__ = (UniqueConstraint("personel_id", "donem_id", name="uq_personel_donem_ayar"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    personel_id: int = Field(foreign_key="personel.id")
    donem_id: int = Field(foreign_key="donem.id")
    ng: int
    created_at: datetime = Field(default_factory=simdi_utc)
