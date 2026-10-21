from __future__ import annotations

from sqlalchemy.orm import Session

from models import CollectionReward, Holiday, User, UserCard


def holiday_filled_card_ids(holiday: Holiday) -> set[int]:
    return {c.id for cat in holiday.categories for c in cat.cards if c.title.strip()}


def ensure_collection_reward(db: Session, user_id: int, holiday_id: int) -> bool:
    """Начисляет кристалл и кубок за полную коллекцию — один раз.

    Полнота считается по заполненным карточкам праздника (админские
    черновики не учитываются, чтобы коллекция была достижима).
    """
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if holiday is None:
        return False

    filled = holiday_filled_card_ids(holiday)
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
            CollectionReward.holiday_id == holiday_id,
        )
        .first()
    )
    if exists is not None:
        return False

    db.add(CollectionReward(user_id=user_id, holiday_id=holiday_id, crystals=1))
    user = db.query(User).filter(User.vk_id == user_id).first()
    if user is not None:
        user.crystals = (user.crystals or 0) + 1
    db.commit()
    return True
