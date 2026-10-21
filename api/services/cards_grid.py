from __future__ import annotations
import datetime

from sqlalchemy.orm import Session

from models import HolidayCard, HolidayCategory, Task, UserCard
from services.msk_time import now_msk, today_msk


def holiday_days(holiday) -> list[str]:
    """Дни праздника С..ПО (МСК, наивные даты). Если ПО — 00:00, последний день — накануне."""
    start = holiday.starts_at.date()
    end = holiday.ends_at.date()
    if holiday.ends_at.time() == datetime.time(0, 0):
        end -= datetime.timedelta(days=1)
    if end < start:
        return []
    return [(start + datetime.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def ensure_card_slots(db: Session, holiday) -> None:
    """Сетка карточек: по одному слоту на каждую категорию × день праздника.

    Добавляет недостающие пустые слоты и удаляет пустые слоты исчезнувших
    дней (заполненные и собранные карточки не трогает).
    """
    days = holiday_days(holiday)
    valid_days = set(days)

    cats = (
        db.query(HolidayCategory)
        .filter(HolidayCategory.holiday_id == holiday.id)
        .order_by(HolidayCategory.id)
        .all()
    )
    for cat in cats:
        existing = {
            c[0] for c in db.query(HolidayCard.day)
            .filter(HolidayCard.category_id == cat.id, HolidayCard.day.isnot(None))
            .all()
        }
        for day in days:
            if day not in existing:
                db.add(HolidayCard(holiday_id=holiday.id, category_id=cat.id, day=day, title=""))

    db.flush()
    if valid_days:
        for cat in cats:
            cards = (
                db.query(HolidayCard)
                .filter(
                    HolidayCard.category_id == cat.id,
                    HolidayCard.day.isnot(None),
                    HolidayCard.day.notin_(list(valid_days)),
                )
                .all()
            )
            for card in cards:
                if card.title.strip() or card.image_url:
                    continue
                if db.query(UserCard).filter(UserCard.card_id == card.id).first() is not None:
                    continue
                db.delete(card)
    db.commit()
    db.expire_all()


def get_active_holiday(db: Session):
    from models import Holiday

    now = now_msk().replace(tzinfo=None)
    return (
        db.query(Holiday)
        .filter(Holiday.starts_at <= now, Holiday.ends_at > now)
        .order_by(Holiday.starts_at.asc())
        .first()
    )


def has_active_task(db: Session, user_id: int) -> bool:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status == "active")
        .first()
        is not None
    )


def collected_card_ids(db: Session, user_id: int) -> set[int]:
    rows = db.query(UserCard.card_id).filter(UserCard.user_id == user_id).all()
    return {r[0] for r in rows}


def all_cards(holiday) -> list[HolidayCard]:
    return [c for cat in holiday.categories for c in cat.cards]


def todays_cards(holiday) -> list[HolidayCard]:
    day = today_msk().isoformat()
    return [c for cat in holiday.categories for c in cat.cards if c.day == day and c.title.strip()]
