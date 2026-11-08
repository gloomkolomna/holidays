from __future__ import annotations

from sqlalchemy.orm import Session

from models import CollectionReward, HolidayCategory, User, UserCard


def category_is_complete(category: HolidayCategory, owned: set[int]) -> bool:
    filled = [c for c in category.cards if c.title.strip()]
    daily = {c.id for c in filled if c.day is not None}
    if not daily or not daily.issubset(owned):
        return False
    return any(c.id in owned for c in filled if c.day is None)


def ensure_collection_reward(db: Session, user_id: int, category_id: int) -> bool:
    """Начисляет кристалл и кубок за все дневные карточки и одну магазинную — один раз."""
    category = db.query(HolidayCategory).filter(HolidayCategory.id == category_id).first()
    if category is None:
        return False

    owned = {
        row[0]
        for row in db.query(UserCard.card_id).filter(UserCard.user_id == user_id).all()
    }
    if not category_is_complete(category, owned):
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
