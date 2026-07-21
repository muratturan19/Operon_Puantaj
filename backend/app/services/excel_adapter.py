# -*- coding: utf-8 -*-
"""
services/excel_adapter.py — Mapping-driven Excel okuma/yazma.

Müşterinin Excel düzeni hiçbir zaman burada hardcode edilmez (CLAUDE.md §3) —
tüm kolon/satır bilgisi bir `ExcelMappingConfig`'ten gelir. `Puantaj.html`'in
`scanPeople`/`hesaplaGen`/`exportBtn` mantığıyla birebir davranış hedefler:
- personel tespiti: kimlik kolonunda "TOPLAM" etiketine kadar satır tara
- export: yalnızca dokunulan satırlara yazılır, dokunulmamış personel
  "tam maaş aldı" anlamına gelir ve hiç değiştirilmez
- sıfır/boş değer davranışı alan bazında (null/formula/zero) mapping'ten gelir
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.models.excel_mapping_schema import ExcelMappingConfig, ExcelSheetMapping

TR_AYLAR = [
    "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
    "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK",
]
_YIL_PATTERN = re.compile(r"(20\d\d)")


def parse_sheet_donem(sheet_name: str) -> Optional[tuple[int, int]]:
    """`Puantaj.html`'deki `parseSheetName`'in birebir karşılığı: 'HAZİRAN 2026 BANKA' → (2026, 6)."""
    up = sheet_name.upper()
    ay = next((i + 1 for i, ad in enumerate(TR_AYLAR) if ad in up), None)
    yil_match = _YIL_PATTERN.search(up)
    yil = int(yil_match.group(1)) if yil_match else None
    if ay is None or yil is None:
        return None
    return (yil, ay)


@dataclass
class RosterKaydi:
    """Bir Excel satırından okunan ham personel kaydı — DB'ye yazmadan önceki ara adım."""

    excel_satir: int
    alanlar: dict[str, Any] = field(default_factory=dict)


def open_workbook(path: str) -> Workbook:
    """Formülleri korumak için `data_only=False` zorunlu (openpyxl varsayılanı zaten bu)."""
    wb = load_workbook(path, data_only=False)
    return wb


def save_workbook(wb: Workbook, path: str) -> None:
    # openpyxl formülleri otomatik recalculate etmez — Excel/LibreOffice açılışta
    # yeniden hesaplasın diye stale cache'i geçersiz kılıyoruz.
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)


def list_matching_sheets(wb: Workbook, sheet_mapping: ExcelSheetMapping) -> list[Worksheet]:
    """`Puantaj.html`'deki `bankaSheets` filtresinin birebir karşılığı."""
    icerir = sheet_mapping.sheet_ad_icerir.upper()
    haric = [h.upper() for h in sheet_mapping.sheet_ad_haric]
    return [
        ws
        for ws in wb.worksheets
        if icerir in ws.title.upper() and not any(h in ws.title.upper() for h in haric)
    ]


def en_guncel_sheet(wb: Workbook, sheet_mapping: ExcelSheetMapping) -> Optional[Worksheet]:
    """Eşleşen sayfalar arasından en güncel (yıl, ay) olanı — yeni bir ay için
    şablon olarak kullanılır (bkz. yeni_ay_sayfasi_olustur)."""
    en_guncel: Optional[tuple[Worksheet, tuple[int, int]]] = None
    for ws in list_matching_sheets(wb, sheet_mapping):
        donem = parse_sheet_donem(ws.title)
        if donem is None:
            continue
        if en_guncel is None or donem > en_guncel[1]:
            en_guncel = (ws, donem)
    return en_guncel[0] if en_guncel else None


def yeni_ay_sayfasi_olustur(
    wb: Workbook,
    referans_ws: Worksheet,
    mapping: ExcelMappingConfig,
    referans_donem: tuple[int, int],
    yeni_donem: tuple[int, int],
    yeni_baslik: str,
) -> Worksheet:
    """Bug (2026-07-06): dosyada henüz sayfası olmayan bir ay için export
    SESSİZCE o dönemi atlıyordu. İlk düzeltme (referans sayfayı OLDUĞU GİBİ
    kopyalamak) YANLIŞ çıktı — kullanıcı geri bildirimi: "o avans çıkışları
    filan hazirana ait, başlık da hâlâ haziran". İKİNCİ düzeltme (mapping'in
    bilmediği HER kolonu temizlemek) de YANLIŞ çıktı — kullanıcı geri bildirimi:
    "tüm formülleri sildin haziran'dan" — Y.TL/MAAŞ/M.1/M.1.5/İZİN.TL/HAKEDİŞ/
    TOPLAM gibi kolonlar mapping'te yok ama FORMÜL (aynı satırdaki diğer
    hücrelerden otomatik hesaplanan yapı), önceki ayın "manuel girdisi" DEĞİL —
    bunlar temizlenirse tüm hesap zinciri kopar. Doğru kural:
      1. Roster satırlarında (baslangic_satir..toplam_satir), FORMÜL olan HER
         hücre (değeri "=" ile başlayan) HER ZAMAN korunur — hangi kolonda
         olursa olsun, çünkü formül otomatik hesaplanan yapıdır, ay'a özel
         manuel veri değildir.
      2. Formül OLMAYAN hücrelerden sadece mapping'in bildiği kimlik/roster
         kolonları (kimlik_kolon_harfi + okuma_alanlari) korunur — avans/icra/
         bes/prim gibi düz SAYI/metin değerleri (önceki ayın manuel girdileri,
         otomatik taşınamaz) VE `yazma_alanlari` kolonlarının düz varsayılan
         değerleri (ör. Ç.GÜN'ün statik "30"u) temizlenir; export zaten
         yalnızca dokunulan satırlara yazar.
      3. Sayfadaki TÜM hücrelerde eski ay+yıl metni ("HAZİRAN 2026") yeni ay+yıl
         ("TEMMUZ 2026") ile değiştiriliyor — başlık hücresi mapping'in bilmediği
         serbest bir metin olduğu için konumunu bilmiyoruz, metin ara/değiştir
         ile buluyoruz.
    """
    yeni_ws = wb.copy_worksheet(referans_ws)
    yeni_ws.title = yeni_baslik

    sm = mapping.sheet_mapping
    toplam_row = find_toplam_row(yeni_ws, sm)
    korunacak_kolonlar = {sm.kimlik_kolon_harfi.upper()} | {
        o.kolon_harfi.upper() for o in sm.okuma_alanlari if o.kolon_harfi
    }

    def _formul_mu(deger: Any) -> bool:
        return isinstance(deger, str) and deger.startswith("=")

    for row in range(sm.baslangic_satir, toplam_row):
        for cell in yeni_ws[row]:
            if _formul_mu(cell.value):
                continue  # formül — hangi kolonda olursa olsun korunur
            if cell.column_letter.upper() not in korunacak_kolonlar:
                cell.value = None

    eski_ay_yil = f"{TR_AYLAR[referans_donem[1] - 1]} {referans_donem[0]}"
    yeni_ay_yil = f"{TR_AYLAR[yeni_donem[1] - 1]} {yeni_donem[0]}"
    for row in yeni_ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and eski_ay_yil in cell.value.upper():
                cell.value = cell.value.upper().replace(eski_ay_yil, yeni_ay_yil)

    return yeni_ws


def _cell_text(ws: Worksheet, col_letter: str, row: int) -> str:
    value = ws[f"{col_letter}{row}"].value
    return str(value).strip() if value is not None else ""


def _cell_value(ws: Worksheet, col_letter: str, row: int) -> Any:
    return ws[f"{col_letter}{row}"].value


def find_toplam_row(ws: Worksheet, sheet_mapping: ExcelSheetMapping) -> int:
    """Kimlik kolonunda `toplam_satir_etiketi`ne (varsayılan "TOPLAM") rastlayan satır."""
    etiket = sheet_mapping.toplam_satir_etiketi.upper()
    for row in range(1, ws.max_row + 1):
        if _cell_text(ws, sheet_mapping.kimlik_kolon_harfi, row).upper() == etiket:
            return row
    return ws.max_row + 1  # bulunamazsa Puantaj.html'deki gibi sona düş


def read_roster(ws: Worksheet, mapping: ExcelMappingConfig) -> list[RosterKaydi]:
    """
    `scanPeople` mantığı: `baslangic_satir`'dan `toplam_satir_etiketi`ne kadar
    tara. Kimlik kolonu boş olan satırlar atlanır (ara boşluklar, alt notlar vb.).
    """
    sm = mapping.sheet_mapping
    toplam_row = find_toplam_row(ws, sm)

    kayitlar: list[RosterKaydi] = []
    for row in range(sm.baslangic_satir, toplam_row):
        kimlik = _cell_text(ws, sm.kimlik_kolon_harfi, row)
        if not kimlik:
            continue

        alanlar: dict[str, Any] = {}
        for okuma in sm.okuma_alanlari:
            if okuma.kolon_harfi:
                deger = _cell_value(ws, okuma.kolon_harfi, row)
                alanlar[okuma.hedef_alan] = deger if deger is not None else okuma.varsayilan_deger
            else:
                alanlar[okuma.hedef_alan] = okuma.varsayilan_deger

        kayitlar.append(RosterKaydi(excel_satir=row, alanlar=alanlar))

    return kayitlar


def write_export(
    ws: Worksheet,
    mapping: ExcelMappingConfig,
    sonuc_by_row: dict[int, dict[str, Any]],
    dokunulan_satirlar: set[int],
) -> None:
    """
    Yalnızca `dokunulan_satirlar` içindeki satırlara yazılır (CLAUDE.md §7 —
    dokunulmamış personel "eksik çalışma da mesai de yok, tam maaş aldı"
    demektir; kullanıcı onayı). Her `yazma_alani` için `sifirsa` davranışı:
      - "zero"    → değer ne olursa olsun yaz (varsayılan 0 anlamlı)
      - "null"    → değer boş/0 ise hücreyi temizle (None), aksi halde yaz
      - "formula" → değer boş/0 ise fallback formülünü yaz, aksi halde
                    yuvarlanmış sayıyı yaz (K-cell `=J*I` davranışı)
    """
    sm = mapping.sheet_mapping

    for row in dokunulan_satirlar:
        sonuc = sonuc_by_row.get(row, {})
        for yazma in sm.yazma_alanlari:
            ham_deger = sonuc.get(yazma.hedef_alan)
            hedef_hucre = ws[f"{yazma.kolon_harfi}{row}"]

            if yazma.sifirsa == "zero":
                hedef_hucre.value = round(ham_deger, 2) if isinstance(ham_deger, float) else ham_deger
            elif yazma.sifirsa == "null":
                hedef_hucre.value = (
                    round(ham_deger, 2) if ham_deger else None
                )
            elif yazma.sifirsa == "formula":
                if ham_deger:
                    hedef_hucre.value = round(ham_deger, 2)
                elif yazma.fallback_formula_sablonu:
                    formul = yazma.fallback_formula_sablonu.format(
                        fm_saat_kolon=sm.fm_saat_kolon, oran_kolon=sm.oran_kolon, row=row
                    )
                    hedef_hucre.value = f"={formul}"
                else:
                    hedef_hucre.value = None
