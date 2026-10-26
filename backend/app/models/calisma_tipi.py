# -*- coding: utf-8 -*-
"""
models/calisma_tipi.py — Çalışan Tipi (Beyaz Yaka / Mavi Yaka / özel).

Bu, parametrizasyonun TEK mekanizmasıdır (CLAUDE.md §7 — üç katmanlı
sistem-varsayılanı/şirket/kişi hiyerarşisi fikri kullanıcı tarafından
reddedildi). Şirket "+Ekle" ile yeni tip tanımlayabilir; her tipin kendi
günlük saat / haftalık gün parametresi olur ve hesap motoruna (payroll_calc)
bu parametre üzerinden girer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc


class CalismaTipi(SQLModel, table=True):
    __tablename__ = "calisma_tipi"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    kod: str = Field(index=True)      # "BY" | "MY" | özel
    ad: str
    gunluk_saat: float = 7.5
    haftalik_gun: int = 6
    # FM (fazla mesai) oranları — kullanıcı kararı (2026-07-04): "her kurumun farklı yaklaşımı
    # olabilir" endişesine karşılık, önceden payroll_calc.py'de sabit 1,5×/2× idi, artık
    # Çalışma Tipi bazında ayarlanabilir. Varsayılanlar mevcut davranışla birebir aynı.
    hafta_ici_fm_orani: float = 1.5
    hafta_sonu_fm_orani: float = 2.0
    # Kullanıcı kararı (2026-07-05, internet araştırmasıyla desteklendi — İş Kanunu asgari
    # %50/%100, toplu iş sözleşmeleri daha yüksek ve resmi tatili hafta tatilinden AYRI
    # oranla ele alabiliyor): resmi tatil artık hafta_sonu_fm_orani'ndan bağımsız kendi
    # oranına sahip. Varsayılan hafta_sonu_fm_orani ile aynı (mevcut davranış korunur).
    resmi_tatil_fm_orani: float = 2.0
    # Hangi gün(ler) bu tip için "hafta tatili" (dinlenme günü) sayılır — weekday() ile aynı
    # kodlama (0=Pzt..6=Paz). Önceden kodda HER ZAMAN Pazar (6) sabitti; artık 5-gün çalışan
    # bir tip (ör. BY, Cumartesi de tatil) gibi farklı düzenlere göre ayarlanabilir.
    hafta_tatili_gunleri: list[int] = Field(default_factory=lambda: [6], sa_column=Column(JSON))
    aktif: bool = True
    created_at: datetime = Field(default_factory=simdi_utc)
