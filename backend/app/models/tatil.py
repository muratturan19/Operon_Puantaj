# -*- coding: utf-8 -*-
"""models/tatil.py — Resmi tatil (Pazar zaten kod içinde otomatik ×2, ayrıca kayda gerek yok)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Tatil(SQLModel, table=True):
    __tablename__ = "tatil"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: int = Field(foreign_key="sirket.id")
    tarih: date
    aciklama: Optional[str] = None
    kaynak: str = "sistem_varsayilan"    # | "ozel"
