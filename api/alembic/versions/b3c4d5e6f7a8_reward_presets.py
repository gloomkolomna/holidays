from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "71fb5c8a0768"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_tasks_one_active", table_name="tasks")
    with op.batch_alter_table("reward_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("preset_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("effect_type", sa.String(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("effect_config", sa.Text(), server_default="{}", nullable=False))
        batch_op.create_index("uq_reward_items_preset_key", ["preset_key"], unique=True)
    with op.batch_alter_table("reward_purchases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("item_title", sa.String(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("status", sa.String(), server_default="available", nullable=False))
        batch_op.add_column(sa.Column("effect_payload", sa.Text(), server_default="{}", nullable=False))
        batch_op.add_column(sa.Column("used_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("target_card_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("target_task_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("external_reference", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))
    op.execute("UPDATE reward_purchases SET item_title = COALESCE((SELECT title FROM reward_items WHERE id = item_id), '')")
    op.execute("UPDATE reward_purchases SET status = 'used'")
    with op.batch_alter_table("reward_purchases", schema=None) as batch_op:
        batch_op.alter_column("item_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("code_id", existing_type=sa.Integer(), nullable=True)
    op.execute("UPDATE reward_purchases SET item_id = NULL, code_id = NULL")
    op.execute("DELETE FROM reward_codes")
    op.execute("DELETE FROM reward_items")


def downgrade() -> None:
    with op.batch_alter_table("reward_purchases", schema=None) as batch_op:
        batch_op.drop_column("last_error")
        batch_op.drop_column("external_reference")
        batch_op.drop_column("target_task_id")
        batch_op.drop_column("target_card_id")
        batch_op.drop_column("used_at")
        batch_op.drop_column("effect_payload")
        batch_op.drop_column("status")
        batch_op.drop_column("item_title")
    with op.batch_alter_table("reward_items", schema=None) as batch_op:
        batch_op.drop_index("uq_reward_items_preset_key")
        batch_op.drop_column("effect_config")
        batch_op.drop_column("effect_type")
        batch_op.drop_column("preset_key")
    op.create_index("uq_tasks_one_active", "tasks", ["user_id"], unique=True, sqlite_where=sa.text("status = 'active'"))
