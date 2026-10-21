from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models import Holiday, HolidayCard, StitchReport, Task, User, UserCard
from services.cards_grid import (
    all_cards,
    collected_card_ids,
    get_active_holiday,
    has_active_task,
    todays_cards,
)
from services.msk_time import today_msk

router = APIRouter(prefix="/api/game", tags=["game"])

DUP_WINDOW_SECONDS = 10


class CardOut(BaseModel):
    id: int
    title: str
    task_text: str | None
    image_url: str | None
    day: str | None
    is_trophy: bool
    norm_crosses: int


class DayCardOut(BaseModel):
    card: CardOut
    collected: bool
    is_current: bool


class TaskOut(BaseModel):
    id: int
    kind: str
    required_crosses: int
    card: CardOut


class GameStateOut(BaseModel):
    holiday_id: int | None
    holiday_title: str | None
    day: str
    today_cards: list[DayCardOut]
    active_task: TaskOut | None
    collected_count: int
    cards_total: int


class CollectionCardOut(BaseModel):
    card: CardOut
    collected: bool
    source: str | None
    earned_at: str | None


class CollectionCategoryOut(BaseModel):
    id: int
    title: str
    norm_crosses: int
    cards: list[CollectionCardOut]


class CollectionOut(BaseModel):
    holiday_id: int
    title: str
    collected: int
    total: int
    trophy_image_url: str | None
    categories: list[CollectionCategoryOut]


def _card_out(card: HolidayCard) -> CardOut:
    return CardOut(
        id=card.id,
        title=card.title,
        task_text=card.task_text,
        image_url=card.image_url,
        day=card.day,
        is_trophy=bool(card.is_trophy),
        norm_crosses=card.category.norm_crosses if card.category else 0,
    )


@router.get("/state", response_model=GameStateOut)
def get_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holiday = get_active_holiday(db)
    if holiday is None:
        return GameStateOut(
            holiday_id=None,
            holiday_title=None,
            day=today_msk().isoformat(),
            today_cards=[],
            active_task=None,
            collected_count=0,
            cards_total=0,
        )

    collected = collected_card_ids(db, user.vk_id)
    task = (
        db.query(Task)
        .filter(Task.user_id == user.vk_id, Task.status == "active")
        .first()
    )
    active_card_ids = {task.card_id} if task else set()

    today_out = [
        DayCardOut(
            card=_card_out(card),
            collected=card.id in collected,
            is_current=card.id in active_card_ids,
        )
        for card in todays_cards(holiday)
    ]

    active_task_out: TaskOut | None = None
    if task is not None:
        card = db.query(HolidayCard).filter(HolidayCard.id == task.card_id).first()
        if card is not None:
            active_task_out = TaskOut(
                id=task.id,
                kind=task.kind,
                required_crosses=task.required_crosses,
                card=_card_out(card),
            )

    all_slots = all_cards(holiday)
    return GameStateOut(
        holiday_id=holiday.id,
        holiday_title=holiday.title,
        day=today_msk().isoformat(),
        today_cards=today_out,
        active_task=active_task_out,
        collected_count=len(collected & {c.id for c in all_slots}),
        cards_total=len(all_slots),
    )


@router.post("/cards/{card_id}/take", response_model=TaskOut)
def take_card(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = (
        db.query(HolidayCard)
        .filter(HolidayCard.id == card_id)
        .first()
    )
    if card is None or not card.title.strip() or card.category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")

    holiday = get_active_holiday(db)
    if holiday is None or holiday.id != card.holiday_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Праздник не активен")

    if card.day != today_msk().isoformat():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Эта карточка показывается в другой день")

    if db.query(UserCard).filter(UserCard.user_id == user.vk_id, UserCard.card_id == card.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Эта карточка уже в коллекции")

    if has_active_task(db, user.vk_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сначала сдайте текущее задание — новое взять нельзя",
        )

    task = Task(
        user_id=user.vk_id,
        holiday_id=card.holiday_id,
        card_id=card.id,
        kind="daily",
        required_crosses=card.category.norm_crosses,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskOut(
        id=task.id,
        kind=task.kind,
        required_crosses=task.required_crosses,
        card=_card_out(card),
    )


def _get_own_task(db: Session, user: User, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.vk_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")
    return task


@router.post("/tasks/{task_id}/abandon")
def abandon_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_own_task(db, user, task_id)
    if task.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Задание уже закрыто")
    task.status = "abandoned"
    task.done_at = datetime.datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/report")
def report_task(
    task_id: int,
    amount: int = Form(...),
    mode: str = Form("norm"),
    photo_before: UploadFile = File(...),
    photo_after: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_own_task(db, user, task_id)
    if task.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Задание уже закрыто")
    if mode not in ("norm", "penalty"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный режим сдачи: норма или штраф")
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Число крестиков должно быть больше нуля")

    required = task.required_crosses * (2 if mode == "penalty" else 1)
    if amount < required:
        label = "для штрафа" if mode == "penalty" else "по норме"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недостаточно крестиков {label}. Нужно: {required} (норма задания: {task.required_crosses})",
        )

    recent = (
        db.query(StitchReport)
        .filter(
            StitchReport.user_id == user.vk_id,
            StitchReport.task_id == task.id,
            StitchReport.created_at >= datetime.datetime.utcnow() - datetime.timedelta(seconds=DUP_WINDOW_SECONDS),
        )
        .first()
    )
    if recent is not None:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Отчёт уже отправлен, подождите немного")

    from services.uploads import save_upload

    url_before = save_upload(photo_before, prefix=f"report_{user.vk_id}_before", max_size=1280)
    url_after = save_upload(photo_after, prefix=f"report_{user.vk_id}_after", max_size=1280)

    report = StitchReport(
        user_id=user.vk_id,
        task_id=task.id,
        amount=amount,
        photo_before=url_before,
        photo_after=url_after,
    )
    db.add(report)

    already = db.query(UserCard).filter(UserCard.user_id == user.vk_id, UserCard.card_id == task.card_id).first()
    if already is None:
        db.add(UserCard(user_id=user.vk_id, card_id=task.card_id, source=task.kind))

    task.status = "done"
    task.done_at = datetime.datetime.utcnow()
    db.commit()

    if already is None:
        from services.rewards import ensure_collection_reward

        ensure_collection_reward(db, user.vk_id, task.holiday_id)

    return {
        "ok": True,
        "card_id": task.card_id,
        "collected": already is None,
        "mode": mode,
    }


@router.get("/collection", response_model=CollectionOut)
def get_collection(
    holiday_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Праздник не найден")

    owned = {
        uc.card_id: uc
        for uc in db.query(UserCard).filter(UserCard.user_id == user.vk_id).all()
    }

    def _entry(card: HolidayCard) -> CollectionCardOut:
        uc = owned.get(card.id)
        return CollectionCardOut(
            card=_card_out(card),
            collected=uc is not None,
            source=uc.source if uc else None,
            earned_at=uc.earned_at.isoformat() if uc else None,
        )

    categories_out = []
    total = 0
    collected_count = 0
    for cat in holiday.categories:
        entries = [_entry(c) for c in cat.cards]
        total += len(entries)
        collected_count += sum(1 for e in entries if e.collected)
        categories_out.append(
            CollectionCategoryOut(
                id=cat.id,
                title=cat.title,
                norm_crosses=cat.norm_crosses,
                cards=entries,
            )
        )

    return CollectionOut(
        holiday_id=holiday.id,
        title=holiday.title,
        collected=collected_count,
        total=total,
        trophy_image_url=holiday.trophy_image_url,
        categories=categories_out,
    )
