"""calisma tipi fm oranlari

Revision ID: d94e6b3c7a12
Revises: c3f7a2e91d05
Create Date: 2026-07-04 05:00:00.000000

Kullanıcı kararı (2026-07-04): "FM oran kısmı parametrelerin ayarlandığı
sayfadan ayarlanmalı" — FM (fazla mesai) çarpanları artık Çalışma Tipi
bazında ayarlanabilir. Varsayılanlar (1,5×/2×) mevcut sabit davranışla
birebir aynı, geriye dönük uyumlu.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd94e6b3c7a12'
down_revision: Union[str, None] = 'c3f7a2e91d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'calisma_tipi',
        sa.Column('hafta_ici_fm_orani', sa.Float(), nullable=False, server_default='1.5'),
    )
    op.add_column(
        'calisma_tipi',
        sa.Column('hafta_sonu_fm_orani', sa.Float(), nullable=False, server_default='2.0'),
    )


def downgrade() -> None:
    op.drop_column('calisma_tipi', 'hafta_sonu_fm_orani')
    op.drop_column('calisma_tipi', 'hafta_ici_fm_orani')
