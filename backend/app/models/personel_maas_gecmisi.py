# -*- coding: utf-8 -*-
"""
models/personel_maas_gecmisi.py — Kişi bazlı maaş tarihçesi (etkin-tarihli).

Kullanıcı sorusu (2026-07-06): "maaşlara zam gelince onu sisteme nasıl alacağız?"
Kod taramasıyla bulunan gerçek açık: `Personel.maas` tek bir "güncel" değerdi,
hiçbir geçmiş tutmuyordu — `ozet()`/Excel export her zaman BUGÜNKÜ değeri
okuyordu, hangi geçmiş dönem hesaplanıyor olursa olsun. Birine zam yapılınca
geçmiş ayların bordrosu da sessizce (yanlışlıkla) yeni maaşla yeniden hesaplanıyordu.

Bu tablo, N.G için zaten çözülmüş olan `PersonelDonemAyar` desenine benzer ama
semantiği FARKLI: `PersonelDonemAyar` SADECE o dönem için bir istisnadır (başka
döneme sızmaz); maaş ise "bu dönemden İTİBAREN, bir sonraki değişikliğe kadar"
geçerlidir (etkin-tarihli/carry-forward). `efektif_maas()` (personel_filtre.py),
hedef dönemden önceki veya o döneme ait EN SON kaydı bulur.

Append-only — AuditLog gibi, UPDATE/DELETE kod seviyesinde yasak. Yanlış girilen
bir zam, yeni bir düzeltme kaydıyla telafi edilir, geçmiş kayıt silinmez.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.core.zaman import simdi_utc


class PersonelMaasGecmisi(SQLModel, table=True):
    __tablename__ = "personel_maas_gecmisi"
    __table_args__ = (UniqueConstraint("personel_id", "yil", "ay", name="uq_personel_maas_gecmisi"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    personel_id: int = Field(foreign_key="personel.id")
    yil: int
    ay: int                                       # bu yıl/ay ve sonrası için geçerli (bir sonraki kayda kadar)
    maas: float
    created_by_id: Optional[int] = Field(default=None, foreign_key="kullanici.id")
    created_at: datetime = Field(default_factory=simdi_utc)
