"""hafta tatili gunleri + resmi tatil fm orani

Revision ID: 51e979ff9e3e
Revises: d94e6b3c7a12
Create Date: 2026-07-05 03:10:00.000000

Kullanıcı geri bildirimi (2026-07-05): "hafta tatili günü" kodda HER ZAMAN Pazar
olarak sabitti (payroll_calc.py::fm_orani, tarih.weekday()==6) — CalismaTipi.
haftalik_gun alanı vardı ama hesap motorunda hiç kullanılmıyordu. 5 gün çalışan
bir tip (ör. Beyaz Yaka, Cumartesi de tatil) için bu YANLIŞ (düşük) FM oranı
uygulanmasına yol açıyordu. Ayrıca resmi tatil ile hafta tatili tek bir orana
(hafta_sonu_fm_orani) sıkışmıştı; toplu iş sözleşmeleri bunları farklı oranlarla
ele alabiliyor (internet araştırması, 2026-07-05).

DÜZELTME (2026-07-05, gerçek müşteri geri bildirimi): İlk sürümde haftalik_gun=5 için
hafta_tatili_gunleri=[5,6] (Cmt+Paz) varsayılmıştı — YANLIŞ çıktı. Gerçek pratik: 5 gün
çalışan Beyaz Yaka için Cumartesi sadece normal bir çalışılmayan gün, "hafta tatili"
(primli, ×2) değil — Cumartesi mesaisi hafta içi oranıyla (×1,5) ödenmeli. Tek hafta
tatili günü (×2) her durumda Pazar. Artık haftalik_gun'dan BAĞIMSIZ olarak her zaman
yalnızca Pazar ([6]) varsayılıyor; şirket isterse Çalışma Tipleri sayfasından Cumartesi'yi
de ekleyebilir (checkbox tamamen kullanıcı kontrolünde, bu sadece varsayılan öneri).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '51e979ff9e3e'
down_revision: Union[str, None] = 'd94e6b3c7a12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('calisma_tipi', sa.Column('resmi_tatil_fm_orani', sa.Float(), nullable=True))
    op.add_column('calisma_tipi', sa.Column('hafta_tatili_gunleri', sa.JSON(), nullable=True))

    conn = op.get_bind()
    # Backfill: resmi_tatil_fm_orani = mevcut hafta_sonu_fm_orani (davranış değişmez)
    conn.execute(sa.text("UPDATE calisma_tipi SET resmi_tatil_fm_orani = hafta_sonu_fm_orani"))
    # Backfill: haftalik_gun'dan bağımsız her zaman [Paz] — tek hafta tatili günü
    # varsayılan olarak Pazar (kullanıcı isterse Çalışma Tipleri'nden değiştirir).
    conn.execute(sa.text("UPDATE calisma_tipi SET hafta_tatili_gunleri = '[6]'::json"))

    op.alter_column('calisma_tipi', 'resmi_tatil_fm_orani', nullable=False, server_default='2.0')
    op.alter_column('calisma_tipi', 'hafta_tatili_gunleri', nullable=False, server_default='[6]')


def downgrade() -> None:
    op.drop_column('calisma_tipi', 'hafta_tatili_gunleri')
    op.drop_column('calisma_tipi', 'resmi_tatil_fm_orani')
