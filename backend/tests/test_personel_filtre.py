# -*- coding: utf-8 -*-
"""tests/test_personel_filtre.py — kısmi ay için işe-dışı gün sayısı hesabı."""
from datetime import date

from app.models.personel import Personel
from app.services.personel_filtre import gelecek_gun_sayisi, ise_disi_gun_sayisi, sayilan_girisler, sayilan_son_gun


def _personel(**kwargs) -> Personel:
    return Personel(sirket_id=1, ad_soyad="Test", calisma_tipi_id=1, maas=30000, ng=30, **kwargs)


def test_tam_ay_calisan_ise_disi_gun_sifir():
    p = _personel()
    assert ise_disi_gun_sayisi(p, 2026, 6) == 0


def test_ay_ortasinda_ise_baslayan():
    # Haziran 2026, 30 gün. 11 Haziran'da başlarsa 10 gün işe-dışı (1-10).
    p = _personel(ise_baslama_tarihi=date(2026, 6, 11))
    assert ise_disi_gun_sayisi(p, 2026, 6) == 10


def test_ay_ortasinda_isten_cikan():
    # 20 Haziran son çalışılan gün → 21-30 arası 10 gün işe-dışı.
    p = _personel(isten_cikis_tarihi=date(2026, 6, 20))
    assert ise_disi_gun_sayisi(p, 2026, 6) == 10


def test_hem_gec_baslayip_hem_erken_cikan():
    p = _personel(ise_baslama_tarihi=date(2026, 6, 5), isten_cikis_tarihi=date(2026, 6, 25))
    # calisilan: 5-25 = 21 gun; toplam 30; ise disi = 9
    assert ise_disi_gun_sayisi(p, 2026, 6) == 9


def test_donem_disinda_tamamen_calismamis():
    p = _personel(ise_baslama_tarihi=date(2026, 7, 1))
    assert ise_disi_gun_sayisi(p, 2026, 6) == 30


# ---------------------------------------------------------------------------
# gelecek_gun_sayisi — müşteri geri bildirimi (2026-08-25):
# "daha ay bitmeden 31 gün yazıyor mesela"
# ---------------------------------------------------------------------------


def test_gecmis_ayda_gelecek_gun_yok():
    """Ay kapandıysa davranış hiç değişmemeli — bordro geçmişi sabit kalır."""
    p = _personel()
    assert gelecek_gun_sayisi(p, 2026, 6, bugun=date(2026, 8, 25)) == 0


def test_ay_ortasinda_kalan_gunler_dusulur():
    # 25 Ağustos'ta, 31 günlük ayın 26-31 arası 6 günü henüz gelmemiştir.
    p = _personel()
    assert gelecek_gun_sayisi(p, 2026, 8, bugun=date(2026, 8, 25)) == 6


def test_ayin_son_gununde_gelecek_gun_sifir():
    p = _personel()
    assert gelecek_gun_sayisi(p, 2026, 8, bugun=date(2026, 8, 31)) == 0


def test_ay_icinde_ayrilanin_kalan_gunleri_cift_sayilmaz():
    """`ise_disi_gun_sayisi` ile çakışmamalı: 10 Ağustos'ta çıkan biri için
    ayın 25'inde alınan çıktıda Ç.GÜN 10 olmalı, 4 değil."""
    p = _personel(isten_cikis_tarihi=date(2026, 8, 10))
    ise_disi = ise_disi_gun_sayisi(p, 2026, 8)          # 11-31 → 21
    gelecek = gelecek_gun_sayisi(p, 2026, 8, bugun=date(2026, 8, 25))
    assert ise_disi == 21
    assert gelecek == 0                                  # çalışma penceresi zaten bitmiş
    assert 31 - ise_disi - gelecek == 10


def test_ay_ortasinda_baslayanin_kalan_gunleri():
    p = _personel(ise_baslama_tarihi=date(2026, 8, 20))
    ise_disi = ise_disi_gun_sayisi(p, 2026, 8)          # 1-19 → 19
    gelecek = gelecek_gun_sayisi(p, 2026, 8, bugun=date(2026, 8, 25))
    assert (ise_disi, gelecek) == (19, 6)
    assert 31 - ise_disi - gelecek == 6                  # 20-25 arası 6 gün


class _Giris:
    def __init__(self, tarih):
        self.tarih = tarih


def test_sayilan_son_gun_gecmis_ayda_ay_sonu():
    assert sayilan_son_gun(2026, 6, bugun=date(2026, 8, 25)) == date(2026, 6, 30)


def test_sayilan_son_gun_icinde_bulunulan_ayda_bugun():
    assert sayilan_son_gun(2026, 8, bugun=date(2026, 8, 25)) == date(2026, 8, 25)


def test_gelecek_tarihli_girisler_elenir():
    """Çift kesinti regresyonu: ileriye dönük işaretlenen raporlu günler
    `gelecek_gun` ile zaten düşülüyor, bir de durum olarak sayılmamalı."""
    girisler = [_Giris(date(2026, 8, g)) for g in (20, 25, 26, 31)]
    kalan = sayilan_girisler(girisler, 2026, 8, bugun=date(2026, 8, 25))
    assert [g.tarih.day for g in kalan] == [20, 25]


def test_gecmis_ayda_hicbir_giris_elenmez():
    girisler = [_Giris(date(2026, 6, g)) for g in (1, 15, 30)]
    assert len(sayilan_girisler(girisler, 2026, 6, bugun=date(2026, 8, 25))) == 3
