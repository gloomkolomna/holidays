from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import require_role
from services.game_access import is_game_open, set_game_open

admin_router = APIRouter(
    prefix="/api/admin/settings",
    tags=["admin-settings"],
    dependencies=[Depends(require_role("admin"))],
)


class GameStateOut(BaseModel):
    game_open: bool


class GameStateIn(BaseModel):
    game_open: bool


@admin_router.get("/game", response_model=GameStateOut)
def get_game_state(db: Session = Depends(get_db)):
    return GameStateOut(game_open=is_game_open(db))


@admin_router.put("/game", response_model=GameStateOut)
def set_game_state(data: GameStateIn, db: Session = Depends(get_db)):
    set_game_open(db, data.game_open)
    return GameStateOut(game_open=is_game_open(db))
