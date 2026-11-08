from typing import Sequence, Union

from alembic import op

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TEMP TABLE collection_reward_count_backfill (
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            holiday_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, category_id)
        )
    """)
    op.execute("""
        INSERT INTO collection_reward_count_backfill (user_id, category_id, holiday_id)
        SELECT u.vk_id, cat.id, cat.holiday_id
        FROM users u
        CROSS JOIN holiday_categories cat
        JOIN holidays h ON h.id = cat.holiday_id
        WHERE u.vk_id NOT IN (7496593, 168732789, 497212988, 541386371, 831173866)
        AND (
            SELECT COUNT(*)
            FROM user_cards uc
            JOIN holiday_cards hc ON hc.id = uc.card_id
            WHERE uc.user_id = u.vk_id
              AND hc.category_id = cat.id
              AND TRIM(hc.title) <> ''
        ) >= CAST(JULIANDAY(DATE(h.ends_at)) - JULIANDAY(DATE(h.starts_at)) AS INTEGER) + 2
        AND NOT EXISTS (
            SELECT 1 FROM collection_rewards cr
            WHERE cr.user_id = u.vk_id AND cr.category_id = cat.id
        )
    """)
    op.execute("""
        INSERT INTO collection_rewards (user_id, holiday_id, category_id, crystals, awarded_at)
        SELECT user_id, holiday_id, category_id, 1, CURRENT_TIMESTAMP
        FROM collection_reward_count_backfill
    """)
    op.execute("""
        UPDATE users
        SET crystals = crystals + (
            SELECT COUNT(*) FROM collection_reward_count_backfill brf
            WHERE brf.user_id = users.vk_id
        )
        WHERE vk_id IN (SELECT user_id FROM collection_reward_count_backfill)
    """)
    op.execute("DROP TABLE collection_reward_count_backfill")


def downgrade() -> None:
    pass
