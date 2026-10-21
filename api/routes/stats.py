from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import require_role
from models import Holiday, HolidayCard, UserCard
from services.msk_time import MSK, now_msk

admin_router = APIRouter(prefix="/api/admin/stats", tags=["admin-stats"], dependencies=[Depends(require_role("admin"))])


class DailyStatRow(BaseModel):
    card_id: int
    title: str
    holiday_id: int
    holiday_title: str
    count: int


class DailyStatsOut(BaseModel):
    day: str
    total_cards: int
    total_players: int
    rows: list[DailyStatRow]


def _day_bounds_utc(day: str) -> tuple[datetime.datetime, datetime.datetime]:
    day_dt = datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=MSK)
    start_utc = day_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    end_utc = (day_dt + datetime.timedelta(days=1)).astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


@admin_router.get("/daily", response_model=DailyStatsOut)
def daily_stats(day: str | None = Query(default=None), db: Session = Depends(get_db)):
    target = day or (now_msk() - datetime.timedelta(days=1)).date().isoformat()
    try:
        start_utc, end_utc = _day_bounds_utc(target)
    except ValueError:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата должна быть в формате ГГГГ-ММ-ДД")

    rows = (
        db.query(HolidayCard, Holiday, __import__("sqlalchemy").func.count(UserCard.id))
        .join(Holiday, Holiday.id == HolidayCard.holiday_id)
        .join(UserCard, UserCard.card_id == HolidayCard.id)
        .filter(UserCard.earned_at >= start_utc, UserCard.earned_at < end_utc)
        .group_by(HolidayCard.id, Holiday.id)
        .all()
    )

    players = (
        db.query(UserCard.user_id)
        .filter(UserCard.earned_at >= start_utc, UserCard.earned_at < end_utc)
        .distinct()
        .count()
    )

    out = [
        DailyStatRow(
            card_id=card.id,
            title=card.title,
            holiday_id=holiday.id,
            holiday_title=holiday.title,
            count=count,
        )
        for card, holiday, count in rows
    ]
    out.sort(key=lambda r: -r.count)

    return DailyStatsOut(
        day=target,
        total_cards=sum(r.count for r in out),
        total_players=players,
        rows=out,
    )
