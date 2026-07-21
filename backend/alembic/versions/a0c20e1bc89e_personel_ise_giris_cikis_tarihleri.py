"""personel ise giris cikis tarihleri

Revision ID: a0c20e1bc89e
Revises: 4a9b8ebeb4ae
Create Date: 2026-07-04 03:10:00.000000

Kullanıcı geri bildirimi (2026-07-04): "giriş çıkışlar çok olur, değişiklik
yapılan gün itibarı ile geçerli olmalı, işten çıkan o ay sonuna dek listede
kalmalı". Elle işaretlenen `aktif: bool` yerine gerçek işe giriş/çıkış
tarihleri — `aktif` artık modelde bu tarihlerden türetilen bir property
(DB sütunu değil). Mevcut aktif=false kayıtlar için bilinen bir çıkış
tarihi olmadığından bugüne set edilir (elle düzeltilebilir); aktif=true
kayıtlar None kalır (hâlâ çalışıyor).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0c20e1bc89e'
down_revision: Union[str, None] = '4a9b8ebeb4ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('personel', sa.Column('ise_baslama_tarihi', sa.Date(), nullable=True))
    op.add_column('personel', sa.Column('isten_cikis_tarihi', sa.Date(), nullable=True))
    op.execute("UPDATE personel SET isten_cikis_tarihi = CURRENT_DATE WHERE aktif = false")
    op.drop_column('personel', 'aktif')


def downgrade() -> None:
    op.add_column('personel', sa.Column('aktif', sa.BOOLEAN(), server_default=sa.true(), nullable=False))
    op.execute("UPDATE personel SET aktif = false WHERE isten_cikis_tarihi IS NOT NULL")
    op.drop_column('personel', 'isten_cikis_tarihi')
    op.drop_column('personel', 'ise_baslama_tarihi')
