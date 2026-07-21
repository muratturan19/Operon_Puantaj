# -*- coding: utf-8 -*-
"""run.py — Geliştirme sunucusu başlatıcı. Windows + UTF-8 uyumlu."""
import sys

import uvicorn

from app.core.config import get_settings

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.api_port, reload=True)
