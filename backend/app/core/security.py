# -*- coding: utf-8 -*-
"""
core/security.py — Parola hash'leme, JWT üretimi/doğrulaması, yetki kontrolü.

Faz 1'de yalnızca yerel kullanıcı adı/şifre auth var. Faz 2 (§8.8) AUTH_MODE=saas
ile Portal SSO (RS256 JWT) auth adaptörünü ekliyor — `get_current_user` import
zamanında `settings.auth_mode`'a göre iki implementasyondan birine bağlanır,
`require_permission` ve tüm route imzaları DEĞİŞMİYOR (iç izin modeli iki modda
da aynı kalıyor, CLAUDE.md §8.2 kararı).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.auth_context import get_tenant_context
from app.core.config import get_settings
from app.core.database import get_session, get_session_saas
from app.models.rbac import Kullanici, Rol
from app.models.sirket import Sirket

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(kullanici: Kullanici) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(kullanici.id),
        "kullanici_adi": kullanici.kullanici_adi,
        "sirket_id": kullanici.sirket_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def authenticate_user(session: Session, kullanici_adi: str, password: str) -> Optional[Kullanici]:
    kullanici = session.exec(
        select(Kullanici).where(Kullanici.kullanici_adi == kullanici_adi)
    ).first()
    if not kullanici or not kullanici.aktif:
        return None
    if not verify_password(password, kullanici.hashed_password):
        return None
    return kullanici


def get_current_user_onprem(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Kullanici:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    kullanici = session.get(Kullanici, int(user_id))
    if kullanici is None or not kullanici.aktif:
        raise credentials_exception
    return kullanici


def get_current_user_saas(
    ctx: dict = Depends(get_tenant_context),
    session: Session = Depends(get_session_saas),
) -> Kullanici:
    """Portal SSO — JWT'deki tenant_slug/role/username'e göre yerel Kullanici'yi
    bulur; ilk SSO girişinde JIT (just-in-time) olarak oluşturur (CLAUDE.md §8.8
    madde 3). `ctx` ve `session` aynı tenant_slug'ı çözer — FastAPI aynı request
    içinde `get_tenant_context`'i bir kez çalıştırıp cache'ler.
    """
    sirket = session.exec(select(Sirket)).first()
    if sirket is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant DB'sinde Şirket kaydı yok — migration başarısız olmuş olabilir",
        )

    rol = session.exec(
        select(Rol).where(Rol.sirket_id == sirket.id, Rol.kod == ctx.get("role"))
    ).first()
    if rol is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Portal rolü '{ctx.get('role')}' Puantaj'da tanımlı değil — "
                "tenant_app_settings.roles = 'admin,kullanici,gm' olarak ayarlanmalı"
            ),
        )

    username = ctx.get("username")
    kullanici = session.exec(
        select(Kullanici).where(Kullanici.sirket_id == sirket.id, Kullanici.kullanici_adi == username)
    ).first()

    if kullanici is None:
        kullanici = Kullanici(
            sirket_id=sirket.id,
            kullanici_adi=username,
            ad_soyad=username,
            hashed_password=hash_password(secrets.token_urlsafe(32)),  # asla kullanılmaz, NOT NULL için
            rol_id=rol.id,
        )
        session.add(kullanici)
        session.commit()
        session.refresh(kullanici)
    elif kullanici.rol_id != rol.id:
        kullanici.rol_id = rol.id  # portal'da rol değişmişse senkronize et
        session.add(kullanici)
        session.commit()
        session.refresh(kullanici)

    if not kullanici.aktif:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kullanıcı pasif")

    kullanici.last_login = datetime.utcnow()
    session.add(kullanici)
    session.commit()
    return kullanici


get_current_user = get_current_user_saas if get_settings().auth_mode == "saas" else get_current_user_onprem


def require_permission(*permission_keys: str):
    """
    Rol.izinler JSON sözlüğünden ince taneli izin kontrolü yapan dependency
    fabrikası. Sabit rol enum'una göre DEĞİL — CLAUDE.md §7'de kararlaştırılan
    genişletilebilir izin modeli budur (ör. ileride "gorebilir_maas_tutari").

    Birden fazla anahtar verilirse HEPSİ gerekir (AND) — kullanıcı kararı
    (2026-07-04): Excel export ve Denetim Kaydı gibi maaş TUTARI içeren
    çıktılar, `excel_disa_aktarabilir`/`audit_gorebilir` iznine sahip ama
    `gorebilir_maas_tutari` olmayan bir rol için de erişilebilir kalmasın diye
    — gelecekteki Rol Yönetimi UI'ı bu ikisini bağımsız checkbox'lar olarak
    sunacağı için, izinlerin rastlantısal eşleşmesine güvenilemez.
    """

    def _check(
        current_user: Kullanici = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> Kullanici:
        rol = session.get(Rol, current_user.rol_id)
        if rol is None or not all(rol.izinler.get(key, False) for key in permission_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz yok",
            )
        return current_user

    return _check
