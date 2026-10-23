from __future__ import annotations
import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import require_role
from models import Log

admin_router = APIRouter(prefix="/api/admin/logs", tags=["admin-logs"], dependencies=[Depends(require_role("admin"))])

MAX_LIMIT = 200


class LogOut(BaseModel):
    id: int
    source: str
    level: str
    event: str | None
    method: str | None
    path: str | None
    status_code: int | None
    message: str | None
    details: dict | None
    user_id: int | None
    created_at: str


def _parse_details(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return {"raw": raw}
    return value if isinstance(value, dict) else {"raw": raw}


@admin_router.get("", response_model=list[LogOut])
def admin_logs(
    level: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
):
    q = db.query(Log).order_by(Log.created_at.desc(), Log.id.desc())
    if level:
        q = q.filter(Log.level == level)
    rows = q.limit(limit).all()
    return [
        LogOut(
            id=row.id,
            source=row.source,
            level=row.level,
            event=row.event,
            method=row.method,
            path=row.path,
            status_code=row.status_code,
            message=row.message,
            details=_parse_details(row.details),
            user_id=row.user_id,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]
