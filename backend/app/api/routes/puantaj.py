# -*- coding: utf-8 -*-
"""
api/routes/puantaj.py — Günlük giriş (grid'in kalbi) + server-side özet hesabı.

Prototipteki `entries[row|ymd]` / `setEntry` / `hesapla()` mantığının API
karşılığı. Kritik mimari fark (CLAUDE.md plan §5): ₺ özet değerleri artık
CLIENT'TA değil SERVER'DA hesaplanıyor — hem tek doğruluk kaynağı olsun hem de
`gorebilir_maas_tutari` izni backend'de trivial biçimde uygulanabilsin diye
(CLAUDE.md §8.1 — henüz kapanmamış ama şema bunu destekliyor).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import (
    DONEM_TEMIZLEYEBILIR,
    GOREBILIR_MAAS_TUTARI,
    PERSONEL_YONETEBILIR,
    PUANTAJ_GIREBILIR,
    PUANTAJ_GOREBILIR,
)
from app.core.security import require_permission
from app.models.calisma_tipi import CalismaTipi
from app.models.donem import Donem
from app.models.personel import Personel
from app.models.personel_donem_ayar import PersonelDonemAyar
from app.models.puantaj import PuantajGirisi
from app.models.rbac import Kullanici, Rol
from app.models.sirket import Sirket
from app.models.tatil import Tatil
from app.services.audit import diff_alanlar, log_change
from app.services.payroll_calc import GunlukGiris, hesapla
from app.services.personel_filtre import donemde_calisiyor_mu, efektif_maas, efektif_ng, ise_disi_gun_sayisi

router = APIRouter(prefix="/api/puantaj", tags=["puantaj"])

GunDurumu = Literal["devamsiz", "yillik_izin", "raporlu"]


class GirisGuncelle(BaseModel):
    gun_durumu: Optional[GunDurumu] = None
    izin_saat: float = 0
    fm_saat: float = 0

    def normalize(self) -> "GirisGuncelle":
        """Tam gün statüsü (devamsiz/yillik_izin/raporlu) saatlik girişle karışmaz —
        kullanıcı onayı: 'hayır, tam gün statüsü'. Sunucu tarafında zorlanır,
        frontend'e güvenilmez."""
        if self.gun_durumu is not None:
            return GirisGuncelle(gun_durumu=self.gun_durumu, izin_saat=0, fm_saat=0)
        return self


class PersonelOzet(BaseModel):
    personel_id: int
    ad_soyad: str
    ng: int  # bu dönem için EFEKTİF N.G (istisna varsa o, yoksa dönemin takvim varsayılanı)
    cgun: int
    izin_saat: float
    fm_saat: float
    yillik_izin_gun: int
    raporlu_gun: int
    izin_tl: Optional[float] = None
    fm_tl: Optional[float] = None
    # Kullanıcı geri bildirimi (2026-07-04): "izin saat bazında hesaba giriyor
    # ama hiç gelmediyse maaş eksilmiyor gibi görünüyor" — hesap zaten doğruydu
    # (Ç.GÜN düşünce gun_maasi zaten azalıyordu), sadece bu düşüş hiçbir yerde
    # ₺ olarak GÖSTERİLMİYORDU. devamsız+raporlu günlerin toplam maaş etkisi.
    gun_maasi_kesintisi: Optional[float] = None


def _donem_bul_veya_olustur(session: Session, sirket_id: int, tarih: date) -> Donem:
    donem = session.exec(
        select(Donem).where(
            Donem.sirket_id == sirket_id, Donem.yil == tarih.year, Donem.ay == tarih.month
        )
    ).first()
    if donem is None:
        donem = Donem(sirket_id=sirket_id, yil=tarih.year, ay=tarih.month)
        session.add(donem)
        session.commit()
        session.refresh(donem)
    return donem


@router.get("", response_model=list[PuantajGirisi])
def listele(
    donem_id: int,
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[PuantajGirisi]:
    donem = session.get(Donem, donem_id)
    if donem is None or donem.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı")
    return session.exec(select(PuantajGirisi).where(PuantajGirisi.donem_id == donem_id)).all()


@router.put("/{personel_id}/{tarih}", response_model=Optional[PuantajGirisi])
def gun_guncelle(
    personel_id: int,
    tarih: date,
    payload: GirisGuncelle,
    request: Request,
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GIREBILIR)),
    session: Session = Depends(get_session),
):
    """Prototipteki `setEntry`: tüm alanlar boşsa satır silinir, aksi halde upsert edilir."""
    payload = payload.normalize()

    personel = session.get(Personel, personel_id)
    if personel is None or personel.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı")

    donem = _donem_bul_veya_olustur(session, current_user.sirket_id, tarih)

    mevcut = session.exec(
        select(PuantajGirisi).where(
            PuantajGirisi.personel_id == personel_id, PuantajGirisi.tarih == tarih
        )
    ).first()

    bos_mu = payload.gun_durumu is None and not payload.izin_saat and not payload.fm_saat

    if bos_mu:
        if mevcut is not None:
            log_change(
                session, current_user.sirket_id, current_user.id,
                "PuantajGirisi", str(mevcut.id), "delete",
                changes=diff_alanlar(mevcut.model_dump(), {}),
                ip_adresi=request.client.host if request.client else None,
            )
            session.delete(mevcut)
            session.commit()
        return None

    if mevcut is None:
        yeni = PuantajGirisi(
            personel_id=personel_id, donem_id=donem.id, tarih=tarih,
            created_by_id=current_user.id, **payload.model_dump(),
        )
        session.add(yeni)
        session.commit()
        session.refresh(yeni)
        log_change(
            session, current_user.sirket_id, current_user.id,
            "PuantajGirisi", str(yeni.id), "create",
            changes=diff_alanlar({}, payload.model_dump()),
            ip_adresi=request.client.host if request.client else None,
        )
        return yeni

    eski = mevcut.model_dump()
    for alan, deger in payload.model_dump().items():
        setattr(mevcut, alan, deger)
    mevcut.updated_by_id = current_user.id
    mevcut.updated_at = datetime.utcnow()
    session.add(mevcut)
    session.commit()
    session.refresh(mevcut)

    degisiklikler = diff_alanlar(eski, mevcut.model_dump())
    if degisiklikler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "PuantajGirisi", str(mevcut.id), "update",
            changes=degisiklikler,
            ip_adresi=request.client.host if request.client else None,
        )
    return mevcut


def _personel_ozet_hesapla(
    session: Session,
    personel: Personel,
    donem: Donem,
    sirket: Optional[Sirket],
    tatiller: set,
    maas_gorebilir: bool,
    girisler: list[PuantajGirisi],
) -> PersonelOzet:
    tip = session.get(CalismaTipi, personel.calisma_tipi_id)
    ng = efektif_ng(session, personel.id, donem)
    maas = efektif_maas(session, personel.id, donem)
    girisler_calc = [
        GunlukGiris(tarih=g.tarih, gun_durumu=g.gun_durumu, izin_saat=g.izin_saat, fm_saat=g.fm_saat)
        for g in girisler
    ]
    sonuc = hesapla(
        maas=maas, ng=ng, gunluk_saat=tip.gunluk_saat if tip else 7.5,
        girisler=girisler_calc, tatiller=tatiller,
        ise_disi_gun=ise_disi_gun_sayisi(personel, donem.yil, donem.ay),
        raporlu_politikasi=sirket.raporlu_politikasi if sirket else "hic_odeme",
        raporlu_esik_gun=sirket.raporlu_esik_gun if sirket else 0,
        hafta_ici_fm_orani=tip.hafta_ici_fm_orani if tip else 1.5,
        hafta_sonu_fm_orani=tip.hafta_sonu_fm_orani if tip else 2.0,
        resmi_tatil_fm_orani=tip.resmi_tatil_fm_orani if tip else 2.0,
        hafta_tatili_gunleri=frozenset(tip.hafta_tatili_gunleri) if tip else frozenset({6}),
    )
    return PersonelOzet(
        personel_id=personel.id,
        ad_soyad=personel.ad_soyad,
        ng=ng,
        cgun=sonuc.cgun,
        izin_saat=sonuc.izin_saat,
        fm_saat=sonuc.fm_saat,
        yillik_izin_gun=sonuc.yillik_izin_gun,
        raporlu_gun=sonuc.raporlu_gun,
        izin_tl=round(sonuc.izin_tl, 2) if maas_gorebilir else None,
        fm_tl=round(sonuc.fm_tl, 2) if maas_gorebilir else None,
        gun_maasi_kesintisi=round(maas - sonuc.gun_maasi, 2) if maas_gorebilir else None,
    )


@router.get("/ozet", response_model=list[PersonelOzet])
def ozet(
    donem_id: int,
    current_user: Kullanici = Depends(require_permission(PUANTAJ_GOREBILIR)),
    session: Session = Depends(get_session),
) -> list[PersonelOzet]:
    donem = session.get(Donem, donem_id)
    if donem is None or donem.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı")

    rol = session.get(Rol, current_user.rol_id)
    maas_gorebilir = bool(rol and rol.izinler.get(GOREBILIR_MAAS_TUTARI, False))

    sirket = session.get(Sirket, current_user.sirket_id)

    tatiller = {t.tarih for t in session.exec(
        select(Tatil).where(Tatil.sirket_id == current_user.sirket_id)
    ).all()}

    personel_listesi = [
        p for p in session.exec(select(Personel).where(Personel.sirket_id == current_user.sirket_id)).all()
        if donemde_calisiyor_mu(p, donem.yil, donem.ay)
    ]

    girisler_by_personel: dict[int, list[PuantajGirisi]] = {}
    for g in session.exec(select(PuantajGirisi).where(PuantajGirisi.donem_id == donem_id)).all():
        girisler_by_personel.setdefault(g.personel_id, []).append(g)

    return [
        _personel_ozet_hesapla(
            session, p, donem, sirket, tatiller, maas_gorebilir, girisler_by_personel.get(p.id, [])
        )
        for p in personel_listesi
    ]


class NgAyarla(BaseModel):
    ng: Optional[int] = None  # None = istisnayı kaldır, dönemin takvim varsayılanına dön


@router.put("/{personel_id}/donem/{donem_id}/ng", response_model=PersonelOzet)
def ng_ayarla(
    personel_id: int,
    donem_id: int,
    payload: NgAyarla,
    request: Request,
    current_user: Kullanici = Depends(require_permission(PERSONEL_YONETEBILIR)),
    session: Session = Depends(get_session),
) -> PersonelOzet:
    """Bu (personel, dönem) çifti için N.G istisnası ekler/kaldırır (kullanıcı
    kararı, 2026-07-06: varsayılan takvim gün sayısı, kişi bazında elle
    değiştirilebilsin — bkz. PersonelDonemAyar)."""
    personel = session.get(Personel, personel_id)
    if personel is None or personel.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı")
    donem = session.get(Donem, donem_id)
    if donem is None or donem.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı")

    mevcut = session.exec(
        select(PersonelDonemAyar).where(
            PersonelDonemAyar.personel_id == personel_id, PersonelDonemAyar.donem_id == donem_id
        )
    ).first()

    if payload.ng is None:
        if mevcut is not None:
            log_change(
                session, current_user.sirket_id, current_user.id,
                "PersonelDonemAyar", str(mevcut.id), "delete",
                changes=diff_alanlar({"ng": mevcut.ng}, {}),
                ip_adresi=request.client.host if request.client else None,
            )
            session.delete(mevcut)
            session.commit()
    elif mevcut is None:
        mevcut = PersonelDonemAyar(personel_id=personel_id, donem_id=donem_id, ng=payload.ng)
        session.add(mevcut)
        session.commit()
        log_change(
            session, current_user.sirket_id, current_user.id,
            "PersonelDonemAyar", str(mevcut.id), "create",
            changes=diff_alanlar({}, {"ng": payload.ng}),
            ip_adresi=request.client.host if request.client else None,
        )
    else:
        eski_ng = mevcut.ng
        mevcut.ng = payload.ng
        session.add(mevcut)
        session.commit()
        if eski_ng != payload.ng:
            log_change(
                session, current_user.sirket_id, current_user.id,
                "PersonelDonemAyar", str(mevcut.id), "update",
                changes=diff_alanlar({"ng": eski_ng}, {"ng": payload.ng}),
                ip_adresi=request.client.host if request.client else None,
            )

    # Güncel özet tek satır olarak dönsün — frontend tüm listeyi tekrar çekmeden güncelleyebilsin.
    rol = session.get(Rol, current_user.rol_id)
    maas_gorebilir = bool(rol and rol.izinler.get(GOREBILIR_MAAS_TUTARI, False))
    sirket = session.get(Sirket, current_user.sirket_id)
    tatiller = {t.tarih for t in session.exec(select(Tatil).where(Tatil.sirket_id == current_user.sirket_id)).all()}
    girisler = session.exec(
        select(PuantajGirisi).where(PuantajGirisi.donem_id == donem_id, PuantajGirisi.personel_id == personel_id)
    ).all()
    return _personel_ozet_hesapla(session, personel, donem, sirket, tatiller, maas_gorebilir, girisler)


@router.post("/donem/{donem_id}/temizle", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def donemi_temizle(
    donem_id: int,
    request: Request,
    current_user: Kullanici = Depends(require_permission(DONEM_TEMIZLEYEBILIR)),
    session: Session = Depends(get_session),
) -> None:
    donem = session.get(Donem, donem_id)
    if donem is None or donem.sirket_id != current_user.sirket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı")

    girisler = session.exec(select(PuantajGirisi).where(PuantajGirisi.donem_id == donem_id)).all()
    for g in girisler:
        log_change(
            session, current_user.sirket_id, current_user.id,
            "PuantajGirisi", str(g.id), "delete",
            changes=diff_alanlar(g.model_dump(), {}),
            ip_adresi=request.client.host if request.client else None,
        )
        session.delete(g)
    session.commit()
