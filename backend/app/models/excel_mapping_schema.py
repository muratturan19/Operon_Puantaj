# -*- coding: utf-8 -*-
"""
models/excel_mapping_schema.py — Excel eşleme config'i (Pydantic, DB tablosu değil).

`E:\\Mira\\AILens_PI\\backend\\app\\models\\mapping.py`'deki FieldMapping/AilensMapping
deseninin Excel-kolonu uyarlaması. Amaç: müşterinin Excel düzeni HİÇBİR ZAMAN
kod içine hardcode edilmez (CLAUDE.md §3) — bu config, `excel_adapter.py`'nin
girdisidir. BESIM.xlsx için somut bir örneği `data/seed/besim_mapping.json`'da.

Import/export mapping'i CLAUDE.md §7'de kapanan karara göre SİMETRİK — aynı
config hem okuma hem yazma alanlarını taşır (ayrı import/export objesi yok).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ExcelOkumaAlani(BaseModel):
    """Roster/personel bilgisini Excel'den okurken hangi alan hangi kolondan gelir."""

    hedef_alan: str                              # "ad_soyad" | "maas" | "ng" | "calisma_tipi_kodu"
    kolon_harfi: Optional[str] = None             # None = kolon yok, varsayilan_deger kullanılır
    varsayilan_deger: Optional[Any] = None        # BESIM'in calisma_tipi_kodu durumu — kolon yok
    guven: float = 1.0
    not_: str = ""


class ExcelYazmaAlani(BaseModel):
    """Hesaplanan sonucu Excel'e yazarken hangi alan hangi kolona, boşken ne olur."""

    hedef_alan: str                               # "cgun" | "izin_saat" | "fm_saat" | "fm_tl"
    kolon_harfi: str
    sifirsa: Literal["null", "formula", "zero"] = "zero"
    fallback_formula_sablonu: Optional[str] = None  # ör. "{fm_saat_kolon}{row}*{oran_kolon}{row}"


class ExcelSheetMapping(BaseModel):
    sheet_ad_icerir: str = "BANKA"
    sheet_ad_haric: list[str] = Field(default_factory=lambda: ["ELDEN"])
    baslangic_satir: int = 3
    toplam_satir_etiketi: str = "TOPLAM"
    kimlik_kolon_harfi: str = "B"                 # personel adı kolonu — TOPLAM'ı bu kolonda arar
    fm_saat_kolon: str = "J"
    oran_kolon: str = "I"                          # K-cell formula fallback'i (=J*I) için
    okuma_alanlari: list[ExcelOkumaAlani]
    yazma_alanlari: list[ExcelYazmaAlani]


class ExcelMappingConfig(BaseModel):
    sablon_versiyon: str = "1.0"
    musteri_adi: str
    durum: Literal["draft", "approved"] = "draft"
    sheet_mapping: ExcelSheetMapping
    notlar: list[str] = Field(default_factory=list)
