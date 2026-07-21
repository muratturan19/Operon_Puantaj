# -*- coding: utf-8 -*-
"""
models/rbac.py — Rol/Kullanıcı.

`Rol.izinler` bilinçli olarak sabit bir enum DEĞİL, açık bir JSON sözlük: "Kullanıcı
maaş tutarını görmesin" gibi politikalar, şema migration'ı gerektirmeden yeni bir
izin anahtarı eklenerek uygulanabilsin diye. Seed roller: admin, kullanici, gm
(CLAUDE.md §8.7 — Kurulum Sihirbazı kararı, 2026-07-04).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Rol(SQLModel, table=True):
    __tablename__ = "rol"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    kod: str = Field(index=True)              # "admin" | "kullanici" | "gm" | özel
    ad: str
    izinler: dict = Field(default_factory=dict, sa_column=Column(JSON))
    sistem_varsayilani: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Kullanici(SQLModel, table=True):
    __tablename__ = "kullanici"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    kullanici_adi: str = Field(unique=True, index=True)
    ad_soyad: str
    email: Optional[str] = None
    hashed_password: str
    rol_id: int = Field(foreign_key="rol.id")
    aktif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
