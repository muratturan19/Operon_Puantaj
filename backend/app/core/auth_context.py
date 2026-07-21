# -*- coding: utf-8 -*-
"""
core/auth_context.py — SaaS modda paylaşılan JWT-doğrulama dependency'si.

`core/database.py::get_session_saas` ve `core/security.py::get_current_user_saas`
İKİSİ de bu dependency'ye ihtiyaç duyar (tenant_slug/role için). Ortak bir modülde
tutulmasının nedeni dairesel import'u önlemek (database.py ↔ security.py).
FastAPI aynı request içinde dependency sonucunu cache'lediği için, JWT
doğrulama/portal-key-fetch işi tek bir request'te yalnızca BİR kez çalışır.
"""
from __future__ import annotations

from typing import Dict

from fastapi import HTTPException, Request, status

from app.services.portal_sso_service import PortalSSOService


async def get_tenant_context(request: Request) -> Dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum bulunamadı",
        )
    try:
        return await PortalSSOService.validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
