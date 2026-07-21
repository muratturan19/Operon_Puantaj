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

import io
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    en_guncel_sheet,
    list_matching_sheets,
    open_workbook,
    parse_sheet_donem,
    read_roster,
    write_export,
    yeni_ay_sayfasi_olustur,
)
from app.services.payroll_calc import GunlukGiris, hesapla
from app.services.personel_filtre import efektif_ng, ise_disi_gun_sayisi

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

    # Kapsam: donem_id verilmezse GİRİŞİ OLAN TÜM DÖNEMLER yazılır (Puantaj_Brief §10 — kapanmış karar)
    donem_sorgu = select(Donem).where(Donem.sirket_id == current_user.sirket_id)
    if donem_id is not None:
        donem_sorgu = donem_sorgu.where(Donem.id == donem_id)
    donemler = session.exec(donem_sorgu).all()

    tatiller = {t.tarih for t in session.exec(
        select(Tatil).where(Tatil.sirket_id == current_user.sirket_id)
    ).all()}

    sirket = session.get(Sirket, current_user.sirket_id)

    for donem in donemler:
        girisi_olan_personel_id = {
            g.personel_id
            for g in session.exec(select(PuantajGirisi).where(PuantajGirisi.donem_id == donem.id)).all()
        }
        if not girisi_olan_personel_id and donem_id is None:
            continue  # "işaretli tüm aylar" — hiç girişi olmayan dönem export'a girmez

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
                referans_ws = en_guncel_sheet(wb, mapping.sheet_mapping)
                if referans_ws is None:
                    continue  # şablon alınacak hiçbir sayfa yok — oluşturulamaz
                referans_donem = parse_sheet_donem(referans_ws.title)
                ws = yeni_ay_sayfasi_olustur(
                    wb, referans_ws, mapping,
                    referans_donem=referans_donem, yeni_donem=(donem.yil, donem.ay),
                    yeni_baslik=yeni_baslik,
                )
            donem.excel_sheet_adi = yeni_baslik
            session.add(donem)
            session.commit()
        sonuc_by_row: dict[int, dict] = {}
        dokunulan_satirlar: set[int] = set()

        # Satır numarası kişi bazında SABİT değildir — biri Ocak'ta 5. satırdaysa
        # Haziran'da 3. satırda olabilir (personel devri, roster sırası kayar).
        # Bu yüzden `Personel.excel_kaynak_satir` (en son import'un satırı) yerine,
        # bu dönemin KENDİ sayfasını tazeden okuyup ad-soyad eşleşmesiyle doğru
        # satırı buluyoruz.
        satir_by_ad_soyad = {
            kayit.alanlar.get("ad_soyad"): kayit.excel_satir
            for kayit in read_roster(ws, mapping)
        }

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
        if ng_kolon:
            aktif_personel_by_ad = {
                p.ad_soyad: p
                for p in session.exec(select(Personel).where(Personel.sirket_id == current_user.sirket_id)).all()
            }
            for ad_soyad, satir in satir_by_ad_soyad.items():
                personel_obj = aktif_personel_by_ad.get(ad_soyad)
                if personel_obj is None:
                    continue
                ws[f"{ng_kolon}{satir}"] = efektif_ng(session, personel_obj.id, donem)

        for personel_id in girisi_olan_personel_id:
            personel = session.get(Personel, personel_id)
            if personel is None:
                continue
            bu_donem_satiri = satir_by_ad_soyad.get(personel.ad_soyad)
            if bu_donem_satiri is None:
                continue  # bu kişi bu dönemin sayfasında yok (ör. henüz işe girmemiş)
            tip = session.get(CalismaTipi, personel.calisma_tipi_id)
            gunluk_saat = tip.gunluk_saat if tip else 7.5

            girisler = [
                GunlukGiris(
                    tarih=g.tarih, gun_durumu=g.gun_durumu,
                    izin_saat=g.izin_saat, fm_saat=g.fm_saat,
                )
                for g in session.exec(
                    select(PuantajGirisi).where(
                        PuantajGirisi.donem_id == donem.id, PuantajGirisi.personel_id == personel_id
                    )
                ).all()
            ]
            sonuc = hesapla(
                maas=personel.maas, ng=efektif_ng(session, personel.id, donem), gunluk_saat=gunluk_saat,
                girisler=girisler, tatiller=tatiller,
                ise_disi_gun=ise_disi_gun_sayisi(personel, donem.yil, donem.ay),
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

        write_export(ws, mapping, sonuc_by_row, dokunulan_satirlar)

    buffer = io.BytesIO()
    wb.calculation.fullCalcOnLoad = True
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=puantaj_export.xlsx"},
    )
