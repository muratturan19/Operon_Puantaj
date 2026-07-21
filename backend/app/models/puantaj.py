# -*- coding: utf-8 -*-
"""
models/puantaj.py — PuantajGirisi: bir personelin bir gündeki durum kaydı.

Prototipteki `entries[row|ymd]` sözlüğünün DB karşılığı — mevcut-durum tablosu.
Geçmiş değişiklikler burada değil, AuditLog'da tutulur (bu tablo yalnızca
"şu an ne doğru" bilgisini taşır, append-only değildir — upsert edilir).

`gun_durumu` — tam gün statüsü (kullanıcı geri bildirimi, 2026-07-04):
  None          → normal gün, izin_saat/fm_saat saatlik girilebilir
  "devamsiz"    → Ç.GÜN'den düşer, maaştan düşer (mevcut "Gelmedi" — sol tık)
  "yillik_izin" → Ç.GÜN'den DÜŞMEZ, maaştan DÜŞMEZ (tam ödenir) — kesin kural
  "raporlu"     → VARSAYILAN: "devamsiz" gibi Ç.GÜN'den düşer, maaştan düşer
                  (kullanıcı kararı: "defaultta raporda para ödenmez olsun, sonra
                  değiştirebiliriz"). Ayrı `gun_durumu` değeri olarak izlenir —
                  grid'de ayrı renk, özet kolonunda ayrı gün sayısı; sadece MAAŞ
                  ETKİSİ devamsız ile aynı. Şirkete göre ayarlanabilir gerçek
                  politika (N gün eşiği vb.) henüz yok (bkz. ROADMAP.md).
gun_durumu set edildiğinde izin_saat=fm_saat=0 olmak ZORUNDA (tam gün statüsü,
saatlik girişle karışmaz — kullanıcı onayı: "hayır, tam gün statüsü").
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class PuantajGirisi(SQLModel, table=True):
    __tablename__ = "puantaj_girisi"
    __table_args__ = (UniqueConstraint("personel_id", "tarih", name="uq_puantaj_personel_tarih"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    personel_id: int = Field(foreign_key="personel.id")
    donem_id: int = Field(foreign_key="donem.id")
    tarih: date
    gun_durumu: Optional[str] = None  # None | "devamsiz" | "yillik_izin" | "raporlu"
    izin_saat: float = 0
    fm_saat: float = 0
    created_by_id: Optional[int] = Field(default=None, foreign_key="kullanici.id")
    updated_by_id: Optional[int] = Field(default=None, foreign_key="kullanici.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
