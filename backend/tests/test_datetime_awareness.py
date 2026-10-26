# -*- coding: utf-8 -*-
"""Saat dilimsiz datetime'ın DB'ye yazılmasını engelleyen korumalar.

Arka plan (2026-10-26): sqlmodel 0.0.47+ saat dilimsiz değeri bağlama sırasında
'Datetime values must have timezone information' ile reddeder. 24 Ekim bakımında imaj
yeniden derlenince sqlmodel 0.0.48'e çıktı; SSO girişindeki `last_login = datetime.utcnow()`
her girişte 500 verdi ve kimse uygulamaya giremedi. Hata kaydının kendisi de aynı sebeple
yazılamadı. Bu testler tablo varsayılanlarını, gerçek bir ORM yazma-okuma turunu ve
kaynakta eski kalıbın geri gelmesini denetler.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, select

import app.models as models
from app.models import HataKaydi, Kullanici, Rol, Sirket

ROOT = Path(__file__).resolve().parent.parent / "app"


def _table_models():
    return [getattr(models, n) for n in models.__all__
            if getattr(getattr(models, n), "__table__", None) is not None]


def test_every_table_default_datetime_is_timezone_aware():
    checked = 0
    for cls in _table_models():
        row = cls.model_construct()  # default_factory dahil varsayılanları üretir
        for name, value in vars(row).items():
            if isinstance(value, datetime):
                checked += 1
                assert value.tzinfo is not None, f"{cls.__name__}.{name} saat dilimsiz"
                assert value.utcoffset() == timedelta(0)
    assert checked >= 11  # beklenenden az alan görüldüyse test boşa geçiyor demektir


def test_orm_insert_and_update_with_now_utc_roundtrip():
    from app.core.zaman import simdi_utc

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[Sirket.__table__, Rol.__table__,
                                                 Kullanici.__table__, HataKaydi.__table__])
    with Session(engine) as s:
        sirket = Sirket(ad="Firma")
        s.add(sirket)
        s.commit()
        s.refresh(sirket)
        rol = Rol(sirket_id=sirket.id, kod="admin", ad="Admin")
        s.add(rol)
        s.commit()
        s.refresh(rol)
        k = Kullanici(sirket_id=sirket.id, kullanici_adi="u", ad_soyad="U", hashed_password="x",
                      rol_id=rol.id)
        s.add(k)
        s.add(HataKaydi(istek_id="E-1", yol="/api/auth/me", metod="GET", hata_tipi="X", mesaj="m",
                        traceback_metni="tb"))
        s.commit()  # naive varsayılan olsaydı StatementError
        k.last_login = simdi_utc()  # SSO girişindeki atama
        s.add(k)
        s.commit()
    with Session(engine) as s:
        k = s.exec(select(Kullanici)).one()
        assert k.last_login is not None and k.last_login.tzinfo is not None
        assert s.exec(select(HataKaydi)).one().zaman.tzinfo is not None


def _python_files():
    for p in ROOT.rglob("*.py"):
        if "__pycache__" not in p.parts:
            yield p


def test_no_naive_utcnow_in_source():
    pattern = re.compile(r"datetime\.utcnow\b")
    offenders = [f"{p.relative_to(ROOT)}:{i}" for p in _python_files()
                 for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if pattern.search(line)]
    assert not offenders, "saat dilimsiz utcnow: " + ", ".join(offenders)
