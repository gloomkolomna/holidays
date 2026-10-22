from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
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

MAX_REPORT_CROSSES = 1_000_000


class CardOut(BaseModel):
    id: int
    title: str
    task_text: str | None
    image_url: str | None
    day: str | None
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
    trophy_image_url: str | None
    complete: bool
    cards: list[CollectionCardOut]


class CollectionOut(BaseModel):
    holiday_id: int
    title: str
    collected: int
    total: int
    categories: list[CollectionCategoryOut]


def _card_out(card: HolidayCard) -> CardOut:
    return CardOut(
        id=card.id,
        title=card.title,
        task_text=card.task_text,
        image_url=card.image_url,
        day=card.day,
        norm_crosses=card.category.norm_crosses if card.category else 0,
    )


def _task_out(db: Session, task: Task | None) -> TaskOut | None:
    if task is None:
        return None
    card = db.query(HolidayCard).filter(HolidayCard.id == task.card_id).first()
    if card is None:
        return None
    return TaskOut(
        id=task.id,
        kind=task.kind,
        required_crosses=task.required_crosses,
        card=_card_out(card),
    )


@router.get("/state", response_model=GameStateOut)
def get_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = (
        db.query(Task)
        .filter(Task.user_id == user.vk_id, Task.status == "active")
        .first()
    )
    active_task_out = _task_out(db, task)

    holiday = get_active_holiday(db)
    if holiday is None:
        return GameStateOut(
            holiday_id=None,
            holiday_title=None,
            day=today_msk().isoformat(),
            today_cards=[],
            active_task=active_task_out,
            collected_count=0,
            cards_total=0,
        )

    collected = collected_card_ids(db, user.vk_id)
    active_card_ids = {task.card_id} if task else set()

    today_out = [
        DayCardOut(
            card=_card_out(card),
            collected=card.id in collected,
            is_current=card.id in active_card_ids,
        )
        for card in todays_cards(holiday)
    ]

    all_slots = all_cards(holiday)
    filled_ids = {c.id for c in all_slots if c.title.strip()}
    return GameStateOut(
        holiday_id=holiday.id,
        holiday_title=holiday.title,
        day=today_msk().isoformat(),
        today_cards=today_out,
        active_task=active_task_out,
        collected_count=len(collected & filled_ids),
        cards_total=len(filled_ids),
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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сначала сдайте текущее задание — новое взять нельзя",
        )
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
    if task.kind == "penalty":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="От выкупленного задания нельзя отказаться — сдайте его (1000 крестиков)",
        )
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
    photo_preview: UploadFile | None = File(None),
    photo_saga: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_own_task(db, user, task_id)
    if task.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Задание уже закрыто")
    if mode not in ("norm", "penalty"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный режим сдачи: норма или штраф")
    if task.kind == "penalty" and mode == "penalty":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Выкупленное задание сдаётся по норме (1000 крестиков) — режим «Штраф» к нему не применяется",
        )
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Число крестиков должно быть больше нуля")
    if amount > MAX_REPORT_CROSSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Слишком большое число крестиков (максимум {MAX_REPORT_CROSSES})",
        )

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
    url_preview = (
        save_upload(photo_preview, prefix=f"report_{user.vk_id}_preview", max_size=1280)
        if photo_preview and photo_preview.filename
        else None
    )
    url_saga = (
        save_upload(photo_saga, prefix=f"report_{user.vk_id}_saga", max_size=1280)
        if photo_saga and photo_saga.filename
        else None
    )

    report = StitchReport(
        user_id=user.vk_id,
        task_id=task.id,
        amount=amount,
        photo_before=url_before,
        photo_after=url_after,
        photo_preview=url_preview,
        photo_saga=url_saga,
    )
    db.add(report)

    already = db.query(UserCard).filter(UserCard.user_id == user.vk_id, UserCard.card_id == task.card_id).first()
    if already is None:
        db.add(UserCard(user_id=user.vk_id, card_id=task.card_id, source=task.kind))

    task.status = "done"
    task.done_at = datetime.datetime.utcnow()

    if already is None:
        from services.rewards import ensure_collection_reward

        category_id = (
            db.query(HolidayCard.category_id)
            .filter(HolidayCard.id == task.card_id)
            .scalar()
        )
        if category_id is not None:
            db.flush()
            ensure_collection_reward(db, user.vk_id, category_id)

    db.commit()

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
        filled_cards = [c for c in cat.cards if c.title.strip()]
        total += len(filled_cards)
        collected_count += sum(1 for c in filled_cards if c.id in owned)
        filled_ids = {c.id for c in filled_cards}
        complete = bool(filled_ids) and filled_ids.issubset(owned.keys())
        categories_out.append(
            CollectionCategoryOut(
                id=cat.id,
                title=cat.title,
                norm_crosses=cat.norm_crosses,
                trophy_image_url=cat.trophy_image_url,
                complete=complete,
                cards=entries,
            )
        )

    return CollectionOut(
        holiday_id=holiday.id,
        title=holiday.title,
        collected=collected_count,
        total=total,
        categories=categories_out,
    )


class MyReportOut(BaseModel):
    id: int
    amount: int
    photo_before: str | None
    photo_after: str | None
    photo_preview: str | None
    photo_saga: str | None
    created_at: str | None
    card_title: str
    holiday_title: str


@router.get("/reports/my", response_model=list[MyReportOut])
def my_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holiday_titles = {h.id: h.title for h in db.query(Holiday.id, Holiday.title).all()}
    rows = (
        db.query(StitchReport, Task, HolidayCard)
        .outerjoin(Task, StitchReport.task_id == Task.id)
        .outerjoin(HolidayCard, Task.card_id == HolidayCard.id)
        .filter(StitchReport.user_id == user.vk_id)
        .order_by(StitchReport.created_at.desc())
        .all()
    )
    return [
        MyReportOut(
            id=report.id,
            amount=report.amount,
            photo_before=report.photo_before,
            photo_after=report.photo_after,
            photo_preview=report.photo_preview,
            photo_saga=report.photo_saga,
            created_at=report.created_at.isoformat() if report.created_at else None,
            card_title=card.title if card else "",
            holiday_title=holiday_titles.get(card.holiday_id, "") if card else "",
        )
        for report, task, card in rows
    ]
