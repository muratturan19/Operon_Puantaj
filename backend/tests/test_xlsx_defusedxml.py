"""Güvenlik regresyonu (2026-10-24): yüklenen Excel'in XML'i defusedxml ile ayrıştırılır.

CPython'un gömülü expat'i (2.8.x/2.9.0) CVE-2026-115506'dan etkileniyor (billion-laughs koruması geç devreye
giriyor → CPU DoS). openpyxl, defusedxml kuruluysa onu kendiliğinden kullanır ve DTD/varlık tanımı içeren XML'i
reddeder. Bu test bağımlılığın düşmesini ve korumanın kapanmasını yakalar.
"""
import io
import zipfile

import pytest

openpyxl = pytest.importorskip("openpyxl")


def _varlik_tanimli_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    wb.active["A1"] = "x"
    tampon = io.BytesIO()
    wb.save(tampon)
    kaynak = zipfile.ZipFile(io.BytesIO(tampon.getvalue()))
    cikti = io.BytesIO()
    with zipfile.ZipFile(cikti, "w") as hedef:
        for ad in kaynak.namelist():
            veri = kaynak.read(ad)
            if ad == "xl/worksheets/sheet1.xml":
                doctype = (b'<!DOCTYPE w [<!ENTITY a "aaaaaaaaaa">'
                           b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>')
                if veri.startswith(b"<?xml"):          # başlık varsa ondan sonra, yoksa en başa
                    son = veri.index(b"?>") + 2
                    veri = veri[:son] + doctype + veri[son:]
                else:
                    veri = doctype + veri
                assert b"<!DOCTYPE" in veri
            hedef.writestr(ad, veri)
    return cikti.getvalue()


def test_openpyxl_defusedxml_kullaniyor():
    from openpyxl.xml import DEFUSEDXML
    assert DEFUSEDXML is True


@pytest.mark.parametrize("salt_okunur", [False, True])
def test_varlik_tanimli_excel_reddedilir(salt_okunur):
    with pytest.raises(Exception) as hata:
        wb = openpyxl.load_workbook(io.BytesIO(_varlik_tanimli_xlsx()), read_only=salt_okunur, data_only=True)
        for satir in wb.active.iter_rows(values_only=True):
            pass
    # openpyxl, defusedxml'in EntitiesForbidden/DTDForbidden hatasını ValueError içine sarabilir → zinciri tara
    zincir, e = [], hata.value
    while e is not None and len(zincir) < 10:
        zincir.append(type(e).__name__)
        e = e.__cause__ or e.__context__
    assert any("Forbidden" in ad for ad in zincir), zincir
