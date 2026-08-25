# -*- coding: utf-8 -*-
"""
tests/test_excel_adapter.py — Gerçek BESIM.xlsx üzerinde round-trip testi.

Doğrular:
- read_roster BESIM'in HAZİRAN 2026 BANKA sayfasındaki gerçek personeli
  (çalışma tipi kolonu olmadan, varsayılan MY ile) doğru okur.
- write_export SADECE dokunulan satırlara yazar; dokunulmamış personelin
  E/L/J/K hücreleri BİT-BİRE-BİT aynı kalır (CLAUDE.md §7).
- ELDEN sayfaları ve diğer tüm sayfalar (formüller dahil) hiç değişmez.
- K hücresi FM.TL=0 durumunda formüle geri döner.
"""
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from app.models.excel_mapping_schema import ExcelMappingConfig
from app.services.excel_adapter import (
    aktif_sayfa_yap,
    en_guncel_sheet,
    find_toplam_row,
    list_matching_sheets,
    open_workbook,
    parse_sheet_donem,
    read_roster,
    roster_satiri_ekle,
    save_workbook,
    sayfayi_kronolojik_yerlestir,
    write_export,
    yeni_ay_sayfasi_olustur,
)
from app.services.payroll_calc import GunlukGiris, hesapla

BESIM_ORIJINAL = Path(__file__).resolve().parents[2] / "BESIM.xlsx"
MAPPING_JSON = Path(__file__).resolve().parents[1] / "app" / "data" / "seed" / "besim_mapping.json"
HAZIRAN_SHEET = "HAZİRAN 2026 BANKA"


@pytest.fixture
def besim_mapping() -> ExcelMappingConfig:
    return ExcelMappingConfig.model_validate(json.loads(MAPPING_JSON.read_text(encoding="utf-8")))


@pytest.fixture
def besim_copy(tmp_path) -> Path:
    """Orijinal dosyaya asla dokunmayız — her testte taze bir kopya kullanılır."""
    hedef = tmp_path / "BESIM_test.xlsx"
    shutil.copy(BESIM_ORIJINAL, hedef)
    return hedef


def test_read_roster_gercek_besim_dosyasi(besim_copy, besim_mapping):
    wb = open_workbook(str(besim_copy))
    sheets = list_matching_sheets(wb, besim_mapping.sheet_mapping)
    sheet_adlari = [ws.title for ws in sheets]

    assert HAZIRAN_SHEET in sheet_adlari
    assert not any("ELDEN" in ad.upper() for ad in sheet_adlari)  # ELDEN asla eşleşmemeli

    ws = wb[HAZIRAN_SHEET]
    kayitlar = read_roster(ws, besim_mapping)

    assert len(kayitlar) == 53  # ÇALIŞAN LİSTESİ ile tutarlı personel sayısı
    ilk = kayitlar[0]
    assert ilk.excel_satir == 3
    assert ilk.alanlar["ad_soyad"] == "BESİM IŞIKER"
    assert ilk.alanlar["maas"] == 50000
    assert ilk.alanlar["ng"] == 30
    assert ilk.alanlar["calisma_tipi_kodu"] == "MY"  # kolon yok → varsayılan_deger fallback


def test_toplam_satiri_doguru_bulunuyor(besim_copy, besim_mapping):
    wb = open_workbook(str(besim_copy))
    ws = wb[HAZIRAN_SHEET]
    toplam_row = find_toplam_row(ws, besim_mapping.sheet_mapping)
    assert ws[f"B{toplam_row}"].value.strip().upper() == "TOPLAM"


def test_export_sadece_dokunulan_satiri_degistirir(besim_copy, besim_mapping):
    wb = open_workbook(str(besim_copy))
    ws = wb[HAZIRAN_SHEET]

    # Dokunulmadan ÖNCEKİ tam sayfa görüntüsü — her hücreyi karşılaştıracağız.
    before = {
        f"{col}{row}": ws[f"{col}{row}"].value
        for row in range(1, ws.max_row + 2)
        for col in "ABCDEFGHIJKLMNOPQRSTUVW"
    }

    # Yalnızca satır 3'e (BESİM IŞIKER, maaş 50000) dokunuyoruz.
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 1), fm_saat=4.0),   # Pazartesi, ×1,5
        GunlukGiris(tarih=date(2026, 6, 7), fm_saat=3.0),   # Pazar, ×2
        GunlukGiris(tarih=date(2026, 6, 2), izin_saat=2.0),
    ]
    sonuc = hesapla(maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    sonuc_by_row = {
        3: {
            "cgun": sonuc.cgun,
            "izin_saat": sonuc.izin_saat,
            "fm_saat": sonuc.fm_saat,
            "fm_tl": sonuc.fm_tl,
        }
    }
    write_export(ws, besim_mapping, sonuc_by_row, dokunulan_satirlar={3})

    export_path = besim_copy.parent / "BESIM_export.xlsx"
    save_workbook(wb, str(export_path))

    wb2 = open_workbook(str(export_path))
    ws2 = wb2[HAZIRAN_SHEET]

    # Dokunulan satır beklenen değerlerle güncellendi mi?
    assert ws2["E3"].value == sonuc.cgun
    assert ws2["L3"].value == round(sonuc.izin_saat, 2)
    assert ws2["J3"].value == round(sonuc.fm_saat, 2)
    assert ws2["K3"].value == round(sonuc.fm_tl, 2)

    # Dokunulmamış TÜM diğer hücreler bit-bire-bit aynı mı? (row 4 dahil — K4 formül fallback'i)
    for row in range(1, ws2.max_row + 2):
        for col in "ABCDEFGHIJKLMNOPQRSTUVW":
            addr = f"{col}{row}"
            if row == 3 and col in ("E", "L", "J", "K"):
                continue  # bilerek değiştirdiğimiz tek satır/kolonlar
            assert ws2[addr].value == before[addr], f"Beklenmedik değişiklik: {addr}"


def test_dosyada_olmayan_ay_icin_yeni_sayfa_olusturulabilir(besim_copy, besim_mapping):
    """Bug (2026-07-06): dosyada TEMMUZ sayfası hiç yoktu (BESIM.xlsx yalnızca
    Ocak-Haziran içeriyor) — export bu ayı SESSİZCE atlıyordu. Artık en güncel
    (Haziran) sayfa şablon alınıp roster/format/formüller dahil kopyalanabiliyor.

    Kullanıcı geri bildirimi (2026-07-06, ikinci tur): ilk sürüm referans sayfayı
    OLDUĞU GİBİ kopyalıyordu — Haziran'a özel AVANS gibi manuel girdiler ve
    başlıktaki "HAZİRAN" metni de yeni aya taşınıyordu.
    Kullanıcı geri bildirimi (2026-07-06, üçüncü tur): ikinci düzeltme (mapping'in
    bilmediği HER kolonu temizlemek) de yanlıştı — Y.TL/MAAŞ/M.1/M.1.5/İZİN.TL/
    HAKEDİŞ/TOPLAM gibi FORMÜL kolonları da mapping'te yok ama bunlar temizlenince
    "tüm formülleri sildin" oldu. Bu test roster + FORMÜL kolonlarının (mapping'te
    olmasa bile) korunduğunu, sadece düz manuel değerlerin (AVANS) temizlendiğini
    ve başlık metninin güncellendiğini doğrular."""
    wb = open_workbook(str(besim_copy))
    assert "TEMMUZ 2026 BANKA" not in wb.sheetnames

    referans = en_guncel_sheet(wb, besim_mapping.sheet_mapping)
    assert referans.title == HAZIRAN_SHEET
    assert referans["F3"].value == "=C3/D3"  # Y.TL — mapping'te yok ama formül

    # Haziran'a özel manuel girdi simülasyonu (ör. avans) + başlık hücresi
    referans["P3"] = 7500  # AVANS kolonu — mapping'in hiç bilmediği DÜZ bir değer
    referans["A1"] = "HAZİRAN 2026 PUANTAJLARI"

    yeni_ws = yeni_ay_sayfasi_olustur(
        wb, referans, besim_mapping,
        referans_donem=(2026, 6), yeni_donem=(2026, 7),
        yeni_baslik="TEMMUZ 2026 BANKA",
    )
    assert "TEMMUZ 2026 BANKA" in wb.sheetnames

    # Roster (Haziran'dan kopyalanan) ve mapping'in kendi kolonları sağlam mı?
    roster = read_roster(yeni_ws, besim_mapping)
    assert len(roster) == 53
    assert roster[0].alanlar["ad_soyad"] == "BESİM IŞIKER"
    assert roster[0].alanlar["maas"] == 50000

    # Mapping'in HİÇ bilmediği ama FORMÜL olan kolonlar (Y.TL/MAAŞ/M.1/M.1.5/
    # İZİN.TL/HAKEDİŞ/TOPLAM) korunmuş olmalı — bunlar ay'a özel değil, yapısal.
    assert yeni_ws["F3"].value == "=C3/D3"
    assert yeni_ws["G3"].value == "=F3*E3"
    assert yeni_ws["H3"].value == "=F3/7.5"
    assert yeni_ws["I3"].value == "=H3*1.5"
    assert yeni_ws["M3"].value == "=L3*H3"
    assert yeni_ws["O3"].value == "=N3+K3+G3-M3"
    # K de FORMÜL olduğu için (yazma_alanı olmasına rağmen) korunur — write_export
    # zaten dokunulan satırlarda bunun üzerine yazacak.
    assert yeni_ws["K3"].value == "=J3*I3"
    # Mapping'in hiç bilmediği DÜZ bir değer (AVANS) temizlenmiş olmalı — Haziran'a
    # özel manuel girdi, otomatik taşınamaz.
    assert yeni_ws["P3"].value is None
    # Başlıktaki eski ay/yıl metni güncellenmiş olmalı.
    assert yeni_ws["A1"].value == "TEMMUZ 2026 PUANTAJLARI"

    # write_export bu satıra gerçekten yazınca formül-fallback davranışı hâlâ
    # doğru çalışıyor mu? (fm_tl=0 → K'ya sayı değil fallback formülü yazılır)
    write_export(yeni_ws, besim_mapping, {3: {"cgun": 30, "izin_saat": 0, "fm_saat": 0, "fm_tl": 0}}, {3})
    assert yeni_ws["K3"].value == "=J3*I3"


def test_diger_sayfalar_ve_elden_hic_degismez(besim_copy, besim_mapping):
    wb = open_workbook(str(besim_copy))
    ws = wb[HAZIRAN_SHEET]

    before_other_sheets = {
        name: {
            f"{col}{row}": wb[name][f"{col}{row}"].value
            for row in range(1, wb[name].max_row + 1)
            for col in "ABCDEFGHIJKLMNOPQRSTUVW"
        }
        for name in wb.sheetnames
        if name != HAZIRAN_SHEET
    }

    girisler = [GunlukGiris(tarih=date(2026, 6, 1), fm_saat=1.0)]
    sonuc = hesapla(maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())
    sonuc_by_row = {3: {"cgun": sonuc.cgun, "izin_saat": sonuc.izin_saat, "fm_saat": sonuc.fm_saat, "fm_tl": sonuc.fm_tl}}
    write_export(ws, besim_mapping, sonuc_by_row, dokunulan_satirlar={3})

    export_path = besim_copy.parent / "BESIM_export2.xlsx"
    save_workbook(wb, str(export_path))

    wb2 = open_workbook(str(export_path))
    for name, snapshot in before_other_sheets.items():
        for addr, val in snapshot.items():
            assert wb2[name][addr].value == val, f"{name}!{addr} beklenmedik şekilde değişti"


# ---------------------------------------------------------------------------
# 2026-08-25 üretim olayı regresyonları
# Müşteri: "normal puantajları giriyoruz, bazen personel de ekliyoruz, ama Excel
# çıktısı aldığımızda güncel girdiğimiz tabloyu değil bambaşka bir şeyi alıyoruz."
# ---------------------------------------------------------------------------


def _temmuz_sayfasi(wb, mapping):
    referans = en_guncel_sheet(wb, mapping.sheet_mapping)
    return yeni_ay_sayfasi_olustur(
        wb, referans, mapping,
        referans_donem=parse_sheet_donem(referans.title),
        yeni_donem=(2026, 7),
        yeni_baslik="TEMMUZ 2026 BANKA",
    )


def test_yeni_ay_sayfasi_kronolojik_yerine_tasinir(besim_copy, besim_mapping):
    """copy_worksheet sayfayı en sona — "servis" sekmesinden bile sonraya — koyuyordu."""
    wb = open_workbook(str(besim_copy))
    ws = _temmuz_sayfasi(wb, besim_mapping)
    assert wb.index(ws) == len(wb.worksheets) - 1  # copy_worksheet'in ham davranışı

    sayfayi_kronolojik_yerlestir(wb, ws, (2026, 7))

    assert wb.sheetnames.index("TEMMUZ 2026 BANKA") == wb.sheetnames.index("HAZİRAN 2026 ELDEN") + 1
    assert wb.sheetnames.index("TEMMUZ 2026 BANKA") < wb.sheetnames.index("servis")


def test_export_dosyasi_yazilan_ay_sekmesinde_acilir(besim_copy, besim_mapping, tmp_path):
    """ASIL ŞİKÂYET: dosya master'dan miras kalan "HAZİRAN 2026 ELDEN" sekmesinde açılıyordu."""
    wb = open_workbook(str(besim_copy))
    assert wb.active.title == "HAZİRAN 2026 ELDEN"  # hatanın kaynağı

    ws = _temmuz_sayfasi(wb, besim_mapping)
    aktif_sayfa_yap(wb, ws)

    hedef = tmp_path / "export.xlsx"
    save_workbook(wb, str(hedef))

    yeniden = open_workbook(str(hedef))
    assert yeniden.active.title == "TEMMUZ 2026 BANKA"
    assert [s.title for s in yeniden.worksheets if s.sheet_view.tabSelected] == ["TEMMUZ 2026 BANKA"]


def test_roster_satiri_ekle_yeni_personeli_yazilabilir_yapar(besim_copy, besim_mapping):
    """SESSİZ VERİ KAYBI: roster'da satırı olmayan personel export'ta atlanıyordu."""
    wb = open_workbook(str(besim_copy))
    ws = _temmuz_sayfasi(wb, besim_mapping)

    once = read_roster(ws, besim_mapping)
    toplam_once = find_toplam_row(ws, besim_mapping.sheet_mapping)
    assert not any(k.alanlar["ad_soyad"] == "YENİ PERSONEL" for k in once)

    yeni_satir = roster_satiri_ekle(
        ws, besim_mapping, {"ad_soyad": "YENİ PERSONEL", "maas": 31000, "ng": 31}
    )

    assert yeni_satir == toplam_once  # TOPLAM'ın hemen üstüne açıldı
    sonra = read_roster(ws, besim_mapping)
    assert len(sonra) == len(once) + 1
    assert sonra[-1].alanlar["ad_soyad"] == "YENİ PERSONEL"
    assert sonra[-1].alanlar["maas"] == 31000
    assert sonra[-1].alanlar["ng"] == 31
    # Satır kendi hesap formüllerini referans satırdan çevrilmiş olarak taşımalı
    assert ws[f"F{yeni_satir}"].value == f"=C{yeni_satir}/D{yeni_satir}"


def test_roster_satiri_ekle_toplam_araligini_genisletir(besim_copy, besim_mapping):
    """openpyxl insert_rows formülleri kaydırmaz; TOPLAM eksik toplardı."""
    wb = open_workbook(str(besim_copy))
    ws = _temmuz_sayfasi(wb, besim_mapping)
    toplam_once = find_toplam_row(ws, besim_mapping.sheet_mapping)
    assert ws[f"E{toplam_once}"].value == f"=SUM(E3:E{toplam_once - 1})"

    yeni_satir = roster_satiri_ekle(ws, besim_mapping, {"ad_soyad": "YENİ PERSONEL", "maas": 1, "ng": 30})

    toplam_sonra = find_toplam_row(ws, besim_mapping.sheet_mapping)
    assert toplam_sonra == toplam_once + 1
    assert ws[f"E{toplam_sonra}"].value == f"=SUM(E3:E{yeni_satir})"  # yeni satır toplama dahil
