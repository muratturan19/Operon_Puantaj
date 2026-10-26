# -*- coding: utf-8 -*-
"""
models/hata.py — Yakalanmamış sunucu hatalarının kalıcı kaydı (append-only).

Neden var (2026-08-25): müşteri "export bambaşka bir tablo veriyor" diye hata
bildirdiğinde elimizde HİÇBİR kayıt yoktu — ne uygulama logu (bkz.
alembic/env.py'deki fileConfig notu) ne de kalıcı bir hata tablosu. `audit_log`
yalnızca iş değişikliklerini (create/update/delete) tutar, hatayı tutmaz.
Bu tablo, kullanıcıya gösterilen `istek_id` ile birebir eşleşir: müşteri
"E-3f9a2c1b kodlu hata" dediğinde kayıt tek sorguyla bulunur.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc


class HataKaydi(SQLModel, table=True):
    __tablename__ = "error_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    istek_id: str = Field(index=True)                 # kullanıcıya gösterilen takip kodu
    zaman: datetime = Field(default_factory=simdi_utc, index=True)
    yol: str                                          # "/api/excel/export"
    metod: str                                        # "GET" | "POST" | ...
    sorgu: Optional[str] = None                       # query string (parametreler teşhis için kritik)
    kullanici: Optional[str] = None                   # JWT'deki username (session açılamamış olabilir)
    sirket_id: Optional[int] = None                   # FK YOK: hata anında şirket kaydı okunamamış olabilir
    hata_tipi: str                                    # "ValueError", "KeyError", ...
    mesaj: str
    traceback_metni: str = Field(sa_column=Column(Text))
