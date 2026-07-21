# -*- coding: utf-8 -*-
"""
core/tenant_scope.py — Tenant'a özgü dosya depolama önekini çözer.

Bug (2026-07-06, gerçek üretim olayı): `data/uploads/{sirket_id}_master.xlsx`
yalnızca sirket_id'ye göre isimlendiriliyordu. SaaS modda her tenant'ın kendi
izole DB'si vardır ve o DB'deki tek Sirket satırı HER ZAMAN id=1'den başlar —
yani iki farklı tenant (ör. "emine" ve "platform_admin") aynı container'ın
paylaşılan dosya sisteminde AYNI "1_master.xlsx" yoluna yazıyordu, birbirinin
Excel dosyasını sessizce eziyordu. Bu modül, dosya yoluna tenant_slug'ı (SaaS
modda) veya sabit bir tekil anahtarı (onprem modda, zaten tek kurulum) katan
bir önek üretir.
"""
from __future__ import annotations

from fastapi import Depends

from app.core.auth_context import get_tenant_context
from app.core.config import get_settings


def _storage_onceki_onprem() -> str:
    return "onprem"


async def _storage_onceki_saas(ctx: dict = Depends(get_tenant_context)) -> str:
    return ctx["tenant_slug"]


get_storage_onceki = _storage_onceki_saas if get_settings().auth_mode == "saas" else _storage_onceki_onprem
