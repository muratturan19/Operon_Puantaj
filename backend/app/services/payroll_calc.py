# -*- coding: utf-8 -*-
"""
services/payroll_calc.py — Bordro hesap motoru.

DB'den bağımsız, saf fonksiyon (test edilebilirlik için). Formüller
CLAUDE.md §4 / Puantaj_Brief.md §5'ten birebir, `Puantaj.html`'deki
`hesapla()`/`hesaplaGen()` ile doğrulanmış test vakalarıyla karşılaştırıldı.

Tek fark: `gunluk_saat` artık hardcoded 7.5 değil, çağıranın ÇalışanTipi'nden
geçirdiği bir parametre (CLAUDE.md §7 — parametrizasyon mekanizması).

`gun_durumu` (kullanıcı geri bildirimi, 2026-07-04) — tam gün statüsü:
  None          → normal gün, izin_saat/fm_saat saatlik geçerli
  DEVAMSIZ      → Ç.GÜN'den düşer (maaştan düşer) — sabit kural, ayarlanamaz
  YILLIK_IZIN   → Ç.GÜN'den DÜŞMEZ (tam ödenir) — kesin kural
  RAPORLU       → Ç.GÜN'e etkisi ŞİRKET POLİTİKASINA bağlı, bkz. `raporlu_politikasi` (2026-07-04
                  kullanıcı kararı: şirket genelinde tek ayar, üç seçenek). Ayrı bir `gun_durumu`
                  değeri olarak izlenmeye devam eder (grid'de ayrı renk/etiket, özet kolonunda
                  ayrı gün sayısı) — politika sadece MAAŞ ETKİSİNİ belirler.

`ise_disi_gun` (kısmi ay, 2026-07-04 kullanıcı kararı) — ay ortasında işe giren/çıkan
personel için, dönemin o ayki toplam gün sayısından işe giriş/çıkış tarihiyle
kesişmeyen gün sayısı. Çağıran (`app/services/personel_filtre.py::ise_disi_gun_sayisi`)
hesaplar, bu modül tarih penceresi mantığını bilmez — sadece bir sayı olarak alır.
`gun_durumu` grid'de zaten devre dışı bırakıldığı için (`DayCell` `devreDisiMi`) bu
günlere elle devamsız işaretlenemez; otomatik düşülmezse sessiz fazla ödeme olur.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DEVAMSIZ = "devamsiz"
YILLIK_IZIN = "yillik_izin"
RAPORLU = "raporlu"
GUN_DURUMLARI = {DEVAMSIZ, YILLIK_IZIN, RAPORLU}

RAPORLU_TAM_ODE = "tam_ode"        # Yıllık İzin gibi — Ç.GÜN'den hiç düşmez
RAPORLU_HIC_ODEME = "hic_odeme"    # Devamsız gibi — tamamı düşer (varsayılan, mevcut davranış)
RAPORLU_N_GUN_ESIGI = "n_gun_esigi"  # ardışık her rapor bloğunun ilk N günü ödenir, sonrası düşer
RAPORLU_POLITIKALARI = {RAPORLU_TAM_ODE, RAPORLU_HIC_ODEME, RAPORLU_N_GUN_ESIGI}


def _raporlu_dusen_gun_sayisi(girisler: list["GunlukGiris"], esik_gun: int) -> int:
    """N-gün eşiği politikası: ardışık raporlu günler tek bir "blok" (rapor dönemi)
    sayılır, her bloğun ilk `esik_gun` günü ödenir (SGK devraldığı için şirket
    ödemeye devam etmez varsayımı — kullanıcı: "belli bir günün üzerini SGK ödüyor").
    Bilinen sınırlama: bir rapor bloğu ay sınırını aşarsa, her ay kendi girişler
    listesini gördüğü için blok o ayda yeniden N'den başlar (Faz 1 basitleştirmesi)."""
    tarihler = sorted(g.tarih for g in girisler if g.gun_durumu == RAPORLU)
    if not tarihler:
        return 0

    def blok_kesintisi(uzunluk: int) -> int:
        return max(0, uzunluk - esik_gun)

    dusen = 0
    blok_uzunlugu = 1
    for onceki, simdi in zip(tarihler, tarihler[1:]):
        if (simdi - onceki).days == 1:
            blok_uzunlugu += 1
        else:
            dusen += blok_kesintisi(blok_uzunlugu)
            blok_uzunlugu = 1
    dusen += blok_kesintisi(blok_uzunlugu)
    return dusen


@dataclass(frozen=True)
class GunlukGiris:
    """Bir personelin bir günkü puantaj kaydı — PuantajGirisi'nin hesap-motoru-dostu izdüşümü."""

    tarih: date
    gun_durumu: str | None = None  # None | DEVAMSIZ | YILLIK_IZIN | RAPORLU
    izin_saat: float = 0.0
    fm_saat: float = 0.0


@dataclass(frozen=True)
class HesapSonucu:
    cgun: int
    izin_saat: float
    izin_tl: float
    fm_saat: float
    fm_tl: float
    saatlik_ucret: float
    gun_maasi: float
    hakedis: float
    yillik_izin_gun: int
    raporlu_gun: int
    raporlu_dusen_gun: int  # politikaya göre fiilen maaştan düşen raporlu gün sayısı


def fm_orani(
    tarih: date,
    tatiller: set[date],
    hafta_ici_fm_orani: float = 1.5,
    hafta_sonu_fm_orani: float = 2.0,
    resmi_tatil_fm_orani: float = 2.0,
    hafta_tatili_gunleri: frozenset[int] = frozenset({6}),
) -> float:
    """Üç kademeli oran (kullanıcı kararı, 2026-07-05 — internet araştırmasıyla
    desteklendi: İş Kanunu asgari fazla mesai %50/1,5×, resmi tatil/hafta tatili
    çalışması genelde %100/2×, toplu iş sözleşmeleri daha yüksek VE resmi tatili
    hafta tatilinden ayrı oranla ele alabiliyor):
      1. Resmi tatil → resmi_tatil_fm_orani (varsayılan ×2)
      2. Bu Çalışma Tipi'nin hafta tatili günü (`hafta_tatili_gunleri`, weekday
         0=Pzt..6=Paz, varsayılan yalnızca Pazar) → hafta_sonu_fm_orani (×2)
      3. Aksi halde hafta içi → hafta_ici_fm_orani (×1,5)
    ÖNEMLİ: hafta tatili günü artık HER ZAMAN Pazar değil — 5 gün çalışan bir
    tip için (ör. Cumartesi de tatilse) `hafta_tatili_gunleri={5,6}` verilmeli,
    aksi halde o günün fazla mesaisi yanlışlıkla hafta-içi oranıyla hesaplanır."""
    if tarih in tatiller:
        return resmi_tatil_fm_orani
    if tarih.weekday() in hafta_tatili_gunleri:
        return hafta_sonu_fm_orani
    return hafta_ici_fm_orani


def hesapla(
    maas: float,
    ng: int,
    gunluk_saat: float,
    girisler: list[GunlukGiris],
    tatiller: set[date],
    prim: float = 0.0,
    ise_disi_gun: int = 0,
    raporlu_politikasi: str = RAPORLU_HIC_ODEME,
    raporlu_esik_gun: int = 0,
    hafta_ici_fm_orani: float = 1.5,
    hafta_sonu_fm_orani: float = 2.0,
    resmi_tatil_fm_orani: float = 2.0,
    hafta_tatili_gunleri: frozenset[int] = frozenset({6}),
) -> HesapSonucu:
    """
    saatlik_ücret = (MAAŞ / N.G) / gunluk_saat
    Ç.GÜN         = N.G − ise_disi_gun − devamsız_gün − raporlu_düşen_gün   (min 0)
                    — yıllık izin hiçbir zaman düşmez; raporlu_düşen_gün politikaya bağlı
                    (0/tam raporlu_gün/N-gün-eşiği artığı); ise_disi_gun kısmi ay için.
    G             = (MAAŞ / N.G) × Ç.GÜN
    İZİN.TL       = toplam_izin_saati × saatlik_ücret
    FM.TL         = Σ fm_saat_gün × saatlik_ücret × fm_orani(...) — bkz. fm_orani() üç kademesi
    HAKEDİŞ       = PRİM + FM.TL + G − İZİN.TL
    """
    if ng <= 0:
        raise ValueError("N.G sıfır veya negatif olamaz")
    if gunluk_saat <= 0:
        raise ValueError("gunluk_saat sıfır veya negatif olamaz")
    if raporlu_politikasi not in RAPORLU_POLITIKALARI:
        raise ValueError(f"bilinmeyen raporlu_politikasi: {raporlu_politikasi!r}")

    saatlik = (maas / ng) / gunluk_saat

    devamsizlik_sayisi = sum(1 for g in girisler if g.gun_durumu == DEVAMSIZ)
    raporlu_gun = sum(1 for g in girisler if g.gun_durumu == RAPORLU)

    if raporlu_politikasi == RAPORLU_TAM_ODE:
        raporlu_dusen_gun = 0
    elif raporlu_politikasi == RAPORLU_N_GUN_ESIGI:
        raporlu_dusen_gun = _raporlu_dusen_gun_sayisi(girisler, raporlu_esik_gun)
    else:  # RAPORLU_HIC_ODEME
        raporlu_dusen_gun = raporlu_gun

    cgun = max(0, ng - ise_disi_gun - devamsizlik_sayisi - raporlu_dusen_gun)
    gun_maasi = (maas / ng) * cgun

    yillik_izin_gun = sum(1 for g in girisler if g.gun_durumu == YILLIK_IZIN)

    toplam_izin_saat = sum(g.izin_saat for g in girisler)
    izin_tl = toplam_izin_saat * saatlik

    toplam_fm_saat = sum(g.fm_saat for g in girisler)
    fm_tl = sum(
        g.fm_saat * saatlik * fm_orani(
            g.tarih, tatiller, hafta_ici_fm_orani, hafta_sonu_fm_orani,
            resmi_tatil_fm_orani, hafta_tatili_gunleri,
        )
        for g in girisler
        if g.fm_saat
    )

    hakedis = prim + fm_tl + gun_maasi - izin_tl

    return HesapSonucu(
        cgun=cgun,
        izin_saat=toplam_izin_saat,
        izin_tl=izin_tl,
        fm_saat=toplam_fm_saat,
        fm_tl=fm_tl,
        saatlik_ucret=saatlik,
        gun_maasi=gun_maasi,
        hakedis=hakedis,
        yillik_izin_gun=yillik_izin_gun,
        raporlu_gun=raporlu_gun,
        raporlu_dusen_gun=raporlu_dusen_gun,
    )
