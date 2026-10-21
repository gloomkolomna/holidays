from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import require_role
from models import Holiday, User, UserCard

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


def _full_name(user: User) -> str:
    return user.display_name or f"Игрок {user.vk_id}"


@admin_router.get("", response_model=list[PlayerOut])
def list_players(db: Session = Depends(get_db)):
    holidays = db.query(Holiday).order_by(Holiday.starts_at.desc()).all()
    holiday_filled = {
        h.id: {c.id for cat in h.categories for c in cat.cards if c.title.strip()}
        for h in holidays
    }
    holiday_titles = {h.id: h.title for h in holidays}

    card_to_holiday = {
        c.id: c.holiday_id
        for h in holidays
        for c in h.categories
        for c in c.cards
        if c.title.strip()
    }

    users = db.query(User).order_by(User.created_at.desc()).limit(500).all()
    out: list[PlayerOut] = []
    for user in users:
        owned = {
            row[0]
            for row in db.query(UserCard.card_id).filter(UserCard.user_id == user.vk_id).all()
        }
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

        out.append(
            PlayerOut(
                vk_id=user.vk_id,
                display_name=_full_name(user),
                role=user.role,
                crystals=user.crystals or 0,
                cards_total=len(owned),
                collections=collections,
            )
        )
    return out
