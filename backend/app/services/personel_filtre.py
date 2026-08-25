# -*- coding: utf-8 -*-
"""services/personel_filtre.py — Bir personelin belirli bir dönemde (yıl/ay)
puantaj listesinde görünüp görünmeyeceğini belirler.

Kullanıcı geri bildirimi (2026-07-04): işten çıkan personel, çıktığı ayın
SONUNA KADAR listede kalmalı (o ay içindeki günlerine puantaj girilebilsin
diye); bir sonraki aydan itibaren düşer. Yeni giren personel, işe başladığı
aydan itibaren görünür (daha öncesinde değil).
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

import sqlalchemy as sa
from sqlmodel import Session, select

from app.models.donem import Donem
from app.models.personel import Personel
from app.models.personel_donem_ayar import PersonelDonemAyar
from app.models.personel_maas_gecmisi import PersonelMaasGecmisi


# Türkiye kalıcı olarak UTC+3 (2016'dan beri yaz saati uygulaması yok). Sunucu
# UTC çalıştığı için `date.today()` gece 00:00-03:00 arasında BİR ÖNCEKİ günü
# verir — "bugüne kadar kaç gün geçti" hesabı bundan etkilenmemeli.
_TR = timezone(timedelta(hours=3))


def bugun_tr() -> date:
    return datetime.now(_TR).date()


def gelecek_gun_sayisi(personel: Personel, yil: int, ay: int, bugun: date | None = None) -> int:
    """Dönemin HENÜZ GELMEMİŞ gün sayısı — `ise_disi_gun_sayisi` ile çakışmaz.

    Kullanıcı kararı (2026-08-25, müşteri geri bildirimi: "daha ay bitmeden 31 gün
    yazıyor mesela"): içinde bulunulan ay için Ç.GÜN, ayın tamamı değil bugüne
    kadar geçen gün üzerinden hesaplanır. Geçmiş aylarda bu sayı 0'dır, yani
    davranış değişmez.

    Yalnızca hem GELECEKTE hem de kişinin çalışma penceresi İÇİNDE olan günler
    sayılır; pencere dışındaki günler zaten `ise_disi_gun_sayisi` ile düşülüyor,
    ikisini birden saymak çift kesinti olurdu (ör. 10 Ağustos'ta işten çıkan biri
    ayın 25'inde export edilirse Ç.GÜN yine 10 çıkmalı, 4 değil).
    """
    bugun = bugun or bugun_tr()
    donem_bitis = date(yil, ay, calendar.monthrange(yil, ay)[1])
    if bugun >= donem_bitis:
        return 0

    gelecek_baslangic = max(date(yil, ay, 1), bugun + timedelta(days=1))
    calisilan_bitis = min(donem_bitis, personel.isten_cikis_tarihi or donem_bitis)
    calisilan_baslangic = max(date(yil, ay, 1), personel.ise_baslama_tarihi or date(yil, ay, 1))

    baslangic = max(gelecek_baslangic, calisilan_baslangic)
    bitis = calisilan_bitis
    return max(0, (bitis - baslangic).days + 1)


def sayilan_son_gun(yil: int, ay: int, bugun: date | None = None) -> date:
    """Bu dönemde hesaba katılan son gün — geçmiş aylarda ayın son günü."""
    donem_bitis = date(yil, ay, calendar.monthrange(yil, ay)[1])
    return min(donem_bitis, bugun or bugun_tr())


def sayilan_girisler(girisler: list, yil: int, ay: int, bugun: date | None = None) -> list:
    """Gelecek tarihli girişleri eler.

    Bug (2026-08-25, `gelecek_gun` ile aynı gün ortaya çıktı): ay bitmeden Ç.GÜN
    artık gelmemiş günleri düşüyor. Kullanıcılar ileriye dönük de işaretleme
    yapıyor (ör. ZÜBEYDE KURAN'ın 26-31 Ağustos raporlu günleri) ve bu günler
    ÇİFT düşülüyordu: bir kez `gelecek_gun` içinde, bir kez raporlu/devamsız
    olarak. "Bugüne kadar" çıktısı, bugüne kadarki girişlerle hesaplanmalı —
    henüz yaşanmamış bir fazla mesai de ödenmemeli.
    """
    son_gun = sayilan_son_gun(yil, ay, bugun)
    return [g for g in girisler if g.tarih <= son_gun]


def donemde_calisiyor_mu(personel: Personel, yil: int, ay: int) -> bool:
    donem_baslangic = date(yil, ay, 1)
    donem_bitis = date(yil, ay, calendar.monthrange(yil, ay)[1])

    if personel.ise_baslama_tarihi is not None and personel.ise_baslama_tarihi > donem_bitis:
        return False
    if personel.isten_cikis_tarihi is not None and personel.isten_cikis_tarihi < donem_baslangic:
        return False
    return True


def ise_disi_gun_sayisi(personel: Personel, yil: int, ay: int) -> int:
    """Kısmi ay maaşı (kullanıcı kararı, 2026-07-04): ay ortasında işe giren/çıkan
    personelin o aydaki işe-giriş-öncesi/çıkış-sonrası gün sayısı — bu günler
    grid'de zaten tıklanamaz (`DayCell.devreDisiMi`), dolayısıyla elle devamsız
    işaretlenemez; `payroll_calc.hesapla()`'da Ç.GÜN'den otomatik düşülmesi
    gerekir, yoksa kısmi ay çalışana tam ay maaşı ödenmiş olur."""
    donem_baslangic = date(yil, ay, 1)
    donem_bitis = date(yil, ay, calendar.monthrange(yil, ay)[1])
    toplam_gun = (donem_bitis - donem_baslangic).days + 1

    calisilan_baslangic = max(donem_baslangic, personel.ise_baslama_tarihi or donem_baslangic)
    calisilan_bitis = min(donem_bitis, personel.isten_cikis_tarihi or donem_bitis)
    calisilan_gun = max(0, (calisilan_bitis - calisilan_baslangic).days + 1)

    return max(0, toplam_gun - calisilan_gun)


def efektif_ng(session: Session, personel_id: int, donem: Donem) -> int:
    """Bu (personel, dönem) çifti için kullanılacak N.G — kullanıcı kararı
    (2026-07-06): varsayılan dönemin takvim gün sayısı (`Donem.ng`), kişi bazlı
    bir istisna (`PersonelDonemAyar`) varsa SADECE bu dönem için onu kullanır.
    `Personel.ng` artık hesaplamada KULLANILMAZ (bkz. personel_donem_ayar.py)."""
    override = session.exec(
        select(PersonelDonemAyar).where(
            PersonelDonemAyar.personel_id == personel_id,
            PersonelDonemAyar.donem_id == donem.id,
        )
    ).first()
    return override.ng if override else donem.ng


def efektif_maas(session: Session, personel_id: int, donem: Donem) -> float:
    """Bu (personel, dönem) çifti için geçerli maaş — kullanıcı sorusu (2026-07-06):
    "maaşlara zam gelince onu sisteme nasıl alacağız?" `PersonelMaasGecmisi`
    ETKİN-TARİHLİDİR (carry-forward) — `PersonelDonemAyar`'ın aksine (sadece o
    dönem için istisna), bir zam kaydı girildiği (yıl,ay)'dan itibaren bir
    sonraki zam kaydına kadar TÜM dönemlere uygulanır. Hedef dönemden önceki
    veya o döneme ait EN SON kayıt kullanılır; hiç kayıt yoksa (bu kişi için
    henüz hiç zam girilmemiş) `Personel.maas`'a düşülür."""
    kayit = session.exec(
        select(PersonelMaasGecmisi)
        .where(
            PersonelMaasGecmisi.personel_id == personel_id,
            sa.or_(
                PersonelMaasGecmisi.yil < donem.yil,
                sa.and_(PersonelMaasGecmisi.yil == donem.yil, PersonelMaasGecmisi.ay <= donem.ay),
            ),
        )
        .order_by(PersonelMaasGecmisi.yil.desc(), PersonelMaasGecmisi.ay.desc())
    ).first()
    if kayit is not None:
        return kayit.maas

    personel = session.get(Personel, personel_id)
    return personel.maas if personel else 0.0
