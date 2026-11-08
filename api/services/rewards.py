from __future__ import annotations

from sqlalchemy.orm import Session

from models import CollectionReward, HolidayCategory, User, UserCard


def category_is_complete(category: HolidayCategory, owned: set[int]) -> bool:
    holiday_days = (category.holiday.ends_at.date() - category.holiday.starts_at.date()).days + 1
    filled = {c.id for c in category.cards if c.title.strip()}
    return len(filled & owned) >= holiday_days + 1


def ensure_collection_reward(db: Session, user_id: int, category_id: int) -> bool:
    """Начисляет кристалл и кубок за набор карточек в количестве дней праздника + 1 — один раз."""
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
