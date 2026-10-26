# -*- coding: utf-8 -*-
"""api/routes/auth.py — Yerel kullanıcı adı/şifre girişi (Faz 1). Portal SSO Faz 2+ (CLAUDE.md §8.2)."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session

from app.core.zaman import simdi_utc
from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import authenticate_user, create_access_token, get_current_user
from app.models.rbac import Kullanici, Rol

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    kullanici_adi: str
    ad_soyad: str
    rol_kod: str
    izinler: dict


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    if get_settings().auth_mode == "saas":
        # SaaS modda giriş yalnızca Portal SSO ile yapılır (bkz. api/routes/sso.py);
        # yerel şifre girişi hem anlamsız hem de JIT kullanıcıların rastgele
        # şifresiyle zaten çalışmaz.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    kullanici = authenticate_user(session, form_data.username, form_data.password)
    if kullanici is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    kullanici.last_login = simdi_utc()
    session.add(kullanici)
    session.commit()

    return TokenResponse(access_token=create_access_token(kullanici))


@router.get("/me", response_model=MeResponse)
def me(
    current_user: Kullanici = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MeResponse:
    rol = session.get(Rol, current_user.rol_id)
    return MeResponse(
        id=current_user.id,
        kullanici_adi=current_user.kullanici_adi,
        ad_soyad=current_user.ad_soyad,
        rol_kod=rol.kod if rol else "",
        izinler=rol.izinler if rol else {},
    )
