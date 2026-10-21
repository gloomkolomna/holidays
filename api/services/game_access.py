from __future__ import annotations

from sqlalchemy.orm import Session

GAME_OPEN_KEY = "game_open"


def is_game_open(db: Session) -> bool:
    from models import Setting

    row = db.query(Setting).filter(Setting.key == GAME_OPEN_KEY).first()
    return row is not None and row.value == "1"


def set_game_open(db: Session, value: bool) -> None:
    from models import Setting

    row = db.query(Setting).filter(Setting.key == GAME_OPEN_KEY).first()
    if row is None:
        db.add(Setting(key=GAME_OPEN_KEY, value="1" if value else "0"))
    else:
        row.value = "1" if value else "0"
    db.commit()
