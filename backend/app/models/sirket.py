# -*- coding: utf-8 -*-
"""models/sirket.py — Şirket (tenant). Faz 1'de her DB tam olarak bir Şirket satırı içerir.

`raporlu_politikasi`/`raporlu_esik_gun` — kullanıcı kararı (2026-07-04): Raporlu'nun
maaş etkisi (Devamsız gibi tam düşer / Yıllık İzin gibi hiç düşmez / ilk N gün ödenir
sonrası düşer) çalışan tipinden bağımsız, ŞİRKET GENELİNDE tek bir politika. Varsayılan
`hic_odeme` — bu oturuma kadarki mevcut davranışla birebir aynı, geriye dönük uyumlu."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc
from app.services.payroll_calc import RAPORLU_HIC_ODEME


class Sirket(SQLModel, table=True):
    __tablename__ = "sirket"

    id: Optional[int] = Field(default=None, primary_key=True)
    ad: str
    raporlu_politikasi: str = RAPORLU_HIC_ODEME  # "tam_ode" | "hic_odeme" | "n_gun_esigi"
    raporlu_esik_gun: int = 0  # yalnızca n_gun_esigi politikasında kullanılır
    created_at: datetime = Field(default_factory=simdi_utc)
