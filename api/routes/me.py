from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models import User

router = APIRouter(prefix="/api", tags=["me"])


class MeResponse(BaseModel):
    vk_id: int
    role: str
    status: str
    display_name: str | None
    crystals: int
    music_enabled: bool
    is_member: bool | None
    created_at: str | None


class MusicIn(BaseModel):
    music_enabled: bool


def _me(user: User) -> MeResponse:
    return MeResponse(
        vk_id=user.vk_id,
        role=user.role,
        status=user.status or "active",
        display_name=user.display_name,
        crystals=user.crystals,
        music_enabled=bool(user.music_enabled),
        is_member=user.is_member,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)):
    return _me(user)


@router.put("/me/music", response_model=MeResponse)
def set_music(data: MusicIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(User).filter(User.vk_id == user.vk_id).first()
    if row is None:
        row = user
    row.music_enabled = data.music_enabled
    db.commit()
    db.refresh(row)
    return _me(row)
