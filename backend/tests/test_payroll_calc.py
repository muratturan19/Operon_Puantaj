# -*- coding: utf-8 -*-
"""
tests/test_payroll_calc.py — Puantaj_Brief.md §13 kabul kriterlerinin doğrulanmış
test vakaları. Bu testler kırmızıysa hesap motoruna ASLA dokunma — önce
Puantaj.html'deki hesapla()/hesaplaGen() ile karşılaştır (CLAUDE.md §4/§5).
"""
from datetime import date

import pytest

from app.services.payroll_calc import (
    DEVAMSIZ,
    RAPORLU,
    RAPORLU_HIC_ODEME,
    RAPORLU_N_GUN_ESIGI,
    RAPORLU_TAM_ODE,
    YILLIK_IZIN,
    GunlukGiris,
    hesapla,
)

TATIL_2026 = {date(2026, 5, 19)}  # 19 Mayıs resmi tatil


def test_vaka_1_fm_iki_kademe_ve_izin():
    # maaş 32000, N.G 30 → saatlik 142,2222
    # 4 saat FM hafta içi (Pazartesi, ×1,5) = 853,33
    # 3 saat FM Pazar (×2) = 853,33 → FM.TL = 1.706,67
    # 2 saat izin → İZİN.TL = 284,44
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 1), fm_saat=4.0),   # Pazartesi
        GunlukGiris(tarih=date(2026, 6, 7), fm_saat=3.0),   # Pazar
        GunlukGiris(tarih=date(2026, 6, 2), izin_saat=2.0),
    ]
    sonuc = hesapla(maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert round(sonuc.saatlik_ucret, 4) == 142.2222
    assert round(sonuc.fm_tl, 2) == 1706.67
    assert round(sonuc.izin_tl, 2) == 284.44


def test_vaka_2_devamsizlik_cgun_ve_gun_maasi():
    # maaş 50000, 2 gün devamsız → Ç.GÜN = 28, G = 46.666,67
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=DEVAMSIZ),
        GunlukGiris(tarih=date(2026, 6, 4), gun_durumu=DEVAMSIZ),
    ]
    sonuc = hesapla(maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc.cgun == 28
    assert round(sonuc.gun_maasi, 2) == 46666.67


def test_yillik_izin_maastan_dusmez():
    """Kullanıcı geri bildirimi (2026-07-04): Yıllık İzin Ç.GÜN'den düşmez, tam ödenir."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=YILLIK_IZIN),
        GunlukGiris(tarih=date(2026, 6, 4), gun_durumu=YILLIK_IZIN),
    ]
    sonuc = hesapla(maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc.cgun == 30  # devamsızlık YOK, düşmedi
    assert round(sonuc.gun_maasi, 2) == 50000.00  # tam maaş
    assert sonuc.yillik_izin_gun == 2


def test_raporlu_varsayilan_maastan_duser():
    """Kullanıcı kararı (2026-07-04): 'defaultta raporda para ödenmez olsun, sonra
    değiştirebiliriz' — Raporlu varsayılan olarak DEVAMSIZ gibi Ç.GÜN'den düşer,
    ama ayrı bir gun_durumu olarak izlenir (ROADMAP.md — şirket bazlı politika henüz yok)."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=RAPORLU),
        GunlukGiris(tarih=date(2026, 6, 4), gun_durumu=RAPORLU),
    ]
    sonuc = hesapla(maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc.cgun == 28  # devamsız gibi düşüyor
    assert round(sonuc.gun_maasi, 2) == 46666.67
    assert sonuc.raporlu_gun == 2  # ama ayrı sayaçta izleniyor


def test_devamsiz_yillik_izin_raporlu_ayni_ayda_karismaz():
    """Üç tam-gün statüsü aynı ayda birlikte doğru sayılmalı, birbirine karışmamalı."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 2), gun_durumu=DEVAMSIZ),
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=YILLIK_IZIN),
        GunlukGiris(tarih=date(2026, 6, 4), gun_durumu=YILLIK_IZIN),
        GunlukGiris(tarih=date(2026, 6, 5), gun_durumu=RAPORLU),
    ]
    sonuc = hesapla(maas=30000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc.cgun == 28  # devamsız (1) + raporlu (1) düşüyor, yıllık izin düşmüyor
    assert sonuc.yillik_izin_gun == 2
    assert sonuc.raporlu_gun == 1


def test_vaka_3_resmi_tatil_fm_x2():
    # 19 Mayıs (resmi tatil), 5 saat FM ×2, saatlik 142,2222 → 1.422,22
    girisler = [GunlukGiris(tarih=date(2026, 5, 19), fm_saat=5.0)]
    sonuc = hesapla(maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=TATIL_2026)

    assert round(sonuc.fm_tl, 2) == 1422.22


def test_regresyon_sifir_giris_degisiklik_yok():
    """İzin=0 ve FM=0 olan personelde tüm ₺ alanları 0/dokunulmaz kalmalı."""
    girisler = [GunlukGiris(tarih=date(2026, 6, 1))]  # devamsızlık yok, izin yok, FM yok
    sonuc = hesapla(maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc.cgun == 30
    assert sonuc.izin_tl == 0
    assert sonuc.fm_tl == 0
    assert round(sonuc.gun_maasi, 2) == 32000.00


def test_izin_ve_fm_karismaz():
    """6 saat FM (hafta içi, ×1,5) + 6 saat izin aynı gün → net +0,5×6×saatlik farkla ayrı kovalarda."""
    saatlik = (32000 / 30) / 7.5
    girisler = [GunlukGiris(tarih=date(2026, 6, 1), fm_saat=6.0, izin_saat=6.0)]  # Pazartesi
    sonuc = hesapla(maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert round(sonuc.fm_tl, 2) == round(6.0 * saatlik * 1.5, 2)
    assert round(sonuc.izin_tl, 2) == round(6.0 * saatlik, 2)
    # FM ve izin ayrı kovalar: toplam saat alanları birbirine karışmamalı
    assert sonuc.fm_saat == 6.0
    assert sonuc.izin_saat == 6.0


def test_farkli_calisan_tipi_gunluk_saat_parametresi():
    """CalismaTipi'nin gunluk_saat'i hesaba doğrudan yansımalı (BY 8 saat örneği)."""
    girisler = [GunlukGiris(tarih=date(2026, 6, 1), fm_saat=2.0)]  # Pazartesi
    sonuc_by = hesapla(maas=32000, ng=30, gunluk_saat=8.0, girisler=girisler, tatiller=set())
    sonuc_my = hesapla(maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set())

    assert sonuc_by.saatlik_ucret < sonuc_my.saatlik_ucret
    assert sonuc_by.fm_tl < sonuc_my.fm_tl


def test_kismi_ay_ise_disi_gun_cgunden_duser():
    """Kullanıcı kararı (2026-07-04): ay ortasında işe giren/çıkan personelin
    işe-dışı günleri otomatik olarak Ç.GÜN'den düşer (kısmi ay maaşı)."""
    sonuc = hesapla(maas=30000, ng=30, gunluk_saat=7.5, girisler=[], tatiller=set(), ise_disi_gun=10)

    assert sonuc.cgun == 20
    assert round(sonuc.gun_maasi, 2) == 20000.00


def test_ise_disi_gun_ve_devamsizlik_birlikte_dusuyor():
    girisler = [GunlukGiris(tarih=date(2026, 6, 20), gun_durumu=DEVAMSIZ)]
    sonuc = hesapla(maas=30000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(), ise_disi_gun=10)

    assert sonuc.cgun == 19  # 30 - 10 (ise disi) - 1 (devamsiz)


def test_raporlu_tam_ode_politikasi_cgunden_dusmez():
    """Raporlu Tam Öde politikasında Yıllık İzin gibi Ç.GÜN'den hiç düşmez."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=RAPORLU),
        GunlukGiris(tarih=date(2026, 6, 4), gun_durumu=RAPORLU),
    ]
    sonuc = hesapla(
        maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        raporlu_politikasi=RAPORLU_TAM_ODE,
    )

    assert sonuc.cgun == 30
    assert round(sonuc.gun_maasi, 2) == 50000.00
    assert sonuc.raporlu_gun == 2
    assert sonuc.raporlu_dusen_gun == 0


def test_raporlu_hic_odeme_politikasi_raporlu_dusen_gun_esittir_raporlu_gun():
    girisler = [GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=RAPORLU)]
    sonuc = hesapla(
        maas=50000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        raporlu_politikasi=RAPORLU_HIC_ODEME,
    )

    assert sonuc.raporlu_dusen_gun == sonuc.raporlu_gun == 1
    assert sonuc.cgun == 29


def test_raporlu_n_gun_esigi_tek_blok():
    """5 günlük ardışık rapor bloğu, eşik 3 gün → ilk 3 gün ödenir, 2 gün düşer."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, d), gun_durumu=RAPORLU) for d in range(3, 8)
    ]
    sonuc = hesapla(
        maas=30000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        raporlu_politikasi=RAPORLU_N_GUN_ESIGI, raporlu_esik_gun=3,
    )

    assert sonuc.raporlu_gun == 5
    assert sonuc.raporlu_dusen_gun == 2
    assert sonuc.cgun == 28


def test_raporlu_n_gun_esigi_iki_ayri_blok():
    """Aralarında boşluk olan iki ayrı rapor bloğu, eşik HER BLOK için ayrı ayrı uygulanır."""
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 1), gun_durumu=RAPORLU),
        GunlukGiris(tarih=date(2026, 6, 2), gun_durumu=RAPORLU),
        GunlukGiris(tarih=date(2026, 6, 3), gun_durumu=RAPORLU),
        # boşluk (4, 5)
        GunlukGiris(tarih=date(2026, 6, 6), gun_durumu=RAPORLU),
        GunlukGiris(tarih=date(2026, 6, 7), gun_durumu=RAPORLU),
    ]
    sonuc = hesapla(
        maas=30000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        raporlu_politikasi=RAPORLU_N_GUN_ESIGI, raporlu_esik_gun=2,
    )

    # blok1 (3 gün, eşik 2) → 1 düşer; blok2 (2 gün, eşik 2) → 0 düşer
    assert sonuc.raporlu_gun == 5
    assert sonuc.raporlu_dusen_gun == 1


def test_bilinmeyen_raporlu_politikasi_hata_verir():
    with pytest.raises(ValueError):
        hesapla(maas=30000, ng=30, gunluk_saat=7.5, girisler=[], tatiller=set(), raporlu_politikasi="gecersiz")


def test_calisma_tipi_bazli_ozel_fm_orani():
    """Kullanıcı kararı (2026-07-04): FM oranları Çalışma Tipi bazında ayarlanabilir olmalı —
    varsayılan 1,5×/2× yerine özel bir oran (ör. 1,25×/1,75×) hesaba doğrudan yansımalı."""
    saatlik = (32000 / 30) / 7.5
    girisler = [
        GunlukGiris(tarih=date(2026, 6, 1), fm_saat=4.0),  # Pazartesi (hafta içi)
        GunlukGiris(tarih=date(2026, 6, 7), fm_saat=3.0),  # Pazar (hafta sonu)
    ]
    sonuc = hesapla(
        maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        hafta_ici_fm_orani=1.25, hafta_sonu_fm_orani=1.75,
    )
    beklenen = 4.0 * saatlik * 1.25 + 3.0 * saatlik * 1.75
    assert round(sonuc.fm_tl, 2) == round(beklenen, 2)


def test_5_gun_calisan_tip_cumartesi_hafta_tatili_orani_alir():
    """Kullanıcı geri bildirimi (2026-07-05): hafta tatili günü artık HER ZAMAN
    Pazar değil — 5 gün çalışan bir tip (ör. Beyaz Yaka) için Cumartesi de
    hafta_tatili_gunleri'nde olmalı ve hafta_sonu (hafta tatili) oranını almalı,
    hafta_ici oranını DEĞİL."""
    saatlik = (32000 / 30) / 7.5
    girisler = [GunlukGiris(tarih=date(2026, 6, 6), fm_saat=4.0)]  # Cumartesi
    sonuc_5_gun = hesapla(
        maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        hafta_ici_fm_orani=1.5, hafta_sonu_fm_orani=2.0,
        hafta_tatili_gunleri=frozenset({5, 6}),  # Cmt+Paz tatil (5 gün çalışan tip)
    )
    sonuc_6_gun = hesapla(
        maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=set(),
        hafta_ici_fm_orani=1.5, hafta_sonu_fm_orani=2.0,
        hafta_tatili_gunleri=frozenset({6}),  # sadece Pazar tatil (6 gün çalışan tip, varsayılan)
    )

    assert round(sonuc_5_gun.fm_tl, 2) == round(4.0 * saatlik * 2.0, 2)  # hafta tatili oranı
    assert round(sonuc_6_gun.fm_tl, 2) == round(4.0 * saatlik * 1.5, 2)  # hafta içi oranı


def test_resmi_tatil_orani_hafta_sonu_oranindan_bagimsiz():
    """Kullanıcı kararı (2026-07-05): toplu iş sözleşmeleri resmi tatili hafta
    tatilinden farklı bir oranla ele alabiliyor — artık bağımsız bir parametre."""
    saatlik = (32000 / 30) / 7.5
    girisler = [GunlukGiris(tarih=date(2026, 5, 19), fm_saat=5.0)]  # 19 Mayıs resmi tatil
    sonuc = hesapla(
        maas=32000, ng=30, gunluk_saat=7.5, girisler=girisler, tatiller=TATIL_2026,
        hafta_sonu_fm_orani=2.0, resmi_tatil_fm_orani=3.0,  # sendika örneği: resmi tatil ×3
    )
    assert round(sonuc.fm_tl, 2) == round(5.0 * saatlik * 3.0, 2)


def test_gelecek_gun_cgun_dan_dusulur():
    """Ay bitmeden alınan çıktıda Ç.GÜN ayın tamamını göstermemeli (2026-08-25 kararı)."""
    tam_ay = hesapla(maas=31000, ng=31, gunluk_saat=7.5, girisler=[], tatiller=set())
    yarim_ay = hesapla(maas=31000, ng=31, gunluk_saat=7.5, girisler=[], tatiller=set(), gelecek_gun=6)
    assert tam_ay.cgun == 31
    assert yarim_ay.cgun == 25
    # G = (MAAŞ / N.G) × Ç.GÜN — hakediş de orantılı düşmeli
    assert yarim_ay.gun_maasi == pytest.approx(31000 / 31 * 25)


def test_gelecek_gun_devamsizlikla_birlikte():
    sonuc = hesapla(
        maas=31000, ng=31, gunluk_saat=7.5,
        girisler=[GunlukGiris(tarih=date(2026, 8, 5), gun_durumu=DEVAMSIZ)],
        tatiller=set(), gelecek_gun=6,
    )
    assert sonuc.cgun == 24


def test_gelecek_gun_cgun_u_negatife_dusuremez():
    sonuc = hesapla(maas=31000, ng=31, gunluk_saat=7.5, girisler=[], tatiller=set(), gelecek_gun=99)
    assert sonuc.cgun == 0


def test_yarim_gun_izin_tam_yarim_gunluk_ucret_keser():
    """Müşteri geri bildirimi (2026-08-25): "yarım gün için 3 deseler az, 4 deseler
    fazla oluyor" — 7,5 saatlik günde yarım gün 3,75 saattir ve tam olarak yarım
    günlük ücrete denk gelmelidir. Arayüzdeki "Yarım gün" butonu bu değeri yazar."""
    maas, ng, gunluk_saat = 30000.0, 30, 7.5
    sonuc = hesapla(
        maas=maas, ng=ng, gunluk_saat=gunluk_saat,
        girisler=[GunlukGiris(tarih=date(2026, 8, 10), izin_saat=gunluk_saat / 2)],
        tatiller=set(),
    )
    gun_maasi = maas / ng
    assert sonuc.izin_saat == 3.75
    assert sonuc.izin_tl == pytest.approx(gun_maasi / 2)
    assert sonuc.cgun == ng  # izin saati Ç.GÜN'ü düşürmez, yalnızca ücretten keser
    assert sonuc.hakedis == pytest.approx(maas - gun_maasi / 2)
