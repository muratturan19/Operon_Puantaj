"""sirket raporlu politikasi

Revision ID: c3f7a2e91d05
Revises: a0c20e1bc89e
Create Date: 2026-07-04 04:00:00.000000

Kullanıcı kararı (2026-07-04): Raporlu'nun maaş etkisi (tam öde / hiç ödeme /
ilk N gün ödenir) çalışan tipinden bağımsız, şirket genelinde tek bir ayar.
Varsayılan `hic_odeme` + `esik_gun=0` — mevcut davranışla birebir aynı,
geriye dönük uyumlu (mevcut şirket satırları için hiçbir hesap değişmez).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f7a2e91d05'
down_revision: Union[str, None] = 'a0c20e1bc89e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sirket',
        sa.Column('raporlu_politikasi', sa.String(), nullable=False, server_default='hic_odeme'),
    )
    op.add_column(
        'sirket',
        sa.Column('raporlu_esik_gun', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('sirket', 'raporlu_esik_gun')
    op.drop_column('sirket', 'raporlu_politikasi')
