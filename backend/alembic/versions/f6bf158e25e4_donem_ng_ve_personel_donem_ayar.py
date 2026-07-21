"""donem.ng + personel_donem_ayar

Revision ID: f6bf158e25e4
Revises: 51e979ff9e3e
Create Date: 2026-07-06 12:00:00.000000

Kullanıcı geri bildirimi (2026-07-06): "kişi bazında Ç.G değişmiyor, ay ay komple
değişebiliyor ama aynı ay içinde biri 30 biri 31 olmuyor." Önceden N.G
(`Personel.ng`) kişi bazında sabitti ve her ay aynı değer kullanılıyordu — ay
değiştiğinde (ör. Haziran 30 gün → Temmuz 31 gün) otomatik güncellenmiyordu.

Artık `Donem.ng` dönemin varsayılan N.G'sidir (takvim gün sayısı), kişi bazlı
istisnalar (kullanıcı: "kişi bazında elle değiştirilebilsin") yeni
`personel_donem_ayar` tablosunda SADECE ilgili dönem için saklanır.
`Personel.ng` alanı KALDIRILMADI — artık hesaplamada kullanılmıyor, yalnızca
Excel import / yeni personel formundaki referans/başlangıç değeri olarak kalıyor.

Backfill: mevcut tüm Donem satırları için `ng = calendar.monthrange(yil, ay)[1]`
— ör. Haziran 2026 zaten 30 gün olduğu için bu backfill sonrası hiçbir mevcut
hesap SESSİZCE değişmez (regresyon yok, elle doğrulandı).
"""
import calendar
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6bf158e25e4'
down_revision: Union[str, None] = '51e979ff9e3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('donem', sa.Column('ng', sa.Integer(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, yil, ay FROM donem")).fetchall()
    for donem_id, yil, ay in rows:
        gun_sayisi = calendar.monthrange(yil, ay)[1]
        conn.execute(
            sa.text("UPDATE donem SET ng = :ng WHERE id = :id"),
            {"ng": gun_sayisi, "id": donem_id},
        )

    op.alter_column('donem', 'ng', nullable=False, server_default='30')

    op.create_table(
        'personel_donem_ayar',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('personel_id', sa.Integer(), sa.ForeignKey('personel.id'), nullable=False),
        sa.Column('donem_id', sa.Integer(), sa.ForeignKey('donem.id'), nullable=False),
        sa.Column('ng', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('personel_id', 'donem_id', name='uq_personel_donem_ayar'),
    )


def downgrade() -> None:
    op.drop_table('personel_donem_ayar')
    op.drop_column('donem', 'ng')
