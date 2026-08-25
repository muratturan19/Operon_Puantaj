"""personel maas gecmisi

Revision ID: b3a7d1e9f204
Revises: f6bf158e25e4
Create Date: 2026-07-06 12:00:00.000000

Kullanıcı sorusu (2026-07-06): "maaşlara zam gelince onu sisteme nasıl alacağız?"
`Personel.maas` tek bir güncel değerdi, geçmiş tutmuyordu — geçmiş dönemler için
`ozet()`/export her zaman bugünkü maaşı okuyordu. Bu tablo, N.G'deki
`PersonelDonemAyar` desenine benzer ama etkin-tarihli (carry-forward) semantiğe
sahip: bir kayıt, girildiği (yıl,ay)'dan itibaren bir sonraki kayda kadar geçerli.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a7d1e9f204'
down_revision: Union[str, None] = 'f6bf158e25e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'personel_maas_gecmisi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('personel_id', sa.Integer(), nullable=False),
        sa.Column('yil', sa.Integer(), nullable=False),
        sa.Column('ay', sa.Integer(), nullable=False),
        sa.Column('maas', sa.Float(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['personel_id'], ['personel.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['kullanici.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('personel_id', 'yil', 'ay', name='uq_personel_maas_gecmisi'),
    )


def downgrade() -> None:
    op.drop_table('personel_maas_gecmisi')
