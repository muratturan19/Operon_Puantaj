# -*- coding: utf-8 -*-
"""core/zaman.py — DB'ye yazılan "şimdi" değerinin tek kaynağı.

sqlmodel 0.0.47+ saat dilimsiz datetime'ı yazarken reddeder ('Datetime values must have
timezone information'). Saat dilimsiz "utc now" bu yüzden kullanılmaz: 24 Ekim 2026 bakımında
imaj yeniden derlenince SSO girişi her seferinde 500 verdi (2026-10-26).
Sütunlar `timestamp without time zone`; DB oturumu UTC olduğundan değer aynı saatle saklanır.
"""
from datetime import datetime, timezone


def simdi_utc() -> datetime:
    return datetime.now(timezone.utc)
