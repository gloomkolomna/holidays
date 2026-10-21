from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models import Holiday, HolidayCard, Task, User, UserCard
from services.cards_grid import all_cards, has_active_task
from services.msk_time import now_msk

router = APIRouter(prefix="/api/shop", tags=["shop"], dependencies=[Depends(get_current_user)])

PENALTY_CROSSES = 1000


class ShopCardOut(BaseModel):
    id: int
    title: str
    task_text: str | None
    image_url: str | None
    day: str | None
    is_trophy: bool
    norm_crosses: int
    penalty_crosses: int


class ShopHolidayOut(BaseModel):
    holiday_id: int
    title: str
    cards: list[ShopCardOut]


class ShopOut(BaseModel):
    holidays: list[ShopHolidayOut]
    has_active_task: bool
    penalty_crosses: int


def _is_finished(holiday: Holiday) -> bool:
    return now_msk().replace(tzinfo=None) >= holiday.ends_at


def _card_out(card: HolidayCard) -> ShopCardOut:
    return ShopCardOut(
        id=card.id,
        title=card.title,
        task_text=card.task_text,
        image_url=card.image_url,
        day=card.day,
        is_trophy=bool(card.is_trophy),
        norm_crosses=card.category.norm_crosses if card.category else 0,
        penalty_crosses=PENALTY_CROSSES,
    )


@router.get("", response_model=ShopOut)
def get_shop(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    collected = {
        uc.card_id
        for uc in db.query(UserCard).filter(UserCard.user_id == user.vk_id).all()
    }

    holidays = db.query(Holiday).order_by(Holiday.ends_at.desc()).all()
    out: list[ShopHolidayOut] = []
    for holiday in holidays:
        if not _is_finished(holiday) or not holiday.shop_enabled:
            continue
        cards = [c for c in all_cards(holiday) if c.title.strip() and c.id not in collected]
        if not cards:
            continue
        out.append(
            ShopHolidayOut(
                holiday_id=holiday.id,
                title=holiday.title,
                cards=[_card_out(c) for c in cards],
            )
        )

    return ShopOut(
        holidays=out,
        has_active_task=has_active_task(db, user.vk_id),
        penalty_crosses=PENALTY_CROSSES,
    )


class TakeIn(BaseModel):
    card_id: int


@router.post("/take")
def take_card(data: TakeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(HolidayCard).filter(HolidayCard.id == data.card_id).first()
    if card is None or not card.title.strip() or card.category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")

    holiday = db.query(Holiday).filter(Holiday.id == card.holiday_id).first()
    if holiday is None or not _is_finished(holiday):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Карточку можно выкупить только после завершения праздника")
    if not holiday.shop_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Магазин выкупа закрыт для этого праздника")

    if db.query(UserCard).filter(UserCard.user_id == user.vk_id, UserCard.card_id == card.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Эта карточка уже в коллекции")

    if has_active_task(db, user.vk_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сначала сдайте текущее задание — новое взять нельзя",
        )

    task = Task(
        user_id=user.vk_id,
        holiday_id=holiday.id,
        card_id=card.id,
        kind="penalty",
        required_crosses=PENALTY_CROSSES,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "ok": True,
        "task_id": task.id,
        "card_id": card.id,
        "required_crosses": task.required_crosses,
    }
