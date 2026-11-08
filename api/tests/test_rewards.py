from models import CollectionReward, RewardItem, RewardPurchase, User
from services.msk_time import now_msk
from services.rewards import ensure_collection_reward
from tests.conftest import make_user_client
from tests.test_holidays import _multi_day_holiday_payload, _png_bytes
from tests.test_shop import _finished_holiday


def _active_holiday_one_card(admin_client, title="Короткий"):
    payload = _multi_day_holiday_payload(title)
    today = now_msk().replace(tzinfo=None)
    payload["starts_at"] = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    payload["ends_at"] = today.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    hid = admin_client.post("/api/admin/holidays", json=payload).json()["id"]
    cat = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Кат", "norm_crosses": 300}).json()
    slots = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]
    card_id = None
    for slot in slots:
        if slot["day"] == now_msk().date().isoformat():
            card_id = admin_client.put(
                f"/api/admin/holidays/{hid}/cards/{slot['id']}", json={"title": "Единственная"},
            ).json()["id"]
    return hid, cat["id"], card_id


def test_rewards_requires_auth(client):
    assert client.get("/api/rewards").status_code == 401


def test_full_category_awards_crystal_and_trophy(admin_client, db, uploads_tmp):
    hid, cat_id, card_id = _active_holiday_one_card(admin_client)
    extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Магазинная"},
    ).json()
    with make_user_client(123) as player:
        db.add(__import__("models").UserCard(user_id=123, card_id=extra["id"], source="penalty"))
        db.commit()
        task = player.post(f"/api/game/cards/{card_id}/take").json()
        resp = player.post(
            f"/api/game/tasks/{task['id']}/report",
            data={"amount": "300", "mode": "norm"},
            files={
                "photo_before": ("b.png", _png_bytes(), "image/png"),
                "photo_after": ("a.png", _png_bytes(), "image/png"),
            },
        )
        assert resp.status_code == 200
        rewards = player.get("/api/rewards").json()

    assert rewards["crystals"] == 1
    assert len(rewards["trophies"]) == 1
    assert rewards["trophies"][0]["holiday_id"] == hid
    assert rewards["trophies"][0]["category_id"] == cat_id
    assert ensure_collection_reward(db, 123, cat_id) is False
    assert db.query(CollectionReward).filter_by(user_id=123, category_id=cat_id).count() == 1


def test_category_reward_per_category_independent(admin_client, db):
    payload = _multi_day_holiday_payload("Двухразделовый")
    today = now_msk().replace(tzinfo=None)
    payload["starts_at"] = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    payload["ends_at"] = today.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    hid = admin_client.post("/api/admin/holidays", json=payload).json()["id"]
    cat1 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Наряды", "norm_crosses": 500}).json()
    cat2 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Декор", "norm_crosses": 900}).json()
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    by_cat = {c["id"]: c["cards"] for c in detail["categories"]}
    card1 = admin_client.put(f"/api/admin/holidays/{hid}/cards/{by_cat[cat1['id']][0]['id']}", json={"title": "Первая"}).json()
    card2 = admin_client.put(f"/api/admin/holidays/{hid}/cards/{by_cat[cat2['id']][0]['id']}", json={"title": "Вторая"}).json()
    extra1 = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat1["id"], "title": "Магазинная 1"},
    ).json()
    extra2 = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat2["id"], "title": "Магазинная 2"},
    ).json()

    db.add(User(vk_id=555, role="player"))
    db.add(__import__("models").UserCard(user_id=555, card_id=card1["id"]))
    db.add(__import__("models").UserCard(user_id=555, card_id=extra1["id"], source="penalty"))
    db.commit()

    assert ensure_collection_reward(db, 555, cat1["id"]) is True
    assert ensure_collection_reward(db, 555, cat1["id"]) is False
    assert ensure_collection_reward(db, 555, cat2["id"]) is False
    user = db.query(User).filter(User.vk_id == 555).first()
    assert user.crystals == 1
    assert db.query(CollectionReward).filter_by(user_id=555).count() == 1

    db.add(__import__("models").UserCard(user_id=555, card_id=card2["id"]))
    db.add(__import__("models").UserCard(user_id=555, card_id=extra2["id"], source="penalty"))
    db.commit()
    assert ensure_collection_reward(db, 555, cat2["id"]) is True
    user = db.query(User).filter(User.vk_id == 555).first()
    assert user.crystals == 2
    assert db.query(CollectionReward).filter_by(user_id=555).count() == 2


def test_partial_category_no_award(admin_client, db):
    hid, _ = _finished_holiday(admin_client, cards=("Тыква", "Кот"))
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    cat_id = detail["categories"][0]["id"]
    card_ids = [c["id"] for c in detail["categories"][0]["cards"] if c["title"]]
    extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Магазинная"},
    ).json()
    db.add(User(vk_id=777, role="player"))
    db.add(__import__("models").UserCard(user_id=777, card_id=card_ids[0]))
    db.add(__import__("models").UserCard(user_id=777, card_id=extra["id"], source="penalty"))
    db.commit()
    assert ensure_collection_reward(db, 777, cat_id) is False


def _preset(admin_client, key="second_task", price=None):
    item = next(row for row in admin_client.get("/api/admin/rewards/items").json() if row["preset_key"] == key)
    if price is not None:
        item = admin_client.put(
            f"/api/admin/rewards/items/{item['id']}",
            json={"title": item["title"], "description": item["description"], "price_crystals": price, "is_active": True},
        ).json()
    return item


def test_buy_item_happy_path(admin_client, db, uploads_tmp):
    hid, cat_id, card_id = _active_holiday_one_card(admin_client)
    extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Магазинная"},
    ).json()
    item = _preset(admin_client)
    with make_user_client(123) as player:
        db.add(__import__("models").UserCard(user_id=123, card_id=extra["id"], source="penalty"))
        db.commit()
        task = player.post(f"/api/game/cards/{card_id}/take").json()
        player.post(
            f"/api/game/tasks/{task['id']}/report",
            data={"amount": "300", "mode": "norm"},
            files={"photo_before": ("b.png", _png_bytes(), "image/png"), "photo_after": ("a.png", _png_bytes(), "image/png")},
        )
        resp = player.post("/api/rewards/buy", json={"item_id": item["id"]})
        assert resp.status_code == 200
        assert resp.json()["crystals_left"] == 0
        assert "code" not in resp.json()
        rewards = player.get("/api/rewards").json()

    assert rewards["crystals"] == 0
    assert len(rewards["purchases"]) == 1
    assert rewards["purchases"][0]["status"] == "available"
    assert rewards["purchases"][0]["effect_type"] == "extra_active_task"


def test_buy_insufficient_crystals(admin_client):
    item = _preset(admin_client, price=5)
    with make_user_client(123) as player:
        resp = player.post("/api/rewards/buy", json={"item_id": item["id"]})
    assert resp.status_code == 400
    assert "кристалл" in resp.json()["detail"]


def test_repeat_purchases_do_not_need_codes(admin_client, db):
    item = _preset(admin_client)
    db.add(User(vk_id=123, role="player", crystals=5))
    db.commit()
    with make_user_client(123) as player:
        assert player.post("/api/rewards/buy", json={"item_id": item["id"]}).status_code == 200
        assert player.post("/api/rewards/buy", json={"item_id": item["id"]}).status_code == 200
    purchases = db.query(RewardPurchase).all()
    assert len(purchases) == 2
    assert all(purchase.code_id is None for purchase in purchases)
    assert db.query(User).filter(User.vk_id == 123).first().crystals == 3


def test_admin_cannot_create_or_delete_presets(admin_client):
    item = _preset(admin_client)
    assert admin_client.post("/api/admin/rewards/items", json={"title": "Ручная"}).status_code == 405
    assert admin_client.delete(f"/api/admin/rewards/items/{item['id']}").status_code == 405
    updated = admin_client.put(
        f"/api/admin/rewards/items/{item['id']}",
        json={"title": "Новое название", "price_crystals": 3, "is_active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Новое название"
    assert updated.json()["price_crystals"] == 3


def test_buy_rejects_non_preset_item(admin_client, db):
    db.add(RewardItem(title="Старая ручная", price_crystals=1, is_active=True))
    db.commit()
    item = db.query(RewardItem).filter_by(title="Старая ручная").one()
    db.add(User(vk_id=123, role="player", crystals=5))
    db.commit()
    with make_user_client(123) as player:
        assert player.post("/api/rewards/buy", json={"item_id": item.id}).status_code == 404


def test_admin_forbidden_for_player(player_client):
    assert player_client.get("/api/admin/rewards/items").status_code == 403


def test_extra_shop_card_counts_toward_category(admin_client, db, uploads_tmp, monkeypatch):
    import routes.shop as shop_module
    from models import UserCard as UC
    from tests.test_shop import _shop_now_at

    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))
    hid, day_card_ids = _finished_holiday(
        admin_client,
        cards=("Тыква", "Кот", "Призрак", "Паук", "Свеча", "Фонарь"),
    )
    cat_id = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["id"]
    extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Магазинная"},
    ).json()
    second_extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Вторая магазинная"},
    ).json()

    for card_id in day_card_ids[:5]:
        db.add(UC(user_id=123, card_id=card_id))
    db.add(UC(user_id=123, card_id=second_extra["id"], source="penalty"))
    db.commit()
    assert ensure_collection_reward(db, 123, cat_id) is False

    with make_user_client(123) as player:
        shop_cards = [
            c for h in player.get("/api/shop").json()["holidays"]
            if h["holiday_id"] == hid for c in h["cards"]
        ]
        extra_card = [c for c in shop_cards if c["title"] == "Магазинная"][0]
        assert extra_card["id"] == extra["id"]
        take = player.post("/api/shop/take", json={"card_id": extra_card["id"]}).json()
        resp = player.post(
            f"/api/game/tasks/{take['task_id']}/report",
            data={"amount": "1000", "mode": "norm"},
            files={"photo_before": ("b.png", _png_bytes(), "image/png"), "photo_after": ("a.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code == 200
        rewards = player.get("/api/rewards").json()
    assert rewards["crystals"] == 1
    assert len(rewards["trophies"]) == 1
    assert rewards["trophies"][0]["category_id"] == cat_id
    assert rewards["trophies"][0]["category_title"] == "Кат"
