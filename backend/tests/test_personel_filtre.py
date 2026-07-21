# -*- coding: utf-8 -*-
"""tests/test_personel_filtre.py — kısmi ay için işe-dışı gün sayısı hesabı."""
from datetime import date

from app.models.personel import Personel
from app.services.personel_filtre import ise_disi_gun_sayisi


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
