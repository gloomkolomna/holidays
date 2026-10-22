from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import require_role
from models import Holiday, HolidayCard, HolidayCategory, StitchReport, Task, User, UserCard

admin_router = APIRouter(prefix="/api/admin/players", tags=["admin-players"], dependencies=[Depends(require_role("admin"))])


class PlayerCollectionOut(BaseModel):
    holiday_id: int
    title: str
    collected: int
    total: int
    full: bool


class PlayerOut(BaseModel):
    vk_id: int
    display_name: str
    role: str
    crystals: int
    cards_total: int
    collections: list[PlayerCollectionOut]


class PlayerTaskOut(BaseModel):
    id: int
    kind: str
    required_crosses: int
    taken_at: str | None
    holiday_title: str
    card_title: str
    card_task_text: str | None
    card_image_url: str | None
    card_day: str | None


class PlayerCardOut(BaseModel):
    card_id: int
    title: str
    image_url: str | None
    day: str | None
    category_title: str
    holiday_id: int
    holiday_title: str
    source: str
    earned_at: str | None


class PlayerReportOut(BaseModel):
    id: int
    amount: int
    photo_before: str | None
    photo_after: str | None
    created_at: str | None
    card_title: str
    holiday_title: str


class PlayerDetailOut(BaseModel):
    player: PlayerOut
    active_task: PlayerTaskOut | None
    cards: list[PlayerCardOut]
    reports: list[PlayerReportOut]


def _full_name(user: User) -> str:
    return user.display_name or f"Игрок {user.vk_id}"


def _owned_card_ids(db: Session, vk_id: int) -> set[int]:
    return {row[0] for row in db.query(UserCard.card_id).filter(UserCard.user_id == vk_id).all()}


def _holiday_index(db: Session):
    holidays = db.query(Holiday).order_by(Holiday.starts_at.desc()).all()
    holiday_filled = {
        h.id: {c.id for cat in h.categories for c in cat.cards if c.title.strip()}
        for h in holidays
    }
    holiday_titles = {h.id: h.title for h in holidays}
    card_to_holiday = {
        c.id: c.holiday_id
        for h in holidays
        for cat in h.categories
        for c in cat.cards
        if c.title.strip()
    }
    return holiday_titles, holiday_filled, card_to_holiday


def _player_out(db: Session, user: User, holiday_titles, holiday_filled, card_to_holiday) -> PlayerOut:
    owned = _owned_card_ids(db, user.vk_id)
    by_holiday: dict[int, int] = {}
    for card_id in owned:
        hid = card_to_holiday.get(card_id)
        if hid is not None:
            by_holiday[hid] = by_holiday.get(hid, 0) + 1

    collections = []
    for hid in sorted(holiday_titles, key=lambda x: x):
        filled = holiday_filled.get(hid) or set()
        collected = by_holiday.get(hid, 0)
        collections.append(
            PlayerCollectionOut(
                holiday_id=hid,
                title=holiday_titles[hid],
                collected=collected,
                total=len(filled),
                full=bool(filled) and filled.issubset(owned),
            )
        )

    return PlayerOut(
        vk_id=user.vk_id,
        display_name=_full_name(user),
        role=user.role,
        crystals=user.crystals or 0,
        cards_total=len(owned),
        collections=collections,
    )


@admin_router.get("", response_model=list[PlayerOut])
def list_players(search: str | None = Query(default=None), db: Session = Depends(get_db)):
    holiday_titles, holiday_filled, card_to_holiday = _holiday_index(db)

    q = (search or "").strip().casefold()
    users = db.query(User).order_by(User.created_at.desc()).all()
    if q:
        users = [u for u in users if q in _full_name(u).casefold() or q in str(u.vk_id)]

    return [_player_out(db, u, holiday_titles, holiday_filled, card_to_holiday) for u in users[:500]]


@admin_router.get("/{vk_id}", response_model=PlayerDetailOut)
def get_player(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Игрок не найден")

    holiday_titles, holiday_filled, card_to_holiday = _holiday_index(db)
    player = _player_out(db, user, holiday_titles, holiday_filled, card_to_holiday)

    task = db.query(Task).filter(Task.user_id == vk_id, Task.status == "active").first()
    active_task_out: PlayerTaskOut | None = None
    if task is not None:
        card = db.query(HolidayCard).filter(HolidayCard.id == task.card_id).first()
        active_task_out = PlayerTaskOut(
            id=task.id,
            kind=task.kind,
            required_crosses=task.required_crosses,
            taken_at=task.taken_at.isoformat() if task.taken_at else None,
            holiday_title=holiday_titles.get(task.holiday_id, ""),
            card_title=card.title if card else "",
            card_task_text=card.task_text if card else None,
            card_image_url=card.image_url if card else None,
            card_day=card.day if card else None,
        )

    rows = (
        db.query(UserCard, HolidayCard, HolidayCategory)
        .join(HolidayCard, UserCard.card_id == HolidayCard.id)
        .join(HolidayCategory, HolidayCard.category_id == HolidayCategory.id)
        .filter(UserCard.user_id == vk_id)
        .order_by(HolidayCard.holiday_id, HolidayCategory.id, HolidayCard.day)
        .all()
    )
    cards_out = [
        PlayerCardOut(
            card_id=card.id,
            title=card.title,
            image_url=card.image_url,
            day=card.day,
            category_title=cat.title,
            holiday_id=card.holiday_id,
            holiday_title=holiday_titles.get(card.holiday_id, ""),
            source=uc.source,
            earned_at=uc.earned_at.isoformat() if uc.earned_at else None,
        )
        for uc, card, cat in rows
    ]

    report_rows = (
        db.query(StitchReport, Task, HolidayCard)
        .outerjoin(Task, StitchReport.task_id == Task.id)
        .outerjoin(HolidayCard, Task.card_id == HolidayCard.id)
        .filter(StitchReport.user_id == vk_id)
        .order_by(StitchReport.created_at.desc())
        .all()
    )
    reports_out = [
        PlayerReportOut(
            id=report.id,
            amount=report.amount,
            photo_before=report.photo_before,
            photo_after=report.photo_after,
            created_at=report.created_at.isoformat() if report.created_at else None,
            card_title=card.title if card else "",
            holiday_title=holiday_titles.get(card.holiday_id, "") if card else "",
        )
        for report, task, card in report_rows
    ]

    return PlayerDetailOut(player=player, active_task=active_task_out, cards=cards_out, reports=reports_out)
