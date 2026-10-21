from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import Setting

router = APIRouter(prefix="/api/appearance", tags=["appearance"], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix="/api/admin/appearance", tags=["admin-appearance"], dependencies=[Depends(require_role("admin"))])

GAME_BG_KEY = "game_bg_url"
COLLECTION_BG_KEY = "collection_bg_url"

KEYS = {"game_bg": GAME_BG_KEY, "collection_bg": COLLECTION_BG_KEY}


class AppearanceOut(BaseModel):
    game_bg_url: str | None
    collection_bg_url: str | None


def _get_setting(db: Session, key: str) -> str | None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None or not row.value:
        return None
    return row.value


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()


def get_game_bg(db: Session) -> str | None:
    return _get_setting(db, GAME_BG_KEY)


def get_collection_bg(db: Session) -> str | None:
    return _get_setting(db, COLLECTION_BG_KEY)


@router.get("", response_model=AppearanceOut)
def get_appearance(db: Session = Depends(get_db)):
    return AppearanceOut(
        game_bg_url=_get_setting(db, GAME_BG_KEY),
        collection_bg_url=_get_setting(db, COLLECTION_BG_KEY),
    )


@admin_router.post("/{kind}/image")
def admin_upload_appearance(kind: str, file: UploadFile, db: Session = Depends(get_db)):
    if kind not in KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Неизвестный тип картинки")
    from services.uploads import remove_upload, save_upload

    old_url = _get_setting(db, KEYS[kind])
    url = save_upload(file, prefix=f"appearance_{kind}", max_size=1600)
    _set_setting(db, KEYS[kind], url)
    remove_upload(old_url)
    return {"url": url}


@admin_router.delete("/{kind}/image")
def admin_clear_appearance(kind: str, db: Session = Depends(get_db)):
    if kind not in KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Неизвестный тип картинки")
    from services.uploads import remove_upload

    old_url = _get_setting(db, KEYS[kind])
    _set_setting(db, KEYS[kind], "")
    remove_upload(old_url)
    return {"ok": True}
