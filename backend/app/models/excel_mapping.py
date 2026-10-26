# -*- coding: utf-8 -*-
"""models/excel_mapping.py — ExcelMappingTemplate: mapping config'in DB'de saklanan hâli."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.zaman import simdi_utc


class ExcelMappingTemplate(SQLModel, table=True):
    __tablename__ = "excel_mapping_template"

    id: Optional[int] = Field(default=None, primary_key=True)
    sirket_id: Optional[int] = Field(default=None, foreign_key="sirket.id")
    ad: str                                       # "BESIM Standart"
    versiyon: int = 1
    durum: str = "draft"                           # "draft" | "approved"
    mapping_json: dict = Field(sa_column=Column(JSON))  # ExcelMappingConfig.model_dump()
    created_by_id: Optional[int] = Field(default=None, foreign_key="kullanici.id")
    created_at: datetime = Field(default_factory=simdi_utc)
    approved_at: Optional[datetime] = None
