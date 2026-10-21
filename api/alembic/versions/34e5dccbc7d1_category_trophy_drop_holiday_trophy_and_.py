"""category_trophy_drop_holiday_trophy_and_is_trophy

Revision ID: 34e5dccbc7d1
Revises: fa2e92189d16
Create Date: 2026-10-21 16:55:42.611490

Кубок переезжает с праздника на категорию («кубок категории»):
holidays.trophy_image_url удаляется, появляется
holiday_categories.trophy_image_url. Концепция «кубковой карточки»
ликвидируется: карточки с is_trophy=1 и их следы в user_cards/tasks
удаляются, колонка holiday_cards.is_trophy убирается.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '34e5dccbc7d1'
down_revision: Union[str, None] = 'fa2e92189d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM user_cards WHERE card_id IN (SELECT id FROM holiday_cards WHERE is_trophy = 1)")
    op.execute("DELETE FROM tasks WHERE card_id IN (SELECT id FROM holiday_cards WHERE is_trophy = 1)")
    op.execute("DELETE FROM holiday_cards WHERE is_trophy = 1")

    with op.batch_alter_table('holiday_categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trophy_image_url', sa.String(), nullable=True))

    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.drop_column('trophy_image_url')

    with op.batch_alter_table('holiday_cards', schema=None) as batch_op:
        batch_op.drop_column('is_trophy')


def downgrade() -> None:
    with op.batch_alter_table('holiday_cards', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_trophy', sa.Boolean(), nullable=False, server_default='0'))

    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trophy_image_url', sa.String(), nullable=True))

    with op.batch_alter_table('holiday_categories', schema=None) as batch_op:
        batch_op.drop_column('trophy_image_url')
