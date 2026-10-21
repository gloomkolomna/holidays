import datetime

from models import CollectionReward, RewardCode, RewardItem, User
from services.msk_time import now_msk
from services.rewards import ensure_collection_reward
from tests.conftest import make_user_client
from tests.test_holidays import _multi_day_holiday_payload, _png_bytes
from tests.test_shop import _finished_holiday, _shop_now_at


def _active_holiday_one_card(admin_client, title="Короткий"):
    payload = _multi_day_holiday_payload(title)
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
    with make_user_client(123) as player:
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
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Двухразделовый")).json()["id"]
    cat1 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Наряды", "norm_crosses": 500}).json()
    cat2 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Декор", "norm_crosses": 900}).json()
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    by_cat = {c["id"]: c["cards"] for c in detail["categories"]}
    card1 = admin_client.put(f"/api/admin/holidays/{hid}/cards/{by_cat[cat1['id']][0]['id']}", json={"title": "Первая"}).json()
    card2 = admin_client.put(f"/api/admin/holidays/{hid}/cards/{by_cat[cat2['id']][0]['id']}", json={"title": "Вторая"}).json()

    db.add(User(vk_id=555, role="player"))
    db.add(__import__("models").UserCard(user_id=555, card_id=card1["id"]))
    db.commit()

    assert ensure_collection_reward(db, 555, cat1["id"]) is True
    assert ensure_collection_reward(db, 555, cat1["id"]) is False
    assert ensure_collection_reward(db, 555, cat2["id"]) is False

    user = db.query(User).filter(User.vk_id == 555).first()
    assert user.crystals == 1
    assert db.query(CollectionReward).filter_by(user_id=555).count() == 1

    db.add(__import__("models").UserCard(user_id=555, card_id=card2["id"]))
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
    db.add(User(vk_id=777, role="player"))
    db.add(__import__("models").UserCard(user_id=777, card_id=card_ids[0]))
    db.commit()
    assert ensure_collection_reward(db, 777, cat_id) is False


def _make_item(admin_client, title="Промокод Фермы", price=1, codes=("FARM-100", "FARM-200")):
    item = admin_client.post(
        "/api/admin/rewards/items",
        json={"title": title, "description": "Бонус в «Ферме»", "price_crystals": price},
    ).json()
    admin_client.post(f"/api/admin/rewards/items/{item['id']}/codes", json={"codes": list(codes)})
    return item


def test_buy_item_happy_path(admin_client, db, uploads_tmp):
    hid, cat_id, card_id = _active_holiday_one_card(admin_client)
    item = _make_item(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{card_id}/take").json()
        player.post(
            f"/api/game/tasks/{task['id']}/report",
            data={"amount": "300", "mode": "norm"},
            files={
                "photo_before": ("b.png", _png_bytes(), "image/png"),
                "photo_after": ("a.png", _png_bytes(), "image/png"),
            },
        )
        resp = player.post("/api/rewards/buy", json={"item_id": item["id"]})
        assert resp.status_code == 200
        assert resp.json()["crystals_left"] == 0
        assert resp.json()["code"] == "FARM-100"

        rewards = player.get("/api/rewards").json()
    assert rewards["crystals"] == 0
    assert len(rewards["purchases"]) == 1
    assert rewards["purchases"][0]["code"] == "FARM-100"
    assert rewards["items"][0]["codes_available"] == 1


def test_buy_insufficient_crystals(admin_client):
    item = _make_item(admin_client, price=5)
    with make_user_client(123) as player:
        resp = player.post("/api/rewards/buy", json={"item_id": item["id"]})
    assert resp.status_code == 400
    assert "кристалл" in resp.json()["detail"]


def test_buy_out_of_codes(admin_client, db):
    item = _make_item(admin_client, codes=("ONLY-1",))
    db.add(User(vk_id=123, role="player", crystals=10))
    db.commit()
    with make_user_client(123) as player:
        assert player.post("/api/rewards/buy", json={"item_id": item["id"]}).status_code == 200
        resp = player.post("/api/rewards/buy", json={"item_id": item["id"]})
    assert resp.status_code == 400
    assert "распродан" in resp.json()["detail"]


def test_admin_items_crud_and_codes(admin_client):
    item = admin_client.post(
        "/api/admin/rewards/items",
        json={"title": "Тест", "price_crystals": 2},
    ).json()
    assert item["codes_available"] == 0

    added = admin_client.post(
        f"/api/admin/rewards/items/{item['id']}/codes",
        json={"codes": ["A-1", "A-2", ""]},
    ).json()
    assert added["added"] == 2
    assert added["available"] == 2

    updated = admin_client.put(
        f"/api/admin/rewards/items/{item['id']}",
        json={"title": "Тест2", "price_crystals": 3},
    ).json()
    assert updated["title"] == "Тест2"

    codes = admin_client.get(f"/api/admin/rewards/items/{item['id']}/codes").json()
    assert len(codes) == 2

    code_id = codes[0]["id"]
    assert admin_client.delete(f"/api/admin/rewards/codes/{code_id}").status_code == 200
    assert len(admin_client.get(f"/api/admin/rewards/items/{item['id']}/codes").json()) == 1

    assert admin_client.delete(f"/api/admin/rewards/items/{item['id']}").status_code == 200
    assert admin_client.get("/api/admin/rewards/items").json() == []


def test_taken_code_cannot_be_deleted(admin_client, db):
    item = _make_item(admin_client, codes=("X-1",))
    code = db.query(RewardCode).filter(RewardCode.item_id == item["id"]).first()
    code.taken_by = 123
    db.commit()
    resp = admin_client.delete(f"/api/admin/rewards/codes/{code.id}")
    assert resp.status_code == 400


def test_admin_forbidden_for_player(player_client):
    assert player_client.get("/api/admin/rewards/items").status_code == 403


def test_trophy_card_required_for_full_category(admin_client, db, uploads_tmp, monkeypatch):
    import routes.shop as shop_module
    from models import UserCard as UC

    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))

    hid, day_card_ids = _finished_holiday(admin_client, cards=("Тыква",))
    cat_id = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["id"]
    trophy = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Кубковая", "is_trophy": True},
    ).json()

    db.add(UC(user_id=123, card_id=day_card_ids[0]))
    db.commit()

    assert ensure_collection_reward(db, 123, cat_id) is False

    with make_user_client(123) as player:
        shop_cards = [
            c for h in player.get("/api/shop").json()["holidays"]
            if h["holiday_id"] == hid for c in h["cards"]
        ]
        trophy_card = [c for c in shop_cards if c["is_trophy"]][0]
        assert trophy_card["id"] == trophy["id"]

        take = player.post("/api/shop/take", json={"card_id": trophy_card["id"]}).json()
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
