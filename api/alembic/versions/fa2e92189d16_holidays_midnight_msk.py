"""holidays_midnight_msk

Revision ID: fa2e92189d16
Revises: 90b9a81e6f1d
Create Date: 2026-10-21 16:11:14.531478

Праздники всегда начинаются в 00:00:00 и заканчиваются в 23:59:59
(МСК). Существующие строки приводятся к тем же датам с фиксированным
временем; дни сетки карточек не меняются (дни считаются по датам).
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'fa2e92189d16'
down_revision: Union[str, None] = '90b9a81e6f1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE holidays SET starts_at = substr(starts_at, 1, 10) || ' 00:00:00'")
    op.execute("UPDATE holidays SET ends_at = substr(ends_at, 1, 10) || ' 23:59:59'")


def downgrade() -> None:
    pass
