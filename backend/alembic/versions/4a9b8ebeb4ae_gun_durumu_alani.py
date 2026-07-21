"""gun durumu alani

Revision ID: 4a9b8ebeb4ae
Revises: 81f9c9647f37
Create Date: 2026-07-04 01:57:02.830187

Kullanıcı geri bildirimi (2026-07-04): Yıllık İzin ve Raporlu için tam-gün
statüsü eklendi. `tam_gun_devamsizlik: bool` yerine `gun_durumu: str | None`
(None | "devamsiz" | "yillik_izin" | "raporlu") — mevcut True/False verisi
kaybolmadan dönüştürülüyor.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4a9b8ebeb4ae'
down_revision: Union[str, None] = '81f9c9647f37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('puantaj_girisi', sa.Column('gun_durumu', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute("UPDATE puantaj_girisi SET gun_durumu = 'devamsiz' WHERE tam_gun_devamsizlik = true")
    op.drop_column('puantaj_girisi', 'tam_gun_devamsizlik')


def downgrade() -> None:
    op.add_column('puantaj_girisi', sa.Column('tam_gun_devamsizlik', sa.BOOLEAN(), server_default=sa.false(), nullable=False))
    op.execute("UPDATE puantaj_girisi SET tam_gun_devamsizlik = true WHERE gun_durumu = 'devamsiz'")
    op.drop_column('puantaj_girisi', 'gun_durumu')
