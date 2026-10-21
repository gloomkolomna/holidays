from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import Holiday, HolidayCard, HolidayCategory
from services.cards_grid import ensure_card_slots, holiday_days
from services.msk_time import now_msk

router = APIRouter(prefix="/api/holidays", tags=["holidays"], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix="/api/admin/holidays", tags=["admin-holidays"], dependencies=[Depends(require_role("admin"))])


def _status(holiday: Holiday) -> str:
    now = now_msk().replace(tzinfo=None)
    if now < holiday.starts_at:
        return "upcoming"
    if now >= holiday.ends_at:
        return "finished"
    return "active"


class HolidayCardOut(BaseModel):
    id: int
    category_id: int
    day: str | None
    is_trophy: bool
    title: str
    task_text: str | None
    image_url: str | None
    norm_crosses: int


class HolidayCategoryOut(BaseModel):
    id: int
    title: str
    norm_crosses: int
    cards_count: int


class HolidayCategoryDetailOut(HolidayCategoryOut):
    cards: list[HolidayCardOut]


class HolidayOut(BaseModel):
    id: int
    title: str
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    bg_image_url: str | None
    bg_color: str | None
    palette: str | None
    animation_preset: str | None
    animation_url: str | None
    animation_size: int
    animation_count: int
    animation_opacity: int
    audio_url: str | None
    trophy_image_url: str | None
    shop_enabled: bool
    status: str
    days: list[str]
    categories_count: int
    cards_count: int


class HolidayDetailOut(HolidayOut):
    categories: list[HolidayCategoryDetailOut]


class HolidayCategoryIn(BaseModel):
    title: str
    norm_crosses: int = 1000


class HolidayCardIn(BaseModel):
    title: str = ""
    task_text: str | None = None
    is_trophy: bool = False


class HolidayExtraCardIn(BaseModel):
    category_id: int | None = None
    title: str
    task_text: str | None = None
    is_trophy: bool = False


class HolidayIn(BaseModel):
    title: str
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    bg_image_url: str | None = None
    bg_color: str | None = None
    palette: str | None = None
    animation_preset: str | None = None
    animation_size: int = 50
    animation_count: int = 14
    animation_opacity: int = 100
    shop_enabled: bool = True


def _card_out(card: HolidayCard) -> HolidayCardOut:
    return HolidayCardOut(
        id=card.id,
        category_id=card.category_id,
        day=card.day,
        is_trophy=bool(card.is_trophy),
        title=card.title,
        task_text=card.task_text,
        image_url=card.image_url,
        norm_crosses=card.category.norm_crosses if card.category else 0,
    )


def _category_summary(cat: HolidayCategory, filled_only: bool) -> HolidayCategoryOut:
    cards = [c for c in cat.cards if c.title.strip()] if filled_only else list(cat.cards)
    return HolidayCategoryOut(
        id=cat.id,
        title=cat.title,
        norm_crosses=cat.norm_crosses,
        cards_count=len(cards),
    )


def _category_detail(cat: HolidayCategory, filled_only: bool) -> HolidayCategoryDetailOut:
    cards = [c for c in cat.cards if c.title.strip()] if filled_only else list(cat.cards)
    return HolidayCategoryDetailOut(
        **_category_summary(cat, filled_only).model_dump(),
        cards=[_card_out(c) for c in cards],
    )


def _summary(holiday: Holiday, filled_only: bool) -> HolidayOut:
    cards = [c for cat in holiday.categories for c in cat.cards if c.title.strip()] if filled_only else None
    cards_count = len(cards) if cards is not None else sum(len(cat.cards) for cat in holiday.categories)
    return HolidayOut(
        id=holiday.id,
        title=holiday.title,
        starts_at=holiday.starts_at,
        ends_at=holiday.ends_at,
        bg_image_url=holiday.bg_image_url,
        bg_color=holiday.bg_color,
        palette=holiday.palette,
        animation_preset=holiday.animation_preset,
        animation_url=holiday.animation_url,
        animation_size=holiday.animation_size,
        animation_count=holiday.animation_count,
        animation_opacity=holiday.animation_opacity,
        audio_url=holiday.audio_url,
        trophy_image_url=holiday.trophy_image_url,
        shop_enabled=bool(holiday.shop_enabled),
        status=_status(holiday),
        days=holiday_days(holiday),
        categories_count=len(holiday.categories),
        cards_count=cards_count,
    )


def _detail(holiday: Holiday, filled_only: bool) -> HolidayDetailOut:
    return HolidayDetailOut(
        **_summary(holiday, filled_only).model_dump(),
        categories=[_category_detail(cat, filled_only) for cat in holiday.categories],
    )


def _validate(data: HolidayIn) -> tuple[datetime.datetime, datetime.datetime]:
    """Проверяет праздник и возвращает границы: С — 00:00:00, ПО — 23:59:59 (МСК).

    Время из запроса игнорируется: праздник всегда начинается в полночь
    и заканчивается в последнюю секунду дня.
    """
    starts = data.starts_at.replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
    ends = data.ends_at.replace(tzinfo=None).replace(hour=23, minute=59, second=59, microsecond=0)
    if ends < starts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата окончания должна быть не раньше даты начала")
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название праздника обязательно")
    if not 10 <= data.animation_size <= 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Размер анимации должен быть от 10 до 100%")
    if not 1 <= data.animation_count <= 40:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Количество объектов анимации должно быть от 1 до 40")
    if not 10 <= data.animation_opacity <= 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Прозрачность анимации должна быть от 10 до 100%")
    return starts, ends


def _get_holiday(db: Session, holiday_id: int) -> Holiday:
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Праздник не найден")
    return holiday


def _get_category(db: Session, holiday_id: int, category_id: int) -> HolidayCategory:
    cat = (
        db.query(HolidayCategory)
        .filter(HolidayCategory.id == category_id, HolidayCategory.holiday_id == holiday_id)
        .first()
    )
    if cat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    return cat


@router.get("", response_model=list[HolidayOut])
def list_holidays(db: Session = Depends(get_db)):
    holidays = db.query(Holiday).order_by(Holiday.starts_at.desc()).all()
    return [_summary(h, filled_only=True) for h in holidays]


@router.get("/active", response_model=HolidayDetailOut)
def get_active_holiday(db: Session = Depends(get_db)):
    now = now_msk().replace(tzinfo=None)
    holiday = (
        db.query(Holiday)
        .filter(Holiday.starts_at <= now, Holiday.ends_at > now)
        .order_by(Holiday.starts_at.asc())
        .first()
    )
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного праздника")
    return _detail(holiday, filled_only=True)


@router.get("/{holiday_id}", response_model=HolidayDetailOut)
def get_holiday(holiday_id: int, db: Session = Depends(get_db)):
    return _detail(_get_holiday(db, holiday_id), filled_only=True)


@admin_router.get("", response_model=list[HolidayOut])
def admin_list_holidays(
    holiday_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    holidays = db.query(Holiday).order_by(Holiday.starts_at.desc()).all()
    out = [_summary(h, filled_only=False) for h in holidays]
    if holiday_status:
        out = [h for h in out if h.status == holiday_status]
    return out


@admin_router.post("", response_model=HolidayDetailOut)
def admin_create_holiday(data: HolidayIn, db: Session = Depends(get_db)):
    starts, ends = _validate(data)
    holiday = Holiday(
        title=data.title.strip(),
        starts_at=starts,
        ends_at=ends,
        bg_image_url=data.bg_image_url,
        bg_color=data.bg_color if (data.bg_color or "").strip() else None,
        palette=data.palette,
        animation_preset=data.animation_preset,
        animation_size=data.animation_size,
        animation_count=data.animation_count,
        animation_opacity=data.animation_opacity,
        shop_enabled=data.shop_enabled,
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    ensure_card_slots(db, holiday)
    return _detail(holiday, filled_only=False)


@admin_router.get("/{holiday_id}", response_model=HolidayDetailOut)
def admin_get_holiday(holiday_id: int, db: Session = Depends(get_db)):
    return _detail(_get_holiday(db, holiday_id), filled_only=False)


@admin_router.put("/{holiday_id}", response_model=HolidayDetailOut)
def admin_update_holiday(holiday_id: int, data: HolidayIn, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    starts, ends = _validate(data)
    holiday.title = data.title.strip()
    holiday.starts_at = starts
    holiday.ends_at = ends
    holiday.bg_image_url = data.bg_image_url
    holiday.bg_color = data.bg_color if (data.bg_color or "").strip() else None
    holiday.palette = data.palette
    holiday.animation_preset = data.animation_preset
    holiday.animation_size = data.animation_size
    holiday.animation_count = data.animation_count
    holiday.animation_opacity = data.animation_opacity
    holiday.shop_enabled = data.shop_enabled
    db.commit()
    db.refresh(holiday)
    ensure_card_slots(db, holiday)
    return _detail(holiday, filled_only=False)


@admin_router.post("/{holiday_id}/bg-image")
def admin_upload_holiday_bg(holiday_id: int, file: UploadFile, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload, save_upload

    old_url = holiday.bg_image_url
    holiday.bg_image_url = save_upload(file, prefix=f"holiday_{holiday_id}_bg", max_size=1600)
    db.commit()
    remove_upload(old_url)
    return {"bg_image_url": holiday.bg_image_url}


@admin_router.post("/{holiday_id}/animation")
def admin_upload_holiday_animation(holiday_id: int, file: UploadFile, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload, save_silhouette_upload

    old_url = holiday.animation_url
    holiday.animation_url = save_silhouette_upload(file, prefix=f"holiday_{holiday_id}_anim")
    db.commit()
    remove_upload(old_url)
    return {"animation_url": holiday.animation_url}


@admin_router.delete("/{holiday_id}/animation")
def admin_clear_holiday_animation(holiday_id: int, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload

    old_url = holiday.animation_url
    holiday.animation_url = None
    db.commit()
    remove_upload(old_url)
    return {"ok": True}


@admin_router.post("/{holiday_id}/audio")
def admin_upload_holiday_audio(holiday_id: int, file: UploadFile, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload, save_audio_upload

    old_url = holiday.audio_url
    holiday.audio_url = save_audio_upload(file, prefix=f"holiday_{holiday_id}_audio")
    db.commit()
    remove_upload(old_url)
    return {"audio_url": holiday.audio_url}


@admin_router.delete("/{holiday_id}/audio")
def admin_clear_holiday_audio(holiday_id: int, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload

    old_url = holiday.audio_url
    holiday.audio_url = None
    db.commit()
    remove_upload(old_url)
    return {"ok": True}


@admin_router.delete("/{holiday_id}")
def admin_delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    db.delete(holiday)
    db.commit()
    return {"ok": True}


@admin_router.post("/{holiday_id}/categories", response_model=HolidayCategoryDetailOut)
def admin_create_category(holiday_id: int, data: HolidayCategoryIn, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название категории обязательно")
    if data.norm_crosses <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Норма крестиков должна быть положительным числом")
    cat = HolidayCategory(holiday_id=holiday.id, title=data.title.strip(), norm_crosses=data.norm_crosses)
    db.add(cat)
    db.commit()
    db.refresh(holiday)
    ensure_card_slots(db, holiday)
    for c in holiday.categories:
        if c.id == cat.id:
            return _category_detail(c, filled_only=False)
    return _category_detail(cat, filled_only=False)


@admin_router.put("/{holiday_id}/categories/{category_id}", response_model=HolidayCategoryOut)
def admin_update_category(holiday_id: int, category_id: int, data: HolidayCategoryIn, db: Session = Depends(get_db)):
    cat = _get_category(db, holiday_id, category_id)
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название категории обязательно")
    if data.norm_crosses <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Норма крестиков должна быть положительным числом")
    cat.title = data.title.strip()
    cat.norm_crosses = data.norm_crosses
    db.commit()
    db.refresh(cat)
    return _category_summary(cat, filled_only=False)


@admin_router.post("/{holiday_id}/extra-cards", response_model=HolidayCardOut)
def admin_create_extra_card(holiday_id: int, data: HolidayExtraCardIn, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    if data.category_id is not None:
        cat = _get_category(db, holiday_id, data.category_id)
    else:
        cat = holiday.categories[0] if holiday.categories else None
    if cat is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сначала создайте категорию")
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название карточки обязательно")
    card = HolidayCard(
        holiday_id=holiday_id,
        category_id=cat.id,
        day=None,
        is_trophy=bool(data.is_trophy),
        title=data.title.strip(),
        task_text=(data.task_text or "").strip() or None,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_out(card)


@admin_router.delete("/{holiday_id}/cards/{card_id}")
def admin_delete_card(holiday_id: int, card_id: int, db: Session = Depends(get_db)):
    card = _get_card(db, holiday_id, card_id)
    if card.day is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Слоты сетки дней удаляются сменой дат праздника")
    from services.uploads import remove_upload

    url = card.image_url
    db.delete(card)
    db.commit()
    remove_upload(url)
    return {"ok": True}


@admin_router.post("/{holiday_id}/trophy-image")
def admin_upload_trophy_image(holiday_id: int, file: UploadFile, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload, save_silhouette_upload

    old_url = holiday.trophy_image_url
    holiday.trophy_image_url = save_silhouette_upload(file, prefix=f"holiday_{holiday_id}_trophy")
    db.commit()
    remove_upload(old_url)
    return {"trophy_image_url": holiday.trophy_image_url}


@admin_router.delete("/{holiday_id}/trophy-image")
def admin_clear_trophy_image(holiday_id: int, db: Session = Depends(get_db)):
    holiday = _get_holiday(db, holiday_id)
    from services.uploads import remove_upload

    old_url = holiday.trophy_image_url
    holiday.trophy_image_url = None
    db.commit()
    remove_upload(old_url)
    return {"ok": True}


@admin_router.delete("/{holiday_id}/categories/{category_id}")
def admin_delete_category(holiday_id: int, category_id: int, db: Session = Depends(get_db)):
    cat = _get_category(db, holiday_id, category_id)
    from services.uploads import remove_upload

    urls = [c.image_url for c in cat.cards]
    db.delete(cat)
    db.commit()
    for url in urls:
        remove_upload(url)
    return {"ok": True}


def _get_card(db: Session, holiday_id: int, card_id: int) -> HolidayCard:
    card = (
        db.query(HolidayCard)
        .filter(HolidayCard.id == card_id, HolidayCard.holiday_id == holiday_id)
        .first()
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")
    return card


@admin_router.put("/{holiday_id}/cards/{card_id}", response_model=HolidayCardOut)
def admin_update_card(holiday_id: int, card_id: int, data: HolidayCardIn, db: Session = Depends(get_db)):
    card = _get_card(db, holiday_id, card_id)
    card.title = data.title.strip()
    card.task_text = (data.task_text or "").strip() or None
    if card.day is not None:
        card.is_trophy = False
    else:
        card.is_trophy = bool(data.is_trophy)
    db.commit()
    db.refresh(card)
    return _card_out(card)


@admin_router.post("/{holiday_id}/cards/{card_id}/image")
def admin_upload_card_image(holiday_id: int, card_id: int, file: UploadFile, db: Session = Depends(get_db)):
    card = _get_card(db, holiday_id, card_id)
    from services.uploads import remove_upload, save_upload

    old_url = card.image_url
    card.image_url = save_upload(file, prefix=f"card_{holiday_id}", max_size=800)
    db.commit()
    remove_upload(old_url)
    return {"image_url": card.image_url}


@admin_router.delete("/{holiday_id}/cards/{card_id}/image")
def admin_clear_card_image(holiday_id: int, card_id: int, db: Session = Depends(get_db)):
    card = _get_card(db, holiday_id, card_id)
    from services.uploads import remove_upload

    url = card.image_url
    card.image_url = None
    db.commit()
    remove_upload(url)
    return {"ok": True}
