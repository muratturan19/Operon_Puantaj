# -*- coding: utf-8 -*-
"""Portal SSO JWT doğrulama — Platform standardı (CLAUDE.md §4.2/6, §8.8).

Yalnızca AUTH_MODE=saas'ta kullanılır. SaaS_Platform/apps/SRM'deki kanıtlanmış
PortalSSOService deseninin birebir uyarlaması.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx
import jwt  # PyJWT — python-jose bırakıldı: GHSA-3qf3-8w2g-rqmx (kritik, düzeltmesi yok)

from app.core.config import get_settings

logger = logging.getLogger("operon_puantaj.portal_sso")

# Portal jetonunda bulunması ZORUNLU claim'ler — eksikse jeton reddedilir.
_ZORUNLU_CLAIMLER = ["exp", "iat", "aud", "iss", "sub"]


def _coz(token: str, public_key: str) -> Dict:
    settings = get_settings()
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],              # yalnız RS256: HS/none algoritma karışıklığı kapalı
        audience=settings.portal_app_slug,
        issuer=settings.portal_issuer,
        options={"require": _ZORUNLU_CLAIMLER},
        leeway=10,                         # portal ile saat kayması payı (sn)
    )


class PortalSSOService:
    _public_key_cache: Optional[str] = None
    _public_key_cache_time: Optional[datetime] = None
    CACHE_TTL_HOURS = 1

    @classmethod
    async def get_public_key(cls, force_refresh: bool = False) -> str:
        if not force_refresh and cls._public_key_cache and cls._public_key_cache_time:
            age = (datetime.now(timezone.utc) - cls._public_key_cache_time).total_seconds() / 3600
            if age < cls.CACHE_TTL_HOURS:
                return cls._public_key_cache

        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.portal_url}/api/.well-known/jwt-public-key.pem",
                timeout=10.0,
            )
            resp.raise_for_status()
            public_key = resp.json()["public_key"]

        cls._public_key_cache = public_key
        cls._public_key_cache_time = datetime.now(timezone.utc)
        logger.info("Portal public key fetched and cached")
        return public_key

    @classmethod
    async def validate_token(cls, token: str) -> Dict:
        try:
            public_key = await cls.get_public_key()
        except Exception as e:
            if cls._public_key_cache:
                logger.warning("Stale portal public key in use: %s", e)
                public_key = cls._public_key_cache
            else:
                raise ValueError(f"Portal public key alınamadı: {e}")

        try:
            payload = _coz(token, public_key)
        except jwt.InvalidSignatureError:
            # İmza tutmadı: portal anahtarı dönmüş olabilir — anahtarı bir kez tazeleyip yeniden dene.
            # (Süresi dolmuş / yanlış aud gibi claim hataları anahtar tazelemeyi tetiklemez.)
            logger.warning("Token imzası doğrulanamadı, portal public key yenileniyor...")
            try:
                public_key = await cls.get_public_key(force_refresh=True)
            except Exception as e:
                raise ValueError(f"Portal public key alınamadı: {e}")
            try:
                payload = _coz(token, public_key)
            except jwt.PyJWTError as e:
                raise ValueError(f"Geçersiz token: {e}")
            logger.info(
                "Token OK (yenilenen key ile) — user=%s tenant=%s",
                payload.get("username"),
                payload.get("tenant_slug"),
            )
            return payload
        except jwt.PyJWTError as e:
            # Mesaja jetonun kendisi yazılmaz — log'a/yanıta sır sızmaz.
            raise ValueError(f"Geçersiz token: {e}")

        logger.info(
            "Token OK — user=%s tenant=%s",
            payload.get("username"),
            payload.get("tenant_slug"),
        )
        return payload
