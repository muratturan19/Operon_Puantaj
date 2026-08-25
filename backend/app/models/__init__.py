# -*- coding: utf-8 -*-
"""models — tüm SQLModel tablolarını tek noktadan içe aktarır (Alembic autogenerate için şart)."""
from app.models.sirket import Sirket
from app.models.rbac import Rol, Kullanici
from app.models.calisma_tipi import CalismaTipi
from app.models.personel import Personel
from app.models.personel_maas_gecmisi import PersonelMaasGecmisi
from app.models.donem import Donem
from app.models.personel_donem_ayar import PersonelDonemAyar
from app.models.tatil import Tatil
from app.models.puantaj import PuantajGirisi
from app.models.audit import AuditLog
from app.models.hata import HataKaydi
from app.models.excel_mapping import ExcelMappingTemplate

__all__ = [
    "Sirket",
    "Rol",
    "Kullanici",
    "CalismaTipi",
    "Personel",
    "PersonelMaasGecmisi",
    "Donem",
    "PersonelDonemAyar",
    "Tatil",
    "PuantajGirisi",
    "AuditLog",
    "HataKaydi",
    "ExcelMappingTemplate",
]
