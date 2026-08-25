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
from datetime import date

import sqlalchemy as sa
from sqlmodel import Session, select

from app.models.donem import Donem
from app.models.personel import Personel
from app.models.personel_donem_ayar import PersonelDonemAyar
from app.models.personel_maas_gecmisi import PersonelMaasGecmisi


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
