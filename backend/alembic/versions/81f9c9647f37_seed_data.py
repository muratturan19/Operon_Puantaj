"""seed data

Revision ID: 81f9c9647f37
Revises: 72502d78fbea
Create Date: 2026-07-03 23:58:08.763789

Bootstrap: tek Şirket satırı + seed roller (admin/kullanici/gm,
izinler app.core.permissions.SEED_ROL_IZINLERI'den — CLAUDE.md §8.7 Kurulum
Sihirbazı kararı) + seed ÇalışanTipi (BY 8x5, MY 7.5x6 — CLAUDE.md §7) +
2026 TR resmi tatilleri (Puantaj_Brief §5).

Şirket adı ve ilk Admin kullanıcısı BURADA oluşturulmuyor — kurulum sihirbazı
(`POST /api/setup/complete`) oluşturuyor. Bu migration sadece rol/tip/tatil
gibi yapısal varsayılanları hazırlar.
"""
import json
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from app.core.permissions import ROL_DISPLAY_ADLARI, SEED_ROL_IZINLERI

# revision identifiers, used by Alembic.
revision: str = '81f9c9647f37'
down_revision: Union[str, None] = '72502d78fbea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VARSAYILAN_TATIL_2026 = [
    "2026-01-01", "2026-03-20", "2026-03-21", "2026-03-22", "2026-04-23",
    "2026-05-01", "2026-05-19", "2026-05-27", "2026-05-28", "2026-05-29", "2026-05-30",
    "2026-07-15", "2026-08-30", "2026-10-29",
]

SIRKET_ADI = "Kurulum Bekleniyor"  # kurulum sihirbazı Sirket.ad'ı gerçek adla günceller


def upgrade() -> None:
    conn = op.get_bind()

    sirket_id = conn.execute(
        sa.text("INSERT INTO sirket (ad, created_at) VALUES (:ad, now()) RETURNING id"),
        {"ad": SIRKET_ADI},
    ).scalar_one()

    for kod, izinler in SEED_ROL_IZINLERI.items():
        ad = ROL_DISPLAY_ADLARI[kod]
        conn.execute(
            sa.text(
                "INSERT INTO rol (sirket_id, kod, ad, izinler, sistem_varsayilani, created_at) "
                "VALUES (:sirket_id, :kod, :ad, :izinler, true, now())"
            ),
            {"sirket_id": sirket_id, "kod": kod, "ad": ad, "izinler": json.dumps(izinler)},
        )

    for kod, ad, gunluk_saat, haftalik_gun in [
        ("BY", "Beyaz Yaka", 8.0, 5),
        ("MY", "Mavi Yaka", 7.5, 6),
    ]:
        conn.execute(
            sa.text(
                "INSERT INTO calisma_tipi (sirket_id, kod, ad, gunluk_saat, haftalik_gun, aktif, created_at) "
                "VALUES (:sirket_id, :kod, :ad, :gunluk_saat, :haftalik_gun, true, now())"
            ),
            {
                "sirket_id": sirket_id, "kod": kod, "ad": ad,
                "gunluk_saat": gunluk_saat, "haftalik_gun": haftalik_gun,
            },
        )

    for tarih_str in VARSAYILAN_TATIL_2026:
        conn.execute(
            sa.text(
                "INSERT INTO tatil (sirket_id, tarih, kaynak) "
                "VALUES (:sirket_id, :tarih, 'sistem_varsayilan')"
            ),
            {"sirket_id": sirket_id, "tarih": date.fromisoformat(tarih_str)},
        )


def downgrade() -> None:
    conn = op.get_bind()
    # Sirket.ad kurulum sihirbazında değişmiş olabilir — isme göre değil, tekil kayda göre bul.
    sirket_id = conn.execute(sa.text("SELECT id FROM sirket LIMIT 1")).scalar_one_or_none()
    if sirket_id is None:
        return
    conn.execute(sa.text("DELETE FROM tatil WHERE sirket_id = :id"), {"id": sirket_id})
    conn.execute(sa.text("DELETE FROM calisma_tipi WHERE sirket_id = :id"), {"id": sirket_id})
    conn.execute(sa.text("DELETE FROM rol WHERE sirket_id = :id"), {"id": sirket_id})
    conn.execute(sa.text("DELETE FROM sirket WHERE id = :id"), {"id": sirket_id})
