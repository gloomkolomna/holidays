"""category_rewards_animation_count_opacity

Revision ID: 90b9a81e6f1d
Revises: cf75845d3140
Create Date: 2026-10-21 15:48:21.828584

Награды за коллекцию переходят с праздника на раздел (категорию):
старые праздничные строки collection_rewards удаляются (кристаллы
у пользователей остаются), добавляется category_id с уникальностью
user+category. Плюс настройки анимации: количество объектов и прозрачность.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '90b9a81e6f1d'
down_revision: Union[str, None] = 'cf75845d3140'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM collection_rewards")

    with op.batch_alter_table('collection_rewards', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            'fk_collection_rewards_category_id', 'holiday_categories',
            ['category_id'], ['id'], ondelete='CASCADE',
        )
        batch_op.drop_constraint('uq_collectionreward_user_holiday', type_='unique')
        batch_op.create_unique_constraint('uq_collectionreward_user_category', ['user_id', 'category_id'])

    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.add_column(sa.Column('animation_count', sa.Integer(), server_default='14', nullable=False))
        batch_op.add_column(sa.Column('animation_opacity', sa.Integer(), server_default='100', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.drop_column('animation_opacity')
        batch_op.drop_column('animation_count')

    op.execute("DELETE FROM collection_rewards")

    with op.batch_alter_table('collection_rewards', schema=None) as batch_op:
        batch_op.drop_constraint('fk_collection_rewards_category_id', type_='foreignkey')
        batch_op.drop_constraint('uq_collectionreward_user_category', type_='unique')
        batch_op.create_unique_constraint('uq_collectionreward_user_holiday', ['user_id', 'holiday_id'])
        batch_op.drop_column('category_id')
