from __future__ import annotations

from sqlalchemy.orm import Session

from models import CollectionReward, HolidayCategory, User, UserCard


def category_filled_card_ids(category: HolidayCategory) -> set[int]:
    return {c.id for c in category.cards if c.title.strip()}


def ensure_collection_reward(db: Session, user_id: int, category_id: int) -> bool:
    """Начисляет кристалл и кубок за полностью собранный раздел — один раз.

    Полнота считается по заполненным карточкам раздела (включая
    магазинные и кубковые; админские черновики не учитываются, чтобы
    раздел был достижим).
    """
    category = db.query(HolidayCategory).filter(HolidayCategory.id == category_id).first()
    if category is None:
        return False

    filled = category_filled_card_ids(category)
    if not filled:
        return False

    owned = {
        row[0]
        for row in db.query(UserCard.card_id).filter(UserCard.user_id == user_id).all()
    }
    if not filled.issubset(owned):
        return False

    exists = (
        db.query(CollectionReward)
        .filter(
            CollectionReward.user_id == user_id,
            CollectionReward.category_id == category_id,
        )
        .first()
    )
    if exists is not None:
        return False

    db.add(CollectionReward(
        user_id=user_id,
        holiday_id=category.holiday_id,
        category_id=category_id,
        crystals=1,
    ))
    user = db.query(User).filter(User.vk_id == user_id).first()
    if user is not None:
        user.crystals = (user.crystals or 0) + 1
    db.flush()
    return True
