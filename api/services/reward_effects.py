from __future__ import annotations

import datetime

from models import RewardItem, RewardPurchase, Task
from services.cards_grid import get_active_holiday

SHOP_EFFECTS = ("shop_always_open", "shop_without_penalty")


def active_task_count(db, user_id: int) -> int:
    return db.query(Task).filter(Task.user_id == user_id, Task.status == "active").count()


def active_effect(db, user_id: int, effect_type: str):
    return (
        db.query(RewardPurchase)
        .join(RewardItem, RewardItem.id == RewardPurchase.item_id)
        .filter(
            RewardPurchase.user_id == user_id,
            RewardPurchase.status == "active",
            RewardItem.effect_type == effect_type,
        )
        .first()
    )


def expire_shop_effects(db, user_id: int):
    if get_active_holiday(db) is None:
        return
    effects = (
        db.query(RewardPurchase)
        .join(RewardItem, RewardItem.id == RewardPurchase.item_id)
        .filter(
            RewardPurchase.user_id == user_id,
            RewardPurchase.status == "active",
            RewardItem.effect_type.in_(SHOP_EFFECTS),
        )
        .all()
    )
    for purchase in effects:
        purchase.status = "used"
        purchase.used_at = datetime.datetime.utcnow()
    if effects:
        db.commit()


def shop_open(db, user_id: int, now=None):
    from services.msk_time import now_msk

    if get_active_holiday(db) is not None:
        expire_shop_effects(db, user_id)
        return False, "holiday_active"
    current = now if now is not None else now_msk()
    if current.weekday() in (5, 6) or active_effect(db, user_id, "shop_always_open"):
        return True, "open"
    return False, "weekday"


def can_take_task(db, user_id: int) -> bool:
    count = active_task_count(db, user_id)
    if count == 0:
        return True
    return count == 1 and active_effect(db, user_id, "extra_active_task") is not None


def finish_extra_task_effect(db, user_id: int, tasks_before_report: int):
    if tasks_before_report < 2:
        return
    purchase = active_effect(db, user_id, "extra_active_task")
    if purchase:
        purchase.status = "used"
        purchase.used_at = datetime.datetime.utcnow()
