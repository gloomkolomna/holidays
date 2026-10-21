from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from db import get_db
from models import User
from services.auth import create_access_token
from services.game_access import is_game_open
from services.vk_sign import verify_launch_params

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SessionRequest(BaseModel):
    params: dict


class SessionResponse(BaseModel):
    token: str
    vk_id: int
    role: str


@router.post("/session", response_model=SessionResponse)
def create_session(req: SessionRequest, db: Session = Depends(get_db)):
    vk_id = verify_launch_params(req.params)
    if vk_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная подпись")

    user = db.query(User).filter(User.vk_id == vk_id).first()
    is_admin = vk_id in config.get_admin_vk_ids()

    if not is_admin and not is_game_open(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "game_closed", "message": "Игра ещё не открыта — совсем скоро!"},
        )

    if not is_admin and config.MEMBER_GATE_ENABLED:
        from services.vk_group_member import fetch_is_member, get_membership

        if user is None:
            if fetch_is_member(vk_id) is False:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "members_only", "message": "Игра доступна только подписчикам группы"},
                )
        elif not get_membership(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "members_only", "message": "Игра доступна только подписчикам группы"},
            )

    if user is None:
        user = User(vk_id=vk_id, role="admin" if is_admin else "player")
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.role != "admin" and user.status == "blocked":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт заблокирован")
        if is_admin and user.role != "admin":
            user.role = "admin"
            db.commit()
            db.refresh(user)

    if not user.display_name:
        try:
            from services.vk_names import resolve_vk_names

            nm = resolve_vk_names([user.vk_id]).get(user.vk_id, {})
            full = f"{nm.get('first_name', '')} {nm.get('last_name', '')}".strip()
        except Exception:
            full = ""
        if full:
            user.display_name = full
            db.commit()

    token = create_access_token(user.vk_id)
    return SessionResponse(token=token, vk_id=user.vk_id, role=user.role)
