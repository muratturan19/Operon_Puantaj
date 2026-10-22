# -*- coding: utf-8 -*-
"""tests/test_portal_sso_jwt.py — JWT doğrulaması, gerçek jetonlarla (python-jose → PyJWT geçişi).

Portal SSO (RS256): geçerli jeton geçer; aud/iss/exp/eksik claim/yabancı anahtar/
açık anahtarla HS256 sahtesi/alg=none reddedilir.
Kendi (on-prem) jetonumuz: üret → doğrula turu, `sub` string olarak taşınır ve int id'ye döner.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import security
from app.core.config import get_settings
from app.services.portal_sso_service import PortalSSOService

_ANAHTAR = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_ACIK = _ANAHTAR.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()


@pytest.fixture(autouse=True)
def _acik_anahtar(monkeypatch):
    async def sabit(cls, force_refresh: bool = False):
        return _ACIK

    monkeypatch.setattr(PortalSSOService, "get_public_key", classmethod(sabit))
    yield
    PortalSSOService._public_key_cache = None
    PortalSSOService._public_key_cache_time = None


def _claim(**degis):
    settings = get_settings()
    simdi = datetime.now(timezone.utc)
    c = {
        "iss": settings.portal_issuer,
        "sub": "16",
        "aud": settings.portal_app_slug,
        "exp": int((simdi + timedelta(hours=2)).timestamp()),
        "iat": int(simdi.timestamp()),
        "tenant_slug": "testa",
        "username": "testa",
        "role": "admin",
    }
    c.update(degis)
    return {k: v for k, v in c.items() if v is not None}


def _dogrula(tok: str) -> dict:
    return asyncio.run(PortalSSOService.validate_token(tok))


def _b64(v) -> str:
    ham = v if isinstance(v, bytes) else json.dumps(v).encode()
    return base64.urlsafe_b64encode(ham).rstrip(b"=").decode()


# ── Portal SSO (RS256) ────────────────────────────────────────────────────────

def test_gecerli_portal_jetonu_gecer():
    p = _dogrula(jwt.encode(_claim(), _ANAHTAR, algorithm="RS256"))
    assert p["sub"] == "16" and p["tenant_slug"] == "testa"


@pytest.mark.parametrize(
    "degis",
    [
        {"aud": "baska-uygulama"},
        {"iss": "https://kotu.example"},
        {"exp": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp())},
        {"sub": None},  # zorunlu claim eksik
        {"aud": None},
        {"iat": None},
    ],
)
def test_claim_ihlali_reddedilir(degis):
    with pytest.raises(ValueError):
        _dogrula(jwt.encode(_claim(**degis), _ANAHTAR, algorithm="RS256"))


def test_baska_anahtarla_imzali_reddedilir():
    baska = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(ValueError):
        _dogrula(jwt.encode(_claim(), baska, algorithm="RS256"))


def test_acik_anahtarla_hs256_sahtesi_reddedilir():
    """Algoritma karışıklığı: açık anahtarı HMAC sırrı gibi kullanan HS256 jetonu."""
    govde = f"{_b64({'alg': 'HS256', 'typ': 'JWT'})}.{_b64(_claim())}"
    imza = hmac.new(_ACIK.encode(), govde.encode(), hashlib.sha256).digest()
    with pytest.raises(ValueError):
        _dogrula(f"{govde}.{_b64(imza)}")


def test_alg_none_reddedilir():
    with pytest.raises(ValueError):
        _dogrula(f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(_claim())}.")


# ── Kendi on-prem jetonumuz (HS) ──────────────────────────────────────────────

class _FakeSession:
    def __init__(self, kullanici):
        self._k = kullanici
        self.istenen = None

    def get(self, model, pk):
        self.istenen = pk
        return self._k if pk == self._k.id else None


def _kullanici():
    return SimpleNamespace(id=12, kullanici_adi="emine", sirket_id=1, aktif=True)


def test_kendi_jetonu_tur_atar_sub_string():
    k = _kullanici()
    tok = security.create_access_token(k)
    settings = get_settings()
    ham = jwt.decode(tok, settings.secret_key, algorithms=[settings.jwt_algorithm])
    assert ham["sub"] == "12" and isinstance(ham["sub"], str)

    oturum = _FakeSession(k)
    assert security.get_current_user_onprem(token=tok, session=oturum) is k
    assert oturum.istenen == 12  # string sub, int birincil anahtara geri çevrildi


@pytest.mark.parametrize(
    "jeton",
    [
        # sub int — PyJWT >=2.10 reddeder (bizim jetonlarımız hep string sub taşır)
        lambda s: jwt.encode({"sub": 12, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                             s.secret_key, algorithm="HS256"),
        # süresi dolmuş
        lambda s: jwt.encode({"sub": "12", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
                             s.secret_key, algorithm="HS256"),
        # exp yok
        lambda s: jwt.encode({"sub": "12"}, s.secret_key, algorithm="HS256"),
        # sayısal olmayan sub
        lambda s: jwt.encode({"sub": "abc", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                             s.secret_key, algorithm="HS256"),
        # yanlış sır
        lambda s: jwt.encode({"sub": "12", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                             "baska-bir-sir-en-az-otuz-iki-bayt-uzunlugunda", algorithm="HS256"),
        # alg none
        lambda s: f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': '12', 'exp': 9999999999})}.",
    ],
)
def test_kendi_jetonu_gecersizse_401(jeton):
    tok = jeton(get_settings())
    with pytest.raises(HTTPException) as e:
        security.get_current_user_onprem(token=tok, session=_FakeSession(_kullanici()))
    assert e.value.status_code == 401
