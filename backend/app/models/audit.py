# -*- coding: utf-8 -*-
"""
models/audit.py — Append-only denetim günlüğü.

Desen `E:\\Mira\\MQ_v3\\backend\\app\\utils\\audit_logger.py`'den doğrulandı:
tek satır/aksiyon, `changes` alan-bazlı old/new JSON sözlüğü. UPDATE/DELETE
kod seviyesinde yasak — bkz. services/audit.py, bu tabloya yalnızca INSERT yapar.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    aktor_kullanici_id: Optional[int] = Field(default=None, foreign_key="kullanici.id")
    entity_tipi: str = Field(index=True)     # "PuantajGirisi" | "CalismaTipi" | "Personel" | ...
    entity_id: str = Field(index=True)
    aksiyon: str                              # "create" | "update" | "delete"
    changes: dict = Field(default_factory=dict, sa_column=Column(JSON))  # {"alan": {"old": ..., "new": ...}}
    zaman: datetime = Field(default_factory=simdi_utc, index=True)
    ip_adresi: Optional[str] = None
