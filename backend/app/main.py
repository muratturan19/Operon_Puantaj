# -*- coding: utf-8 -*-
"""app/main.py — Operon Puantaj FastAPI uygulaması."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.api.routes import (
    audit,
    auth,
    calisma_tipleri,
    donemler,
    excel,
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

settings = get_settings()

app = FastAPI(title="Operon Puantaj", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
        # `full_path` istemciden gelir — ".."/simge bağlantı ile _static dışına
        # çıkılabilir olmasın diye resolve() sonrası _static_resolved altında
        # kaldığı DOĞRULANMADAN dosya servis edilmez (path traversal, CWE-22).
        candidate = (_static / full_path).resolve()
        if full_path and candidate.is_relative_to(_static_resolved) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
