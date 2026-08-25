# -*- coding: utf-8 -*-
"""
api/routes/excel.py — Excel mapping template CRUD + import/export.

Mimari: mapping onboarding-zamanı üretilir (bkz. CLAUDE.md §3), üretim
ortamı bu config'i statik olarak tüketir — hiç LLM/relay çağrısı yapmaz.
Import/export SİMETRİK tek mapping kullanır (CLAUDE.md §7).

Faz 1'de "master" workbook, şirket başına diskte saklanır
(`data/uploads/{sirket_id}_master.xlsx`) — her export bu dosyanın TEMİZ bir
kopyasına yazılır, orijinal asla üzerine yazılarak bozulmaz.
"""
from __future__ import annotations

import calendar
import io
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.permissions import EXCEL_DISA_AKTARABILIR, EXCEL_ICE_AKTARABILIR, GOREBILIR_MAAS_TUTARI
from app.core.security import require_permission
from app.core.tenant_scope import get_storage_onceki
from app.models.calisma_tipi import CalismaTipi
from app.models.donem import Donem
from app.models.excel_mapping import ExcelMappingTemplate
from app.models.excel_mapping_schema import ExcelMappingConfig
from app.models.personel import Personel
from app.models.puantaj import PuantajGirisi
from app.models.rbac import Kullanici
from app.models.sirket import Sirket
from app.models.tatil import Tatil
from app.services.excel_adapter import (
    TR_AYLAR,
    RosterKaydi,
    aktif_sayfa_yap,
    roster_satirlarini_sil,
    en_guncel_sheet,
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
from app.services.personel_filtre import (
    bugun_tr,
    donemde_calisiyor_mu,
    efektif_maas,
    efektif_ng,
    gelecek_gun_sayisi,
    ise_disi_gun_sayisi,
    sayilan_girisler,
)

logger = logging.getLogger("operon_puantaj.excel")

router = APIRouter(prefix="/api/excel", tags=["excel"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


class MappingTemplateCreate(BaseModel):
    ad: str
    mapping_json: dict


class ImportSonucu(BaseModel):
    donemler_bulundu: list[str]
    personel_olusturulan: int
    personel_guncellenen: int


def _master_dosya_yolu(storage_onceki: str, sirket_id: int) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR / f"{storage_onceki}_{sirket_id}_master.xlsx"


@router.get("/mapping-templates", response_model=list[ExcelMappingTemplate])
def sablonlari_listele(
    current_user: Kullanici = Depends(require_permission(EXCEL_ICE_AKTARABILIR)),
    session: Session = Depends(get_session),
) -> list[ExcelMappingTemplate]:
    return session.exec(
        select(ExcelMappingTemplate).where(
            (ExcelMappingTemplate.sirket_id == current_user.sirket_id)
            | (ExcelMappingTemplate.sirket_id.is_(None))
        )
    ).all()


@router.post("/mapping-templates", response_model=ExcelMappingTemplate, status_code=status.HTTP_201_CREATED)
def sablon_olustur(
    payload: MappingTemplateCreate,
    current_user: Kullanici = Depends(require_permission(EXCEL_ICE_AKTARABILIR)),
    session: Session = Depends(get_session),
) -> ExcelMappingTemplate:
    # mapping_json'ın geçerli bir ExcelMappingConfig olduğunu doğrula (uydurma/hatalı config'i erken yakala)
    ExcelMappingConfig.model_validate(payload.mapping_json)

    sablon = ExcelMappingTemplate(
        sirket_id=current_user.sirket_id,
        ad=payload.ad,
        mapping_json=payload.mapping_json,
        created_by_id=current_user.id,
    )
    session.add(sablon)
    session.commit()
    session.refresh(sablon)
    return sablon


@router.post("/import", response_model=ImportSonucu)
async def ice_aktar(
    mapping_template_id: int,
    dosya: UploadFile,
    current_user: Kullanici = Depends(require_permission(EXCEL_ICE_AKTARABILIR)),
    session: Session = Depends(get_session),
    storage_onceki: str = Depends(get_storage_onceki),
) -> ImportSonucu:
    sablon = session.get(ExcelMappingTemplate, mapping_template_id)
    if sablon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping template bulunamadı")
    mapping = ExcelMappingConfig.model_validate(sablon.mapping_json)

    icerik = await dosya.read()
    master_path = _master_dosya_yolu(storage_onceki, current_user.sirket_id)
    master_path.write_bytes(icerik)

    wb = open_workbook(str(master_path))

    varsayilan_tip = session.exec(
        select(CalismaTipi).where(CalismaTipi.sirket_id == current_user.sirket_id)
    ).first()
    tip_by_kod = {
        t.kod: t
        for t in session.exec(select(CalismaTipi).where(CalismaTipi.sirket_id == current_user.sirket_id)).all()
    }

    donemler_bulundu: list[str] = []
    olusturulan = 0
    guncellenen = 0

    # Sayfa/dönem eşlemesi TÜM eşleşen sayfalar için yapılır (dönem seçicide
    # geçmiş ayların da görünmesi için) — ama personel ROSTER'ı (aşağıda)
    # yalnızca EN GÜNCEL sayfadan alınır (kullanıcı geri bildirimi, 2026-07-06:
    # aylık sayfalar birikince, ayrılmış personel de "aktif" olarak kalıyordu —
    # ör. Ocak'tan Haziran'a kadar 6 ay, her ayda personel devri var; hepsini
    # aynı anda "mevcut personel" saymak yanlış, yalnızca en son ayın kadrosu
    # gerçek/güncel roster'dır).
    sayfa_donemleri: list[tuple] = []
    for ws in list_matching_sheets(wb, mapping.sheet_mapping):
        donem_bilgisi = parse_sheet_donem(ws.title)
        if donem_bilgisi is None:
            continue
        sayfa_donemleri.append((ws, donem_bilgisi))

    if not sayfa_donemleri:
        return ImportSonucu(donemler_bulundu=[], personel_olusturulan=0, personel_guncellenen=0)

    en_guncel_ws, _ = max(sayfa_donemleri, key=lambda t: t[1])

    for ws, (yil, ay) in sayfa_donemleri:
        donemler_bulundu.append(ws.title)

        donem = session.exec(
            select(Donem).where(
                Donem.sirket_id == current_user.sirket_id, Donem.yil == yil, Donem.ay == ay
            )
        ).first()
        if donem is None:
            donem = Donem(sirket_id=current_user.sirket_id, yil=yil, ay=ay, excel_sheet_adi=ws.title)
            session.add(donem)
            session.commit()
            session.refresh(donem)
        elif donem.excel_sheet_adi != ws.title:
            donem.excel_sheet_adi = ws.title
            session.add(donem)
            session.commit()

        if ws is not en_guncel_ws:
            continue  # yalnızca dönem kaydı oluştu — roster bu sayfadan alınmaz

        kayitlar: list[RosterKaydi] = read_roster(ws, mapping)
        for kayit in kayitlar:
            ad_soyad = kayit.alanlar.get("ad_soyad")
            if not ad_soyad:
                continue
            tip_kodu = kayit.alanlar.get("calisma_tipi_kodu")
            tip = tip_by_kod.get(tip_kodu) or varsayilan_tip
            if tip is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Şirkette hiç Çalışma Tipi tanımlı değil — önce en az bir tip oluşturun",
                )

            mevcut = session.exec(
                select(Personel).where(
                    Personel.sirket_id == current_user.sirket_id,
                    Personel.excel_kaynak_satir == kayit.excel_satir,
                    Personel.ad_soyad == ad_soyad,
                )
            ).first()

            if mevcut is None:
                mevcut = session.exec(
                    select(Personel).where(
                        Personel.sirket_id == current_user.sirket_id, Personel.ad_soyad == ad_soyad
                    )
                ).first()

            if mevcut is None:
                yeni = Personel(
                    sirket_id=current_user.sirket_id,
                    ad_soyad=ad_soyad,
                    calisma_tipi_id=tip.id,
                    maas=kayit.alanlar.get("maas") or 0,
                    ng=kayit.alanlar.get("ng") or 30,
                    excel_kaynak_satir=kayit.excel_satir,
                )
                session.add(yeni)
                olusturulan += 1
            else:
                mevcut.maas = kayit.alanlar.get("maas") or mevcut.maas
                mevcut.ng = kayit.alanlar.get("ng") or mevcut.ng
                mevcut.excel_kaynak_satir = kayit.excel_satir
                mevcut.updated_at = datetime.utcnow()
                session.add(mevcut)
                guncellenen += 1
        session.commit()

    return ImportSonucu(
        donemler_bulundu=donemler_bulundu,
        personel_olusturulan=olusturulan,
        personel_guncellenen=guncellenen,
    )


def _master_kaydet(wb, master_path: Path) -> None:
    """Üretilen workbook'u master'ın üzerine ATOMİK olarak yazar.

    Bug (2026-08-25): export ürettiği yeni ay sayfalarını yalnızca indirilen
    dosyaya koyuyor, master'a HİÇ yazmıyordu. Master 3 Temmuz'daki ilk yüklemede
    donmuştu; her export Haziran roster'ından yeniden türetiliyor, müşterinin
    dosyada yaptığı manuel girdiler (avans/icra/prim) ve personel değişiklikleri
    her seferinde kayboluyordu. Artık export kümülatif.

    İlk üzerine yazmadan önce orijinal dosyanın bir kopyası saklanır — Faz 1'de
    master tek kaynak, geri dönüşü olmayan bir yazma bırakılmaz.
    """
    yedek = master_path.with_name(master_path.stem + ".ilk_yukleme" + master_path.suffix)
    if not yedek.exists():
        shutil.copy2(master_path, yedek)

    gecici = master_path.with_name(master_path.stem + ".tmp" + master_path.suffix)
    save_workbook(wb, str(gecici))
    os.replace(gecici, master_path)   # aynı dosya sistemi — yarım kalmış dosya bırakmaz


@router.get("/export")
def disa_aktar(
    mapping_template_id: int,
    donem_id: Optional[int] = None,
    current_user: Kullanici = Depends(require_permission(EXCEL_DISA_AKTARABILIR, GOREBILIR_MAAS_TUTARI)),
    session: Session = Depends(get_session),
    storage_onceki: str = Depends(get_storage_onceki),
) -> StreamingResponse:
    sablon = session.get(ExcelMappingTemplate, mapping_template_id)
    if sablon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping template bulunamadı")
    mapping = ExcelMappingConfig.model_validate(sablon.mapping_json)

    master_path = _master_dosya_yolu(storage_onceki, current_user.sirket_id)
    if not master_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Önce bir dosya içe aktarılmalı")

    wb = open_workbook(str(master_path))

    # Kapsam: donem_id verilmezse GİRİŞİ OLAN TÜM DÖNEMLER yazılır (Puantaj_Brief §10 — kapanmış karar).
    # ORDER BY şart (2026-08-25): sırasız sorguda dönemler DB'nin döndürdüğü keyfi
    # sırayla işleniyordu ve yeni ay sayfası, o an workbook'ta bulunan "en güncel"
    # sayfadan kopyalandığı için Ağustos'un şablonunun Temmuz mu Haziran mı olacağı
    # şansa kalıyordu. Kronolojik sıra bunu deterministik yapar.
    donem_sorgu = select(Donem).where(Donem.sirket_id == current_user.sirket_id)
    if donem_id is not None:
        donem_sorgu = donem_sorgu.where(Donem.id == donem_id)
    donemler = session.exec(donem_sorgu.order_by(Donem.yil, Donem.ay)).all()

    tatiller = {t.tarih for t in session.exec(
        select(Tatil).where(Tatil.sirket_id == current_user.sirket_id)
    ).all()}

    sirket = session.get(Sirket, current_user.sirket_id)

    yazilan_sayfalar: list = []
    eklenen_personel: list[str] = []
    silinen_personel: list[str] = []
    yazilamayan_personel: list[str] = []
    bos_donemler: list[str] = []
    tamamlanmamis_donemler: list[str] = []

    for donem in donemler:
        ay_adi = f"{TR_AYLAR[donem.ay - 1]} {donem.yil}"
        girisi_olan_personel_id = {
            g.personel_id
            for g in session.exec(select(PuantajGirisi).where(PuantajGirisi.donem_id == donem.id)).all()
        }
        if not girisi_olan_personel_id:
            # Hiç girişi olmayan dönemde uygulama kaynak DEĞİLDİR — master'daki
            # tarihî sayfa (ör. müşterinin kendi Ocak-Haziran verisi) olduğu gibi
            # bırakılır. donem_id ile açıkça istense bile: 2026-08-25'ten beri
            # workbook master'a geri yazıldığı için buraya dokunmak müşterinin
            # geçmiş verisini kalıcı olarak silmek demekti.
            bos_donemler.append(ay_adi)
            continue

        if donem.excel_sheet_adi and donem.excel_sheet_adi in wb.sheetnames:
            ws = wb[donem.excel_sheet_adi]
        else:
            # Bug (2026-07-06): dosyada bu ay için hiç sayfa yoksa (ör. Excel'in
            # kapsamadığı yeni/güncel bir ay) export SESSİZCE bu dönemi atlıyordu —
            # kullanıcı grid'de veri girmesine rağmen export dosyasında sekmesi hiç
            # oluşmuyordu. Artık en güncel mevcut sayfa şablon alınıp yeni ay için
            # kopyalanıyor (roster + format + formüller dahil).
            yeni_baslik = f"{TR_AYLAR[donem.ay - 1]} {donem.yil} BANKA"
            if yeni_baslik in wb.sheetnames:
                ws = wb[yeni_baslik]  # önceki bir export'ta zaten oluşturulmuş
            else:
                referans_ws = en_guncel_sheet(wb, mapping.sheet_mapping, once=(donem.yil, donem.ay))
                if referans_ws is None:
                    logger.warning("%s için şablon alınacak sayfa yok, atlandı", ay_adi)
                    continue  # şablon alınacak hiçbir sayfa yok — oluşturulamaz
                referans_donem = parse_sheet_donem(referans_ws.title)
                ws = yeni_ay_sayfasi_olustur(
                    wb, referans_ws, mapping,
                    referans_donem=referans_donem, yeni_donem=(donem.yil, donem.ay),
                    yeni_baslik=yeni_baslik,
                )
                sayfayi_kronolojik_yerlestir(wb, ws, (donem.yil, donem.ay))
                logger.info("Yeni ay sayfası oluşturuldu: %s (şablon: %s)", yeni_baslik, referans_ws.title)
            donem.excel_sheet_adi = yeni_baslik
            session.add(donem)
            session.commit()
        sonuc_by_row: dict[int, dict] = {}
        dokunulan_satirlar: set[int] = set()

        personel_by_ad = {
            p.ad_soyad: p
            for p in session.exec(select(Personel).where(Personel.sirket_id == current_user.sirket_id)).all()
        }

        # Kullanıcı kararı (2026-08-25): dönem başlamadan ÖNCE işten ayrılmış
        # personel o ayın sayfasında hiç görünmemeli. Önceden satırı duruyor ama
        # hiç girişi olmadığı için Ç.GÜN'ü boş kalıyordu — müşteri geri bildirimi:
        # "sarı olan sütun rast gele dolmuş". Ay İÇİNDE ayrılan silinmez
        # (donemde_calisiyor_mu, 2026-07-04 kararı: çıktığı ayın sonuna kadar kalır).
        silinecek_satirlar: set[int] = set()
        for kayit in read_roster(ws, mapping):
            personel_obj = personel_by_ad.get(kayit.alanlar.get("ad_soyad"))
            if personel_obj is not None and not donemde_calisiyor_mu(personel_obj, donem.yil, donem.ay):
                silinecek_satirlar.add(kayit.excel_satir)
                silinen_personel.append(f"{personel_obj.ad_soyad} ({ay_adi})")
        roster_satirlarini_sil(ws, mapping, silinecek_satirlar)

        # Satır numarası kişi bazında SABİT değildir — biri Ocak'ta 5. satırdaysa
        # Haziran'da 3. satırda olabilir (personel devri, roster sırası kayar) ve
        # yukarıdaki silme de numaraları kaydırır. Bu yüzden `Personel.excel_kaynak_satir`
        # (en son import'un satırı) yerine, bu dönemin KENDİ sayfasını tazeden
        # okuyup ad-soyad eşleşmesiyle doğru satırı buluyoruz.
        satir_by_ad_soyad = {
            kayit.alanlar.get("ad_soyad"): kayit.excel_satir
            for kayit in read_roster(ws, mapping)
        }

        # Bug (2026-08-25, SESSİZ VERİ KAYBI): uygulamadan eklenen personelin
        # Excel roster'ında satırı olmadığı için puantajı export'a HİÇ yazılmıyor,
        # üstelik uyarı da verilmiyordu (ör. RÜMEYSA TEMURAYAK, Ağustos 2026 —
        # 25 günlük giriş sessizce düşmüştü). Artık eksik olana satır açılıyor.
        for personel_id in sorted(girisi_olan_personel_id):
            personel = session.get(Personel, personel_id)
            if personel is None or personel.ad_soyad in satir_by_ad_soyad:
                continue
            yeni_satir = roster_satiri_ekle(
                ws, mapping,
                {
                    "ad_soyad": personel.ad_soyad,
                    "maas": efektif_maas(session, personel.id, donem),
                    "ng": efektif_ng(session, personel.id, donem),
                },
            )
            if yeni_satir is None:
                yazilamayan_personel.append(f"{personel.ad_soyad} ({ay_adi})")
            else:
                satir_by_ad_soyad[personel.ad_soyad] = yeni_satir
                eklenen_personel.append(f"{personel.ad_soyad} ({ay_adi})")

        # Bug (2026-07-06): N.G kolonu roster'da hep ÖNCEKİ ayın statik değerini
        # gösteriyordu (ör. Haziran'dan kopyalanan sayfada hep 30) — kullanıcı
        # geri bildirimi: "Ç.GÜN 31 olanları alamıyor, sanırım N.G 30 olduğu için".
        # Bizim hesabımız (E/Ç.GÜN, J/FM vb.) doğru N.G'yi (efektif_ng) kullanıyordu
        # ama müşterinin KENDİ formülleri (Y.TL=MAAŞ/N.G gibi) hâlâ eski N.G'yi
        # okuyup yanlış hesaplıyordu. Artık her dönem için TÜM roster satırlarında
        # (dokunulmuş olsun olmasın) N.G, o kişinin o ay için efektif değeriyle
        # güncelleniyor.
        ng_kolon = next(
            (o.kolon_harfi for o in mapping.sheet_mapping.okuma_alanlari if o.hedef_alan == "ng" and o.kolon_harfi),
            None,
        )
        # Aynı sınıf hata (2026-07-06): N.G'deki gibi, MAAŞ kolonu da müşterinin
        # KENDİ formülleri (Y.TL=MAAŞ/N.G vb.) için roster'da referans — zam
        # girildiğinde bu kolon güncellenmezse müşterinin kendi hesapları eski
        # maaşla yanlış sonuç üretmeye devam eder. `efektif_maas` ile aynı mantık.
        maas_kolon = next(
            (o.kolon_harfi for o in mapping.sheet_mapping.okuma_alanlari if o.hedef_alan == "maas" and o.kolon_harfi),
            None,
        )
        if ng_kolon or maas_kolon:
            for ad_soyad, satir in satir_by_ad_soyad.items():
                personel_obj = personel_by_ad.get(ad_soyad)
                if personel_obj is None:
                    continue
                if ng_kolon:
                    ws[f"{ng_kolon}{satir}"] = efektif_ng(session, personel_obj.id, donem)
                if maas_kolon:
                    ws[f"{maas_kolon}{satir}"] = efektif_maas(session, personel_obj.id, donem)

        for personel_id in girisi_olan_personel_id:
            personel = session.get(Personel, personel_id)
            if personel is None:
                continue
            bu_donem_satiri = satir_by_ad_soyad.get(personel.ad_soyad)
            if bu_donem_satiri is None:
                continue  # satır açılamadı — `yazilamayan_personel` ile raporlanıyor
            tip = session.get(CalismaTipi, personel.calisma_tipi_id)
            gunluk_saat = tip.gunluk_saat if tip else 7.5

            girisler = [
                GunlukGiris(
                    tarih=g.tarih, gun_durumu=g.gun_durumu,
                    izin_saat=g.izin_saat, fm_saat=g.fm_saat,
                )
                # Gelecek tarihli girişler elenir — `gelecek_gun` o günleri zaten
                # Ç.GÜN'den düşüyor, ikisi birden çift kesinti olurdu.
                for g in sayilan_girisler(
                    session.exec(
                        select(PuantajGirisi).where(
                            PuantajGirisi.donem_id == donem.id, PuantajGirisi.personel_id == personel_id
                        )
                    ).all(),
                    donem.yil, donem.ay,
                )
            ]
            sonuc = hesapla(
                maas=efektif_maas(session, personel.id, donem), ng=efektif_ng(session, personel.id, donem), gunluk_saat=gunluk_saat,
                girisler=girisler, tatiller=tatiller,
                ise_disi_gun=ise_disi_gun_sayisi(personel, donem.yil, donem.ay),
                gelecek_gun=gelecek_gun_sayisi(personel, donem.yil, donem.ay),
                raporlu_politikasi=sirket.raporlu_politikasi if sirket else "hic_odeme",
                raporlu_esik_gun=sirket.raporlu_esik_gun if sirket else 0,
                hafta_ici_fm_orani=tip.hafta_ici_fm_orani if tip else 1.5,
                hafta_sonu_fm_orani=tip.hafta_sonu_fm_orani if tip else 2.0,
                resmi_tatil_fm_orani=tip.resmi_tatil_fm_orani if tip else 2.0,
                hafta_tatili_gunleri=frozenset(tip.hafta_tatili_gunleri) if tip else frozenset({6}),
            )
            sonuc_by_row[bu_donem_satiri] = {
                "cgun": sonuc.cgun, "izin_saat": sonuc.izin_saat,
                "fm_saat": sonuc.fm_saat, "fm_tl": sonuc.fm_tl,
            }
            dokunulan_satirlar.add(bu_donem_satiri)

        # Master artık kalıcı olduğu için, girişi kaldırılan bir kişinin ÖNCEKİ
        # export'tan kalan değeri sayfada asılı kalmasın: bu dönemin roster'ındaki
        # dokunulmamış satırlar da yazma alanları için sıfırlanır (sonuc_by_row'da
        # olmadıkları için `sifirsa` kuralı boş/fallback değeri yazar). Sonuç,
        # sayfa her export'ta sıfırdan üretiliyormuş gibi deterministik kalır.
        sifirlanacak = {s for s in satir_by_ad_soyad.values() if s is not None} - dokunulan_satirlar
        write_export(ws, mapping, sonuc_by_row, dokunulan_satirlar | sifirlanacak)
        yazilan_sayfalar.append(ws)
        bugun = bugun_tr()
        if (bugun.year, bugun.month) <= (donem.yil, donem.ay):
            son_gun = calendar.monthrange(donem.yil, donem.ay)[1]
            gecen = bugun.day if (bugun.year, bugun.month) == (donem.yil, donem.ay) else 0
            tamamlanmamis_donemler.append(f"{ay_adi} ({gecen}/{son_gun} gün)")
        logger.info(
            "Export: %s | %s kişi yazıldı, %s satır sıfırlandı",
            ay_adi, len(dokunulan_satirlar), len(sifirlanacak),
        )

    # Dosya açıldığında en güncel yazılan ay görünsün (dönemler kronolojik sıralı).
    if yazilan_sayfalar:
        aktif_sayfa_yap(wb, yazilan_sayfalar[-1])
        _master_kaydet(wb, master_path)

    buffer = io.BytesIO()
    wb.calculation.fullCalcOnLoad = True
    wb.save(buffer)
    buffer.seek(0)

    uyarilar: list[str] = []
    if eklenen_personel:
        uyarilar.append(
            "Excel'de satırı olmayan personel için yeni satır açıldı: " + ", ".join(eklenen_personel)
        )
    if silinen_personel:
        uyarilar.append(
            "Dönem başlamadan önce işten ayrıldığı için sayfadan çıkarıldı: "
            + ", ".join(silinen_personel)
        )
    if tamamlanmamis_donemler:
        uyarilar.append(
            "Ay tamamlanmadı — Ç.GÜN bugüne kadar geçen güne göre hesaplandı: "
            + ", ".join(tamamlanmamis_donemler)
        )
    if yazilamayan_personel:
        uyarilar.append("YAZILAMADI (satır açılamadı): " + ", ".join(yazilamayan_personel))
    if donem_id is not None and bos_donemler:
        uyarilar.append(
            "Hiç puantaj girişi olmadığı için dokunulmayan dönem: " + ", ".join(bos_donemler)
        )

    headers = {"Content-Disposition": "attachment; filename=puantaj_export.xlsx"}
    if uyarilar:
        # HTTP başlığı yalnızca latin-1 taşır — Türkçe karakterler için yüzde kodlama.
        headers["X-Puantaj-Uyari"] = quote(" | ".join(uyarilar))

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
