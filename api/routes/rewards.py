from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user, require_role
from models import CollectionReward, Holiday, HolidayCategory, RewardCode, RewardItem, RewardPurchase, User

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
    title: str
    description: str | None
    image_url: str | None
    price_crystals: int
    codes_available: int


class PurchaseOut(BaseModel):
    id: int
    item_title: str
    code: str
    created_at: str


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


class CodesIn(BaseModel):
    codes: list[str]


def _available_codes(db: Session, item_id: int) -> int:
    return (
        db.query(RewardCode)
        .filter(RewardCode.item_id == item_id, RewardCode.taken_by.is_(None))
        .count()
    )


@router.get("", response_model=RewardsOut)
def get_rewards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = db.query(User).filter(User.vk_id == user.vk_id).first() or user
    trophies = (
        db.query(CollectionReward, Holiday, HolidayCategory)
        .join(Holiday, Holiday.id == CollectionReward.holiday_id)
        .join(HolidayCategory, HolidayCategory.id == CollectionReward.category_id)
        .filter(CollectionReward.user_id == user.vk_id)
        .order_by(CollectionReward.awarded_at.desc())
        .all()
    )

    items = db.query(RewardItem).filter(RewardItem.is_active.is_(True)).order_by(RewardItem.id).all()

    purchases = (
        db.query(RewardPurchase, RewardItem, RewardCode)
        .join(RewardItem, RewardItem.id == RewardPurchase.item_id)
        .join(RewardCode, RewardCode.id == RewardPurchase.code_id)
        .filter(RewardPurchase.user_id == user.vk_id)
        .order_by(RewardPurchase.created_at.desc())
        .all()
    )

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
        items=[
            RewardItemOut(
                id=i.id,
                title=i.title,
                description=i.description,
                image_url=i.image_url,
                price_crystals=i.price_crystals,
                codes_available=_available_codes(db, i.id),
            )
            for i in items
        ],
        purchases=[
            PurchaseOut(
                id=p.id,
                item_title=i.title,
                code=c.code,
                created_at=p.created_at.isoformat(),
            )
            for p, i, c in purchases
        ],
    )


class BuyIn(BaseModel):
    item_id: int


@router.post("/buy")
def buy_item(data: BuyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == data.item_id).first()
    if item is None or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

    row = db.query(User).filter(User.vk_id == user.vk_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if (row.crystals or 0) < item.price_crystals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не хватает кристаллов: нужно {item.price_crystals}, у вас {row.crystals or 0}",
        )

    code = (
        db.query(RewardCode)
        .filter(RewardCode.item_id == item.id, RewardCode.taken_by.is_(None))
        .order_by(RewardCode.id)
        .first()
    )
    if code is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Товар распродан — кодов больше нет")

    row.crystals = row.crystals - item.price_crystals
    code.taken_by = user.vk_id
    code.taken_at = datetime.datetime.utcnow()
    purchase = RewardPurchase(user_id=user.vk_id, item_id=item.id, code_id=code.id)
    db.add(purchase)
    db.commit()

    return {
        "ok": True,
        "purchase_id": purchase.id,
        "code": code.code,
        "crystals_left": row.crystals,
    }


@admin_router.get("/items", response_model=list[RewardItemOut])
def admin_items(db: Session = Depends(get_db)):
    items = db.query(RewardItem).order_by(RewardItem.id).all()
    return [
        RewardItemOut(
            id=i.id,
            title=i.title,
            description=i.description,
            image_url=i.image_url,
            price_crystals=i.price_crystals,
            codes_available=_available_codes(db, i.id),
        )
        for i in items
    ]


@admin_router.post("/items", response_model=RewardItemOut)
def admin_create_item(data: RewardItemIn, db: Session = Depends(get_db)):
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название товара обязательно")
    if data.price_crystals <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Цена должна быть положительной")
    item = RewardItem(
        title=data.title.strip(),
        description=data.description,
        price_crystals=data.price_crystals,
        is_active=data.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return RewardItemOut(
        id=item.id,
        title=item.title,
        description=item.description,
        image_url=item.image_url,
        price_crystals=item.price_crystals,
        codes_available=0,
    )


@admin_router.put("/items/{item_id}", response_model=RewardItemOut)
def admin_update_item(item_id: int, data: RewardItemIn, db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название товара обязательно")
    if data.price_crystals <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Цена должна быть положительной")
    item.title = data.title.strip()
    item.description = data.description
    item.price_crystals = data.price_crystals
    item.is_active = data.is_active
    db.commit()
    db.refresh(item)
    return RewardItemOut(
        id=item.id,
        title=item.title,
        description=item.description,
        image_url=item.image_url,
        price_crystals=item.price_crystals,
        codes_available=_available_codes(db, item.id),
    )


@admin_router.post("/items/{item_id}/image")
def admin_upload_item_image(item_id: int, file: UploadFile, db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    from services.uploads import remove_upload, save_upload

    old_url = item.image_url
    item.image_url = save_upload(file, prefix=f"reward_{item_id}", max_size=800)
    db.commit()
    remove_upload(old_url)
    return {"image_url": item.image_url}


@admin_router.delete("/items/{item_id}")
def admin_delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    db.delete(item)
    db.commit()
    return {"ok": True}


@admin_router.post("/items/{item_id}/codes")
def admin_add_codes(item_id: int, data: CodesIn, db: Session = Depends(get_db)):
    item = db.query(RewardItem).filter(RewardItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    added = 0
    for raw in data.codes:
        code = raw.strip()
        if not code:
            continue
        db.add(RewardCode(item_id=item.id, code=code))
        added += 1
    db.commit()
    return {"added": added, "available": _available_codes(db, item.id)}


@admin_router.get("/items/{item_id}/codes")
def admin_list_codes(item_id: int, db: Session = Depends(get_db)):
    codes = (
        db.query(RewardCode)
        .filter(RewardCode.item_id == item_id)
        .order_by(RewardCode.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": c.id,
            "code": c.code,
            "taken_by": c.taken_by,
            "taken_at": c.taken_at.isoformat() if c.taken_at else None,
        }
        for c in codes
    ]


@admin_router.delete("/codes/{code_id}")
def admin_delete_code(code_id: int, db: Session = Depends(get_db)):
    code = db.query(RewardCode).filter(RewardCode.id == code_id).first()
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Код не найден")
    if code.taken_by is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код уже выдан игроку — удалить нельзя")
    db.delete(code)
    db.commit()
    return {"ok": True}
