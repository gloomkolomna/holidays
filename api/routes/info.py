from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import Setting

router = APIRouter(prefix="/api/info", tags=["info"], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix="/api/admin/info", tags=["admin-info"], dependencies=[Depends(require_role("admin"))])

INFO_SETTING_KEY = "info_blocks"

DEFAULT_BLOCKS: list[dict] = [
    {
        "title": "🧵 Пересчёт для полукреста",
        "text": (
            "Вышиваете полукрестом? Норма пересчитывается ×1,5:\n"
            "500 крестиков = 750 полукрестов\n"
            "400 крестиков = 600 полукрестов\n"
            "300 крестика = 450 полукрестов"
        ),
    },
    {"title": "🔑 Кодовое слово", "text": "Кодовое слово — название карточки"},
]


class InfoBlock(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=5000)


class InfoOut(BaseModel):
    blocks: list[InfoBlock]


def _load_blocks(db: Session) -> list[InfoBlock]:
    row = db.query(Setting).filter(Setting.key == INFO_SETTING_KEY).first()
    if row is not None:
        try:
            raw = json.loads(row.value)
            return [InfoBlock(**b) for b in raw]
        except (ValueError, TypeError):
            pass
    return [InfoBlock(**b) for b in DEFAULT_BLOCKS]


@router.get("", response_model=InfoOut)
def get_info(db: Session = Depends(get_db)):
    return InfoOut(blocks=_load_blocks(db))


@admin_router.put("", response_model=InfoOut)
def set_info(data: InfoOut, db: Session = Depends(get_db)):
    if not data.blocks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужен хотя бы один блок")
    row = db.query(Setting).filter(Setting.key == INFO_SETTING_KEY).first()
    if row is None:
        row = Setting(key=INFO_SETTING_KEY, value="[]")
        db.add(row)
    row.value = json.dumps([b.model_dump() for b in data.blocks], ensure_ascii=False)
    db.commit()
    return InfoOut(blocks=_load_blocks(db))
