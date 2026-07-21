# -*- coding: utf-8 -*-
"""api/routes/sso.py — Portal SSO giriş endpoint'i (yalnızca AUTH_MODE=saas).

Platform standardı (SaaS_Platform CLAUDE.md §6 Adım 5, apps/SRM/backend/app/api/sso.py
ile birebir aynı): Portal admin panelinden "Aç" ile POST edilen RS256 JWT'yi
doğrular, `access_token` httponly cookie'sini set eder.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.services.portal_sso_service import PortalSSOService

router = APIRouter(prefix="/api", tags=["sso"])


@router.post("/sso/login")
async def sso_login(token: str = Form(...)):
    try:
        await PortalSSOService.validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7200,
    )
    return resp


@router.post("/sso/logout")
async def sso_logout():
    """httponly access_token cookie'sini temizler — frontend'in JS'ten silemediği
    tek yol bu (bkz. AuthContext.cikisYap)."""
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("access_token")
    return resp
