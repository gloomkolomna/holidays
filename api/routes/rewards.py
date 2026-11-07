from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import (
    CollectionReward,
    Holiday,
    HolidayCard,
    HolidayCategory,
    RewardItem,
    RewardPurchase,
    Task,
    User,
    UserCard,
)
from services.cards_grid import get_active_holiday
from services.reward_effects import active_effect, active_task_count, shop_open
from services.reward_integrations import IntegrationError, apply_external_reward, revoke_external_reward
from services.reward_presets import config_dict, config_json, ensure_reward_presets

router = APIRouter(prefix="/api/rewards", tags=["rewards"], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix="/api/admin/rewards", tags=["admin-rewards"], dependencies=[Depends(require_role("admin"))])


class TrophyOut(BaseModel):
    holiday_id: int
    title: str
    category_id: int
    category_title: str
    crystals: int
    trophy_image_url: str | None
    awarded_at: str


class RewardItemOut(BaseModel):
    id: int
    preset_key: str | None
    effect_type: str
    effect_config: dict
    title: str
    description: str | None
    image_url: str | None
    price_crystals: int
    is_active: bool


class PurchaseOut(BaseModel):
    id: int
    item_id: int | None
    item_title: str
    status: str
    effect_type: str
    effect_config: dict
    created_at: str
    used_at: str | None
    target_card_id: int | None
    target_task_id: int | None
    external_reference: str | None
    last_error: str | None


class RewardsOut(BaseModel):
    crystals: int
    trophies: list[TrophyOut]
    items: list[RewardItemOut]
    purchases: list[PurchaseOut]


class RewardItemIn(BaseModel):
    title: str
    description: str | None = None
    price_crystals: int = 1
    is_active: bool = True
    effect_config: dict | None = None


class BuyIn(BaseModel):
    item_id: int


class UseIn(BaseModel):
    card_id: int | None = None
    task_id: int | None = None


def _item_out(item: RewardItem) -> RewardItemOut:
    return RewardItemOut(
        id=item.id,
        preset_key=item.preset_key,
        effect_type=item.effect_type,
        effect_config=config_dict(item.effect_config),
        title=item.title,
        description=item.description,
        image_url=item.image_url,
        price_crystals=item.price_crystals,
        is_active=item.is_active,
    )


def _purchase_out(purchase: RewardPurchase, item: RewardItem | None) -> PurchaseOut:
    return PurchaseOut(
        id=purchase.id,
        item_id=purchase.item_id,
        item_title=purchase.item_title or (item.title if item else "Награда"),
        status=purchase.status,
        effect_type=item.effect_type if item else "",
        effect_config=config_dict(purchase.effect_payload),
        created_at=purchase.created_at.isoformat(),
        used_at=purchase.used_at.isoformat() if purchase.used_at else None,
        target_card_id=purchase.target_card_id,
        target_task_id=purchase.target_task_id,
        external_reference=purchase.external_reference,
        last_error=purchase.last_error,
    )


def _own_purchase(db: Session, purchase_id: int, user_id: int):
    purchase = db.query(RewardPurchase).filter(
        RewardPurchase.id == purchase_id,
        RewardPurchase.user_id == user_id,
    ).first()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Награда не найдена")
    item = db.query(RewardItem).filter(RewardItem.id == purchase.item_id).first() if purchase.item_id else None
    return purchase, item


@router.get("", response_model=RewardsOut)
def get_rewards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_reward_presets(db)
    me = db.query(User).filter(User.vk_id == user.vk_id).first() or user
    trophies = (
        db.query(CollectionReward, Holiday, HolidayCategory)
        .join(Holiday, Holiday.id == CollectionReward.holiday_id)
        .join(HolidayCategory, HolidayCategory.id == CollectionReward.category_id)
        .filter(CollectionReward.user_id == user.vk_id)
        .order_by(CollectionReward.awarded_at.desc())
        .all()
    )
    items = db.query(RewardItem).filter(
        RewardItem.is_active.is_(True),
        RewardItem.preset_key.isnot(None),
    ).order_by(RewardItem.id).all()
    purchases = db.query(RewardPurchase).filter(
        RewardPurchase.user_id == user.vk_id,
    ).order_by(RewardPurchase.created_at.desc(), RewardPurchase.id.desc()).all()
    items_by_id = {item.id: item for item in db.query(RewardItem).all()}

    return RewardsOut(
        crystals=me.crystals or 0,
        trophies=[
            TrophyOut(
                holiday_id=cr.holiday_id,
                title=h.title,
                category_id=cr.category_id,
                category_title=cat.title,
                crystals=cr.crystals,
                trophy_image_url=cat.trophy_image_url,
                awarded_at=cr.awarded_at.isoformat(),
            )
            for cr, h, cat in trophies
        ],
        items=[_item_out(item) for item in items],
        purchases=[_purchase_out(purchase, items_by_id.get(purchase.item_id)) for purchase in purchases],
    )


@router.post("/buy")
def buy_item(data: BuyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_reward_presets(db)
    item = db.query(RewardItem).filter(
        RewardItem.id == data.item_id,
        RewardItem.preset_key.isnot(None),
    ).first()
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="Награда не найдена")
    row = db.query(User).filter(User.vk_id == user.vk_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if (row.crystals or 0) < item.price_crystals:
        raise HTTPException(
            status_code=400,
            detail=f"Не хватает кристаллов: нужно {item.price_crystals}, у вас {row.crystals or 0}",
        )

    debited = db.execute(
        update(User)
        .where(User.vk_id == user.vk_id, User.crystals >= item.price_crystals)
        .values(crystals=User.crystals - item.price_crystals)
    )
    if debited.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Не хватает кристаллов")
    purchase = RewardPurchase(
        user_id=user.vk_id,
        item_id=item.id,
        item_title=item.title,
        status="available",
        effect_payload=item.effect_config,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    db.refresh(row)
    return {"ok": True, "purchase_id": purchase.id, "crystals_left": row.crystals}


@router.post("/purchases/{purchase_id}/use")
def use_reward(purchase_id: int, data: UseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_reward_presets(db)
    purchase, item = _own_purchase(db, purchase_id, user.vk_id)
    if item is None:
        raise HTTPException(status_code=409, detail="Эта награда из старой лавки и не имеет игрового эффекта")
    if purchase.status != "available":
        raise HTTPException(status_code=409, detail="Награда уже применена или обнулена")
    effect = item.effect_type
    payload = config_dict(purchase.effect_payload)

    if effect.startswith("external_"):
        try:
            result = apply_external_reward(effect, purchase.id, user.vk_id, payload)
        except IntegrationError as exc:
            purchase.last_error = str(exc)
            db.commit()
            raise HTTPException(status_code=502, detail=str(exc))
        purchase.status = "used"
        purchase.external_reference = config_json(result)
        purchase.last_error = None
        purchase.used_at = datetime.datetime.utcnow()
        db.commit()
        return {"ok": True, "status": purchase.status, "result": result}

    if effect == "reduce_penalty":
        query = db.query(Task).filter(
            Task.user_id == user.vk_id,
            Task.status == "active",
            Task.kind == "penalty",
        )
        if data.task_id is not None:
            query = query.filter(Task.id == data.task_id)
        task = query.first()
        if task is None:
            raise HTTPException(status_code=409, detail="У вас нет активного штрафного задания")
        percent = payload.get("percent", 50)
        task.required_crosses = max(1, (task.required_crosses * (100 - percent) + 99) // 100)
        purchase.target_task_id = task.id
        purchase.status = "used"

    elif effect == "extra_active_task":
        if active_task_count(db, user.vk_id) >= 2:
            raise HTTPException(status_code=409, detail="У вас уже два активных задания")
        if active_effect(db, user.vk_id, "extra_active_task"):
            raise HTTPException(status_code=409, detail="Дополнительное задание уже доступно")
        purchase.status = "active"

    elif effect in ("shop_always_open", "shop_without_penalty"):
        if get_active_holiday(db) is not None:
            raise HTTPException(status_code=409, detail="Эту награду можно применить только между праздниками")
        if active_effect(db, user.vk_id, effect):
            raise HTTPException(status_code=409, detail="Такой эффект уже действует")
        purchase.status = "active"

    elif effect == "complete_shop_card":
        opened, reason = shop_open(db, user.vk_id)
        if not opened:
            detail = "Магазин сейчас закрыт"
            if reason == "holiday_active":
                detail = "Магазин закрыт во время праздника"
            raise HTTPException(status_code=409, detail=detail)
        card = db.query(HolidayCard).filter(HolidayCard.id == data.card_id).first()
        if card is None or not card.title.strip() or card.category is None:
            raise HTTPException(status_code=404, detail="Карточка не найдена")
        holiday = db.query(Holiday).filter(Holiday.id == card.holiday_id).first()
        now = __import__("services.msk_time", fromlist=["now_msk"]).now_msk().replace(tzinfo=None)
        if holiday is None or now < holiday.ends_at or not holiday.shop_enabled:
            raise HTTPException(status_code=400, detail="Эта карточка недоступна в магазине")
        if db.query(UserCard).filter(UserCard.user_id == user.vk_id, UserCard.card_id == card.id).first():
            raise HTTPException(status_code=409, detail="Эта карточка уже в коллекции")
        db.add(UserCard(user_id=user.vk_id, card_id=card.id, source="reward"))
        db.flush()
        from services.rewards import ensure_collection_reward
        ensure_collection_reward(db, user.vk_id, card.category_id)
        purchase.target_card_id = card.id
        purchase.status = "used"

    else:
        raise HTTPException(status_code=400, detail="Неизвестный эффект награды")

    purchase.used_at = datetime.datetime.utcnow() if purchase.status == "used" else None
    purchase.last_error = None
    db.commit()
    return {"ok": True, "status": purchase.status}


@admin_router.get("/items", response_model=list[RewardItemOut])
def admin_items(db: Session = Depends(get_db)):
    ensure_reward_presets(db)
    return [_item_out(item) for item in db.query(RewardItem).filter(RewardItem.preset_key.isnot(None)).order_by(RewardItem.id).all()]


@admin_router.put("/items/{item_id}", response_model=RewardItemOut)
def admin_update_item(item_id: int, data: RewardItemIn, db: Session = Depends(get_db)):
    ensure_reward_presets(db)
    item = db.query(RewardItem).filter(RewardItem.id == item_id, RewardItem.preset_key.isnot(None)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Пресет не найден")
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Название награды обязательно")
    if data.price_crystals <= 0:
        raise HTTPException(status_code=400, detail="Цена должна быть положительной")
    if data.effect_config is not None and item.effect_type == "external_zakaz_discount":
        percent = data.effect_config.get("percent")
        if not isinstance(percent, int) or not 1 <= percent <= 99:
            raise HTTPException(status_code=400, detail="Скидка должна быть от 1 до 99 процентов")
        item.effect_config = config_json({"percent": percent})
    item.title = data.title.strip()
    item.description = data.description
    item.price_crystals = data.price_crystals
    item.is_active = data.is_active
    db.commit()
    db.refresh(item)
    return _item_out(item)


@admin_router.post("/items/{item_id}/image")
def admin_upload_item_image(item_id: int, file: UploadFile, db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == item_id, RewardItem.preset_key.isnot(None)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Пресет не найден")
    from services.uploads import remove_upload, save_upload
    old_url = item.image_url
    item.image_url = save_upload(file, prefix=f"reward_{item_id}", max_size=800)
    db.commit()
    remove_upload(old_url)
    return {"image_url": item.image_url}


@admin_router.get("/purchases")
def admin_purchases(db: Session = Depends(get_db)):
    purchases = db.query(RewardPurchase).order_by(RewardPurchase.created_at.desc(), RewardPurchase.id.desc()).limit(500).all()
    items = {item.id: item for item in db.query(RewardItem).all()}
    users = {user.vk_id: user for user in db.query(User).all()}
    return [
        {
            **_purchase_out(purchase, items.get(purchase.item_id)).model_dump(),
            "user_id": purchase.user_id,
            "display_name": users.get(purchase.user_id).display_name if users.get(purchase.user_id) else None,
        }
        for purchase in purchases
    ]


@admin_router.post("/purchases/{purchase_id}/revoke")
def admin_revoke_purchase(purchase_id: int, db: Session = Depends(get_db)):
    purchase = db.query(RewardPurchase).filter(RewardPurchase.id == purchase_id).first()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Награда не найдена")
    if purchase.status == "revoked":
        return {"ok": True, "status": "revoked"}
    item = db.query(RewardItem).filter(RewardItem.id == purchase.item_id).first() if purchase.item_id else None
    if item is None or purchase.status == "used":
        if item and item.effect_type.startswith("external_") and purchase.external_reference:
            try:
                revoke_external_reward(item.effect_type, purchase.id)
            except IntegrationError as exc:
                purchase.last_error = str(exc)
                db.commit()
                raise HTTPException(status_code=502, detail=str(exc))
        else:
            raise HTTPException(status_code=409, detail="Использованную награду нельзя обнулить")
    purchase.status = "revoked"
    purchase.used_at = datetime.datetime.utcnow()
    purchase.last_error = None
    db.commit()
    return {"ok": True, "status": "revoked"}
