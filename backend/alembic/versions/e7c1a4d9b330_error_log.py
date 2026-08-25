# -*- coding: utf-8 -*-
"""error_log tablosu — yakalanmamış sunucu hatalarının kalıcı kaydı

Revision ID: e7c1a4d9b330
Revises: b3a7d1e9f204
Create Date: 2026-08-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c1a4d9b330"
down_revision: Union[str, None] = "b3a7d1e9f204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "error_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("istek_id", sa.String(), nullable=False),
        sa.Column("zaman", sa.DateTime(), nullable=False),
        sa.Column("yol", sa.String(), nullable=False),
        sa.Column("metod", sa.String(), nullable=False),
        sa.Column("sorgu", sa.String(), nullable=True),
        sa.Column("kullanici", sa.String(), nullable=True),
        sa.Column("sirket_id", sa.Integer(), nullable=True),
        sa.Column("hata_tipi", sa.String(), nullable=False),
        sa.Column("mesaj", sa.String(), nullable=False),
        sa.Column("traceback_metni", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_error_log_istek_id"), "error_log", ["istek_id"])
    op.create_index(op.f("ix_error_log_zaman"), "error_log", ["zaman"])


def downgrade() -> None:
    op.drop_index(op.f("ix_error_log_zaman"), table_name="error_log")
    op.drop_index(op.f("ix_error_log_istek_id"), table_name="error_log")
    op.drop_table("error_log")
