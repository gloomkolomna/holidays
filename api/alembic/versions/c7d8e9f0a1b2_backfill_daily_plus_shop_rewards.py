from typing import Sequence, Union

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TEMP TABLE collection_reward_backfill (
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            holiday_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, category_id)
        )
    """)
    op.execute("""
        INSERT INTO collection_reward_backfill (user_id, category_id, holiday_id)
        SELECT u.vk_id, cat.id, cat.holiday_id
        FROM users u
        CROSS JOIN holiday_categories cat
        WHERE EXISTS (
            SELECT 1 FROM holiday_cards hc
            WHERE hc.category_id = cat.id
              AND hc.day IS NOT NULL
              AND TRIM(hc.title) <> ''
        )
        AND NOT EXISTS (
            SELECT 1 FROM holiday_cards hc
            WHERE hc.category_id = cat.id
              AND hc.day IS NOT NULL
              AND TRIM(hc.title) <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM user_cards uc
                  WHERE uc.user_id = u.vk_id AND uc.card_id = hc.id
              )
        )
        AND EXISTS (
            SELECT 1 FROM holiday_cards hc
            JOIN user_cards uc ON uc.card_id = hc.id
            WHERE hc.category_id = cat.id
              AND hc.day IS NULL
              AND TRIM(hc.title) <> ''
              AND uc.user_id = u.vk_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM collection_rewards cr
            WHERE cr.user_id = u.vk_id AND cr.category_id = cat.id
        )
    """)
    op.execute("""
        INSERT INTO collection_rewards (user_id, holiday_id, category_id, crystals, awarded_at)
        SELECT user_id, holiday_id, category_id, 1, CURRENT_TIMESTAMP
        FROM collection_reward_backfill
    """)
    op.execute("""
        UPDATE users
        SET crystals = crystals + (
            SELECT COUNT(*) FROM collection_reward_backfill brf
            WHERE brf.user_id = users.vk_id
        )
        WHERE vk_id IN (SELECT user_id FROM collection_reward_backfill)
    """)
    op.execute("DROP TABLE collection_reward_backfill")


def downgrade() -> None:
    pass
