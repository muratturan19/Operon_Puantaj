# -*- coding: utf-8 -*-
"""app/main.py — Operon Puantaj FastAPI uygulaması."""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    audit,
    auth,
    calisma_tipleri,
    donemler,
    excel,
    hatalar,
    kullanicilar,
    personel,
    puantaj,
    roller,
    setup,
    sirket,
    sso,
    tatiller,
)
from app.core.config import get_settings
from app.core.logging_setup import yapilandir as log_yapilandir
from app.core.version import SURUM, SURUM_ADI, SURUM_TARIHI
from app.services.hata_kaydi import kaydet as hata_kaydet, yeni_istek_id

settings = get_settings()
logger = log_yapilandir()

app = FastAPI(title="Operon Puantaj", version=SURUM)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Export uyarı başlığı tarayıcıdan okunabilsin (dev'de ayrı origin)
    expose_headers=["X-Puantaj-Uyari"],
)


async def _tenant_bilgisi(request: Request) -> tuple[str | None, str | None]:
    """Hata kaydı için JWT'den (tenant_slug, username). Doğrulanamazsa (None, None)."""
    token = request.cookies.get("access_token")
    if not token:
        return None, None
    try:
        from app.services.portal_sso_service import PortalSSOService

        claims = await PortalSSOService.validate_token(token)
        return claims.get("tenant_slug"), claims.get("username")
    except Exception:  # noqa: BLE001 — hata yolunda ikinci istisna üretme
        return None, None


@app.middleware("http")
async def _istek_logu(request: Request, call_next):
    """Kendi erişim logumuz.

    uvicorn'un `access` logger'ına güvenilmiyor: 2026-07/08'de alembic'in
    fileConfig'i onu susurmuş ve 6 hafta boyunca hiçbir istek kaydı kalmamıştı.
    Bu middleware "operon_puantaj" logger'ına yazar (bkz. core/logging_setup.py),
    yani o sınıf hatalardan etkilenmez.
    """
    baslangic = time.perf_counter()
    yanit = await call_next(request)
    sure_ms = (time.perf_counter() - baslangic) * 1000
    if request.url.path not in ("/health", "/api/health"):
        logger.info(
            "%s %s%s -> %s (%.0f ms)",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            yanit.status_code,
            sure_ms,
        )
    return yanit


@app.exception_handler(Exception)
async def _yakalanmamis_hata(request: Request, exc: Exception) -> JSONResponse:
    """Yakalanmamış her hata: log + tenant DB'sinde kalıcı kayıt + takip kodu.

    Kullanıcıya teknik ayrıntı DÖNÜLMEZ, yalnızca `istek_id` gösterilir —
    müşteri o kodu söylediğinde kayıt Güvenlik ekranından tek sorguyla bulunur.
    """
    istek_id = yeni_istek_id()
    tenant_slug, kullanici = await _tenant_bilgisi(request)
    hata_kaydet(
        istek_id=istek_id,
        exc=exc,
        yol=request.url.path,
        metod=request.method,
        sorgu=request.url.query or None,
        kullanici=kullanici,
        tenant_slug=tenant_slug,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Beklenmeyen bir hata oluştu. Destek ekibine bu kodu iletin.",
            "istek_id": istek_id,
        },
    )


app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(sso.router)
app.include_router(roller.router)
app.include_router(kullanicilar.router)
app.include_router(calisma_tipleri.router)
app.include_router(personel.router)
app.include_router(sirket.router)
app.include_router(donemler.router)
app.include_router(tatiller.router)
app.include_router(puantaj.router)
app.include_router(excel.router)
app.include_router(audit.router)
app.include_router(hatalar.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "surum": SURUM}


@app.get("/api/surum")
def surum() -> dict:
    """Sunucuda çalışan sürüm — kimlik doğrulaması gerektirmez.

    Dışarıdan tek istekle "canlıdaki sürüm hangisi" sorusunu yanıtlar; arayüz de
    kendi gömülü sürümüyle karşılaştırıp eski bir sekmede açık kalmış kullanıcıyı
    uyarmak için kullanır.
    """
    return {"surum": SURUM, "tarih": SURUM_TARIHI, "ad": SURUM_ADI}


@app.get("/api/health")
def api_health() -> dict:
    """Traefik/izleme bu yolu çağırıyor.

    Bug (2026-08-25): tanımlı değildi ve aşağıdaki SPA catch-all'a düşüp
    **200 + index.html** dönüyordu — yani sağlık kontrolü uygulama tamamen
    bozuk olsa bile yeşil kalıyordu.
    """
    return {"status": "ok", "surum": SURUM}


def _find_frontend_static() -> Path | None:
    """Docker: /frontend/dist  |  Dev: bulunamazsa None (Vite ayrı çalışır)."""
    override = os.getenv("FRONTEND_DIST_DIR")
    if override:
        p = Path(override)
        return p if p.is_dir() else None
    p = Path("/frontend/dist")
    if p.is_dir():
        return p
    p = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    return p if p.is_dir() else None


_static = _find_frontend_static()
if _static is not None:
    _static_resolved = _static.resolve()
    _assets_dir = _static / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def _spa_catch_all(full_path: str, request: Request):
        # Bug (2026-08-25): tanımsız `/api/...` yolları da buraya düşüyor ve
        # **200 + HTML** dönüyordu. Frontend JSON beklerken HTML alıyor, hata
        # "anlamsız ekran" olarak yansıyor ve sunucuda hiçbir iz kalmıyordu.
        # API yolları artık dürüst bir 404 JSON döner.
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Bulunamadı"})

        # `full_path` istemciden gelir — ".."/simge bağlantı ile _static dışına
        # çıkılabilir olmasın diye resolve() sonrası _static_resolved altında
        # kaldığı DOĞRULANMADAN dosya servis edilmez (path traversal, CWE-22).
        candidate = (_static / full_path).resolve()
        if full_path and candidate.is_relative_to(_static_resolved) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
