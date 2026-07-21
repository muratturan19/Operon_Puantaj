# -*- coding: utf-8 -*-
"""
core/permissions.py — Bilinen izin anahtarları + seed rollerin varsayılan izin sözlükleri.

Bu bir enum DEĞİL, sadece route'lar ve seed migration'ın aynı string'leri
kullanmasını sağlayan bir referans. `Rol.izinler` şemada serbest JSON kalır —
yeni bir izin anahtarı eklemek migration gerektirmez, sadece burayı ve ilgili
route'un `require_permission(...)` çağrısını günceller.

Rol üçlüsü (CLAUDE.md §8.7 — Kurulum Sihirbazı kararı, 2026-07-04):
  - admin     — tam yetki (eski `ik_yoneticisi`)
  - kullanici — sadece puantaj girer; maaş görünürlüğü wizard'da Admin'in
                seçtiği bir anahtar (varsayılan GİZLİ) — eski `ik_personeli`
  - gm        — tam görünürlük (maaş dahil) + export, SIFIR yazma yetkisi
                (eski `gm`'den semantik olarak FARKLI — önceden tam yetkiliydi)
"""
from __future__ import annotations

PUANTAJ_GIREBILIR = "puantaj_girebilir"
PUANTAJ_GOREBILIR = "puantaj_gorebilir"
GOREBILIR_MAAS_TUTARI = "gorebilir_maas_tutari"
PERSONEL_YONETEBILIR = "personel_yonetebilir"
CALISMA_TIPI_YONETEBILIR = "calisma_tipi_yonetebilir"
KULLANICI_YONETEBILIR = "kullanici_yonetebilir"
TATIL_YONETEBILIR = "tatil_yonetebilir"
EXCEL_ICE_AKTARABILIR = "excel_ice_aktarabilir"
EXCEL_DISA_AKTARABILIR = "excel_disa_aktarabilir"
DONEM_TEMIZLEYEBILIR = "donem_temizleyebilir"
AUDIT_GOREBILIR = "audit_gorebilir"
SIRKET_AYARLARINI_YONETEBILIR = "sirket_ayarlarini_yonetebilir"

# Kurulum sihirbazının "Kullanıcı rolü maaş görebilsin mi?" sorusuna varsayılan yanıt.
KULLANICI_MAAS_VARSAYILAN = False

SEED_ROL_IZINLERI: dict[str, dict[str, bool]] = {
    "admin": {
        PUANTAJ_GIREBILIR: True,
        PUANTAJ_GOREBILIR: True,
        GOREBILIR_MAAS_TUTARI: True,
        PERSONEL_YONETEBILIR: True,
        CALISMA_TIPI_YONETEBILIR: True,
        KULLANICI_YONETEBILIR: True,
        TATIL_YONETEBILIR: True,
        EXCEL_ICE_AKTARABILIR: True,
        EXCEL_DISA_AKTARABILIR: True,
        DONEM_TEMIZLEYEBILIR: True,
        AUDIT_GOREBILIR: True,
        SIRKET_AYARLARINI_YONETEBILIR: True,
    },
    "kullanici": {
        PUANTAJ_GIREBILIR: True,
        PUANTAJ_GOREBILIR: True,
        GOREBILIR_MAAS_TUTARI: KULLANICI_MAAS_VARSAYILAN,  # wizard'da Admin değiştirebilir
        PERSONEL_YONETEBILIR: False,
        CALISMA_TIPI_YONETEBILIR: False,
        KULLANICI_YONETEBILIR: False,
        TATIL_YONETEBILIR: False,
        EXCEL_ICE_AKTARABILIR: False,
        EXCEL_DISA_AKTARABILIR: False,
        DONEM_TEMIZLEYEBILIR: False,
        AUDIT_GOREBILIR: False,
        SIRKET_AYARLARINI_YONETEBILIR: False,
    },
    "gm": {
        # Tam görünürlük, sıfır yazma — export "yazma" sayılmaz (kendi verimizi değiştirmiyor).
        PUANTAJ_GIREBILIR: False,
        PUANTAJ_GOREBILIR: True,
        GOREBILIR_MAAS_TUTARI: True,
        PERSONEL_YONETEBILIR: False,
        CALISMA_TIPI_YONETEBILIR: False,
        KULLANICI_YONETEBILIR: False,
        TATIL_YONETEBILIR: False,
        EXCEL_ICE_AKTARABILIR: False,
        EXCEL_DISA_AKTARABILIR: True,
        DONEM_TEMIZLEYEBILIR: False,
        AUDIT_GOREBILIR: True,
        SIRKET_AYARLARINI_YONETEBILIR: False,
    },
}

ROL_DISPLAY_ADLARI: dict[str, str] = {
    "admin": "Admin",
    "kullanici": "Kullanıcı",
    "gm": "GM",
}
