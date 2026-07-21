# -*- coding: utf-8 -*-
"""
scripts/excel_kesif.py — Onboarding keşif aracı: yeni bir müşteri Excel'ini
mapping çıkarmadan ÖNCE yapılandırılmış biçimde döker.

Kullanım (Murat + Claude, CLAUDE.md §3'teki onboarding sohbeti sırasında):
    python scripts/excel_kesif.py "path/to/musteri.xlsx"
    python scripts/excel_kesif.py "path/to/musteri.xlsx" --sheet-icerir BORDRO --kimlik-kolon C

NE YAPAR: mevcut `excel_adapter.py` fonksiyonlarını (sheet filtreleme, TOPLAM
satırı bulma) aynen kullanarak sheet'leri, header adaylarını, TOPLAM satırının
nerede bulunduğunu ve ham örnek satırları döker.

NE YAPMAZ: hiçbir alanı (ad_soyad/maaş/ng/...) otomatik TAHMİN ETMEZ — CLAUDE.md
kuralı ("tahmin etme, uydurma yasak") burada da geçerli. Çıktı, mapping kararını
verecek insan+Claude konuşmasına HAM ZEMİN sağlar; nihai `ExcelMappingConfig`
JSON'unu bu araç değil, o konuşma üretir.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows konsolu varsayılan olarak cp1254/cp1252 kullanır — Türkçe karakterler
# ve ✅ gibi işaretler bununla bozulur/patlar. CLAUDE.md §9: "UTF-8 zorunlu."
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.excel_mapping_schema import ExcelSheetMapping  # noqa: E402
from app.services.excel_adapter import find_toplam_row, list_matching_sheets, open_workbook  # noqa: E402


def _kolon_harfleri(n: int) -> list[str]:
    from openpyxl.utils import get_column_letter
    return [get_column_letter(i) for i in range(1, n + 1)]


def _satir_dokumu(ws, satir: int, kolon_sayisi: int) -> str:
    harfler = _kolon_harfleri(kolon_sayisi)
    degerler = [f"{h}={ws[f'{h}{satir}'].value!r}" for h in harfler]
    return f"  satır {satir}: " + " | ".join(degerler)


def kesfet(dosya_yolu: str, sheet_icerir: str, sheet_haric: list[str], kimlik_kolon: str,
           baslangic_satir: int, toplam_etiket: str, onizleme_satir: int) -> None:
    wb = open_workbook(dosya_yolu)

    sm = ExcelSheetMapping(
        sheet_ad_icerir=sheet_icerir,
        sheet_ad_haric=sheet_haric,
        baslangic_satir=baslangic_satir,
        toplam_satir_etiketi=toplam_etiket,
        kimlik_kolon_harfi=kimlik_kolon,
        okuma_alanlari=[],
        yazma_alanlari=[],
    )

    tum_sheetler = wb.sheetnames
    eslesen = list_matching_sheets(wb, sm)
    eslesen_adlar = {ws.title for ws in eslesen}

    print(f"# Excel Keşif Raporu — {dosya_yolu}\n")
    print(f"Toplam sheet sayısı: {len(tum_sheetler)}")
    print(f"Filtre: sheet adı '{sheet_icerir}' içerir, {sheet_haric} hariç, kimlik kolonu '{kimlik_kolon}'\n")

    print("## Sheet Listesi\n")
    for ad in tum_sheetler:
        durum = "✅ eşleşti (roster adayı)" if ad in eslesen_adlar else "— eşleşmedi"
        print(f"- {ad}  [{durum}]")

    if not eslesen:
        print("\n⚠️  Hiçbir sheet eşleşmedi — filtre parametrelerini (--sheet-icerir vb.) gözden geçirin.")
        return

    for ws in eslesen:
        print(f"\n## Sheet: {ws.title}\n")
        print(f"Boyut: {ws.max_row} satır × {ws.max_column} kolon\n")

        toplam_row = find_toplam_row(ws, sm)
        if toplam_row > ws.max_row:
            print(f"⚠️  '{toplam_etiket}' etiketi kimlik kolonunda ({kimlik_kolon}) bulunamadı — "
                  f"personel aralığı belirsiz, sheet sonuna kadar taranmış olurdu.\n")
        else:
            personel_sayisi = toplam_row - baslangic_satir
            print(f"'{toplam_etiket}' satırı: {toplam_row} → tahmini personel sayısı: {personel_sayisi} "
                  f"(satır {baslangic_satir}–{toplam_row - 1})\n")

        print("### Başlık adayı satırlar (1 — başlangıç_satır-1):")
        for satir in range(1, baslangic_satir):
            print(_satir_dokumu(ws, satir, ws.max_column))

        print(f"\n### İlk {onizleme_satir} personel satırı (ham):")
        bitis = min(baslangic_satir + onizleme_satir, toplam_row)
        for satir in range(baslangic_satir, bitis):
            print(_satir_dokumu(ws, satir, ws.max_column))

    print("\n---")
    print("Not: Bu rapor hiçbir alanı otomatik eşlemedi. Hangi kolonun ad_soyad/maaş/ng/")
    print("çalışma tipi/FM saat/izin saat olduğuna insan+Claude birlikte karar verir,")
    print("sonra `ExcelMappingConfig` JSON'u elle üretilip `/api/excel/mapping-templates`'e yüklenir.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Onboarding Excel keşif aracı (CLAUDE.md §3)")
    parser.add_argument("dosya", help="Müşteri Excel dosyasının yolu")
    parser.add_argument("--sheet-icerir", default="BANKA", help="Roster sheet adında aranan alt dize")
    parser.add_argument("--sheet-haric", nargs="*", default=["ELDEN"], help="Hariç tutulacak alt dizeler")
    parser.add_argument("--kimlik-kolon", default="B", help="Personel adının olduğu kolon harfi")
    parser.add_argument("--baslangic-satir", type=int, default=3, help="İlk personel satırı")
    parser.add_argument("--toplam-etiket", default="TOPLAM", help="Personel listesinin bittiğini işaret eden etiket")
    parser.add_argument("--onizleme-satir", type=int, default=5, help="Kaç örnek personel satırı dökülsün")
    args = parser.parse_args()

    kesfet(
        dosya_yolu=args.dosya,
        sheet_icerir=args.sheet_icerir,
        sheet_haric=args.sheet_haric,
        kimlik_kolon=args.kimlik_kolon,
        baslangic_satir=args.baslangic_satir,
        toplam_etiket=args.toplam_etiket,
        onizleme_satir=args.onizleme_satir,
    )


if __name__ == "__main__":
    main()
