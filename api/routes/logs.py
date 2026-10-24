from __future__ import annotations
import datetime
import json

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import Log, User
from services.logging_svc import record_log

admin_router = APIRouter(prefix="/api/admin/logs", tags=["admin-logs"], dependencies=[Depends(require_role("admin"))])

client_router = APIRouter(prefix="/api/client-log", tags=["client-logs"])

MAX_LIMIT = 200

CLIENT_LOG_DEDUPE_SECONDS = 60


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


class ClientFileStat(BaseModel):
    name: str = Field(default="", max_length=120)
    size: int = Field(default=0, ge=0, le=10_000_000_000)
    type: str = Field(default="", max_length=60)


class SentFileStat(ClientFileStat):
    compressed: bool = Field(default=False)


class ClientLogIn(BaseModel):
    event: str = Field(max_length=60)
    elapsed_ms: int = Field(default=0, ge=0, le=3_600_000)
    code: str = Field(default="", max_length=40)
    task_id: int | None = None
    files: list[ClientFileStat] = Field(default_factory=list, max_length=10)
    sent: list[SentFileStat] = Field(default_factory=list, max_length=10)
    uploaded_bytes: int = Field(default=0, ge=0, le=10_000_000_000)
    attempts: int = Field(default=1, ge=1, le=10)


def _fmt_size(total: int) -> str:
    if total >= 1_048_576:
        return f"{total / 1_048_576:.1f} МБ"
    if total >= 1024:
        return f"{total // 1024} КБ"
    return f"{total} Б"


@client_router.post("")
def post_client_log(
    data: ClientLogIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recent = (
        db.query(Log)
        .filter(
            Log.user_id == user.vk_id,
            Log.source == "client",
            Log.event == data.event,
            Log.created_at >= datetime.datetime.utcnow() - datetime.timedelta(seconds=CLIENT_LOG_DEDUPE_SECONDS),
        )
        .first()
    )
    if recent is None:
        total = sum(f.size for f in data.files)
        formats = "/".join(sorted({f.type or "?" for f in data.files})) or "нет файлов"
        sent_total = sum(f.size for f in data.sent)
        sent_note = f", на провод {_fmt_size(sent_total)}" if data.sent else ""
        fallback = sum(1 for f in data.sent if not f.compressed)
        fallback_note = f", откат сжатия: {fallback}" if data.sent and fallback else ""
        record_log(
            source="client", level="warn", event=data.event,
            method="POST", path="/api/client-log",
            message=(
                f"Клиент не смог отправить отчёт: {len(data.files)} файл(ов), "
                f"{_fmt_size(total)}, {formats}, {data.elapsed_ms} мс, код {data.code or 'нет'}, "
                f"попыток {data.attempts}, загружено {_fmt_size(data.uploaded_bytes)}{sent_note}{fallback_note}"
            ),
            details={
                "files": [f.model_dump() for f in data.files],
                "sent": [f.model_dump() for f in data.sent],
                "uploaded_bytes": data.uploaded_bytes,
                "attempts": data.attempts,
                "elapsed_ms": data.elapsed_ms,
                "code": data.code,
                "task_id": data.task_id,
                "user_agent": request.headers.get("user-agent", "")[:250],
            },
            user_id=user.vk_id,
            client_ip=request.client.host if request.client else None,
            session_factory=getattr(request.app.state, "session_factory", None),
        )
    return {"ok": True}


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
