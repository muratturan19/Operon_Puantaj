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

import logging
import re
from copy import copy
from dataclasses import dataclass, field
from typing import Any, Optional

from openpyxl import load_workbook
from openpyxl.formula.translate import Translator
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.models.excel_mapping_schema import ExcelMappingConfig, ExcelSheetMapping

logger = logging.getLogger("operon_puantaj.excel")

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


def en_guncel_sheet(
    wb: Workbook,
    sheet_mapping: ExcelSheetMapping,
    once: Optional[tuple[int, int]] = None,
) -> Optional[Worksheet]:
    """Eşleşen sayfalar arasından en güncel (yıl, ay) olanı — yeni bir ay için
    şablon olarak kullanılır (bkz. yeni_ay_sayfasi_olustur).

    `once` verilirse (yeni ayın dönemi), o aydan ÖNCEKİ en güncel sayfa tercih
    edilir: bir ayın şablonu kendinden sonraki bir ay olmamalı. 2026-08-25'ten
    beri export ürettiği sayfaları master'a kalıcı yazdığı için bu mümkün hale
    geldi — Ağustos dosyada varken Temmuz export edilirse şablon Ağustos olur,
    Ağustos'ta işe girmiş personel Temmuz roster'ında belirirdi. Öncesinde hiç
    sayfa yoksa (ilk ay) en güncele düşülür.
    """
    en_guncel: Optional[tuple[Worksheet, tuple[int, int]]] = None
    once_en_guncel: Optional[tuple[Worksheet, tuple[int, int]]] = None
    for ws in list_matching_sheets(wb, sheet_mapping):
        donem = parse_sheet_donem(ws.title)
        if donem is None:
            continue
        if en_guncel is None or donem > en_guncel[1]:
            en_guncel = (ws, donem)
        if once is not None and donem < once and (once_en_guncel is None or donem > once_en_guncel[1]):
            once_en_guncel = (ws, donem)
    secilen = once_en_guncel or en_guncel
    return secilen[0] if secilen else None


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


def sayfayi_kronolojik_yerlestir(wb: Workbook, ws: Worksheet, donem: tuple[int, int]) -> None:
    """Yeni oluşturulan ay sayfasını kendi kronolojik yerine taşır.

    Bug (2026-08-25, müşteri şikâyeti): `copy_worksheet` sayfayı workbook'un EN
    SONUNA, "ÇALIŞAN LİSTESİ"/"servis" gibi yardımcı sekmelerden de sonra
    ekliyordu. 17 sekmelik dosyada güncel ay en sağda, ekran dışında kalıyordu.
    """
    hedef_index: Optional[int] = None
    for i, sayfa in enumerate(wb.worksheets):
        if sayfa is ws:
            continue
        sayfa_donemi = parse_sheet_donem(sayfa.title)
        if sayfa_donemi is not None and sayfa_donemi < donem:
            hedef_index = i
    if hedef_index is None:
        return
    mevcut = wb.index(ws)
    hedef = hedef_index + 1 if hedef_index < mevcut else hedef_index
    if hedef != mevcut:
        wb.move_sheet(ws, offset=hedef - mevcut)


def aktif_sayfa_yap(wb: Workbook, ws: Worksheet) -> None:
    """Dosya açıldığında bu sayfa görünsün.

    Bug (2026-08-25, ASIL ŞİKÂYET): export edilen dosyanın aktif sekmesi
    master'dan miras kalan "HAZİRAN 2026 ELDEN" idi. Kullanıcı Ağustos'u export
    edip dosyayı açtığında karşısına Haziran'ın elden ödeme tablosu geliyordu —
    "girdiğimiz tabloyu değil bambaşka bir şeyi çıktı alıyor" geri bildirimi
    birebir bu. Veri doğru yazılıyordu, yanlış olan açılış sekmesiydi.
    """
    wb.active = wb.index(ws)
    for sayfa in wb.worksheets:
        sayfa.sheet_view.tabSelected = sayfa is ws


def _toplam_araliklarini_genislet(ws: Worksheet, toplam_row: int, eski_son: int, yeni_son: int) -> None:
    """TOPLAM satırındaki `=SUM(E3:E55)` gibi aralıkların bitişini yeni satıra taşır.

    openpyxl `insert_rows` formülleri OTOMATİK kaydırmaz; bu yapılmazsa eklenen
    personelin satırı toplama dahil olmaz ve TOPLAM sessizce eksik çıkar.
    """
    desen = re.compile(r"(:\$?[A-Z]{1,3}\$?)" + str(eski_son) + r"(?![0-9])")
    for cell in ws[toplam_row]:
        if isinstance(cell.value, str) and cell.value.startswith("="):
            yeni_formul = desen.sub(lambda m: f"{m.group(1)}{yeni_son}", cell.value)
            if yeni_formul != cell.value:
                cell.value = yeni_formul


def roster_satiri_ekle(ws: Worksheet, mapping: ExcelMappingConfig, degerler: dict[str, Any]) -> Optional[int]:
    """Excel roster'ında satırı olmayan personel için TOPLAM'ın hemen üstüne satır açar.

    Bug (2026-08-25, SESSİZ VERİ KAYBI): uygulamadan eklenen personel Excel
    master'ın roster'ında bulunmadığı için export'ta `continue` ile atlanıyordu —
    ne hata ne uyarı. Girilen puantaj hiçbir yere yazılmıyordu (ör. RÜMEYSA
    TEMURAYAK, Ağustos 2026). Artık satır açılıyor: stil ve formüller son roster
    satırından kopyalanır, TOPLAM aralıkları genişletilir.
    """
    sm = mapping.sheet_mapping
    toplam_row = find_toplam_row(ws, sm)
    referans_row = toplam_row - 1
    if referans_row < sm.baslangic_satir:
        logger.warning("Roster boş, satır eklenemedi: %s / %r", ws.title, degerler.get("ad_soyad"))
        return None

    ws.insert_rows(toplam_row)
    yeni_row = toplam_row

    for cell in ws[referans_row]:
        hedef = ws.cell(row=yeni_row, column=cell.column)
        hedef._style = copy(cell._style)
        if isinstance(cell.value, str) and cell.value.startswith("="):
            hedef.value = Translator(cell.value, origin=cell.coordinate).translate_formula(hedef.coordinate)

    ws[f"{sm.kimlik_kolon_harfi}{yeni_row}"] = degerler.get("ad_soyad")
    for okuma in sm.okuma_alanlari:
        if okuma.kolon_harfi and okuma.hedef_alan != "ad_soyad" and okuma.hedef_alan in degerler:
            ws[f"{okuma.kolon_harfi}{yeni_row}"] = degerler[okuma.hedef_alan]

    _toplam_araliklarini_genislet(ws, toplam_row + 1, eski_son=referans_row, yeni_son=yeni_row)
    logger.info("Roster satırı eklendi: %s / %r -> satır %s", ws.title, degerler.get("ad_soyad"), yeni_row)
    return yeni_row


def _toplam_araliklarini_daralt(ws: Worksheet, toplam_row: int, eski_son: int, yeni_son: int) -> None:
    """`_toplam_araliklarini_genislet`'in tersi — satır silindiğinde TOPLAM aralığı kısalır."""
    desen = re.compile(r"(:\$?[A-Z]{1,3}\$?)" + str(eski_son) + r"(?![0-9])")
    for cell in ws[toplam_row]:
        if isinstance(cell.value, str) and cell.value.startswith("="):
            yeni_formul = desen.sub(lambda m: f"{m.group(1)}{yeni_son}", cell.value)
            if yeni_formul != cell.value:
                cell.value = yeni_formul


def roster_satirlarini_sil(ws: Worksheet, mapping: ExcelMappingConfig, satirlar: set[int]) -> int:
    """Verilen roster satırlarını sayfadan siler ve TOPLAM aralıklarını daraltır.

    Kullanıcı kararı (2026-08-25): dönem başlamadan önce işten ayrılmış personel
    o ayın sayfasında hiç görünmemeli. Önceden satırları duruyor ama Ç.GÜN'leri
    boş kalıyordu — müşteri sarı sütunu "rastgele dolmuş" olarak görüyordu.
    (Ay içinde ayrılan personel SİLİNMEZ; `personel_filtre.donemde_calisiyor_mu`
    kararı gereği çıktığı ayın sonuna kadar listede kalır.)

    Silme, satır numaralarını kaydırdığı için ÇAĞIRAN roster'ı yeniden okumalıdır.
    """
    if not satirlar:
        return 0
    sm = mapping.sheet_mapping
    toplam_row = find_toplam_row(ws, sm)
    eski_son = toplam_row - 1

    for satir in sorted(satirlar, reverse=True):   # alttan üste — üsttekilerin no'su kaymasın
        ws.delete_rows(satir)
        logger.info("Roster satırı silindi: %s / satır %s", ws.title, satir)

    _toplam_araliklarini_daralt(ws, toplam_row - len(satirlar), eski_son, eski_son - len(satirlar))
    return len(satirlar)
