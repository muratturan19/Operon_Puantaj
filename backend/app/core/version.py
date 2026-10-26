# -*- coding: utf-8 -*-
"""
core/version.py — Uygulama sürümü, tek kaynak.

Sürümleme kuralı (2026-08-25'te tanımlandı): CHANGELOG'daki "Faz" numarası
sürümün MAJOR.MINOR'ıdır (Faz 4.9 → 4.9.x), PATCH ise aynı faz içindeki
düzeltmeleri sayar. CHANGELOG'a yeni bir başlık eklenince burası da güncellenir.

`frontend/src/config/surum.ts` bu değerin ikizidir ve tarayıcıya gömülür; ikisi
aynı kaynak ağaçtan derlendiği için normalde eşittirler. Eşit değillerse
kullanıcının tarayıcısında ESKİ bir arayüz yüklüdür (önbellek) — UI bunu
"Sayfayı yenileyin" uyarısıyla gösterir.
"""
from __future__ import annotations

SURUM = "4.9.6"
SURUM_TARIHI = "2026-10-26"
SURUM_ADI = "Faz 4.9 — SaaS'ta oturum yoksa Portal'a yönlendirme"
