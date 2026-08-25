# -*- coding: utf-8 -*-
"""
core/logging_setup.py — Uygulama logger'ının kendi handler'ı.

Neden ayrı handler ve `propagate=False`: `alembic/env.py` içindeki `fileConfig`
her tenant migration'ında ROOT logger'ı alembic.ini'ye göre yeniden kurar
(level=WARNING, stderr handler). Root'a yaslanan bir yapılandırma (ör.
`logging.basicConfig`) ilk tenant girişinde sessizce ezilir — 2026-07/08'de
6 hafta boyunca hiç log üretilememesinin ikinci yarısı buydu. "operon_puantaj"
logger'ı kendi handler'ını taşır ve root'a yayılmaz; fileConfig onu
`disable_existing_loggers=False` sayesinde artık ne kapatır ne de yeniden
yapılandırır.
"""
from __future__ import annotations

import logging
import sys

KOK_AD = "operon_puantaj"
_BICIM = "%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s"


def yapilandir(seviye: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(KOK_AD)
    logger.setLevel(seviye)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_BICIM))
        logger.addHandler(handler)
    return logger
