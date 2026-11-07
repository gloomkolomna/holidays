import pytest

import routes.shop as shop_module
from models import RewardPurchase, Task, User, UserCard
from services.msk_time import now_msk
from services.reward_integrations import IntegrationError
from tests.conftest import make_user_client
from tests.test_holidays import _multi_day_holiday_payload, _png_bytes
from tests.test_shop import _finished_holiday, _shop_now_at


def _preset(client, key):
    response = client.get("/api/admin/rewards/items")
    assert response.status_code == 200
    return next(item for item in response.json() if item["preset_key"] == key)


def _buy(db, client, item_id, vk_id=123, crystals=20):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if user is None:
        user = User(vk_id=vk_id, role="player", crystals=crystals)
        db.add(user)
    else:
        user.crystals = crystals
    db.commit()
    response = client.post("/api/rewards/buy", json={"item_id": item_id})
    assert response.status_code == 200, response.text
    return response.json()["purchase_id"]


def _use(client, purchase_id, **payload):
    return client.post(f"/api/rewards/purchases/{purchase_id}/use", json=payload)


def _active_cards(admin_client, count=3):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Текущий")).json()["id"]
    result = []
    for index in range(count):
        admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": f"Раздел {index}", "norm_crosses": 300 + index})
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    for category in detail["categories"]:
        today = now_msk().date().isoformat()
        slot = next(card for card in category["cards"] if card["day"] == today)
        card = admin_client.put(
            f"/api/admin/holidays/{hid}/cards/{slot['id']}",
            json={"title": f"Карточка {category['id']}"},
        ).json()
        result.append(card["id"])
    return hid, result


def test_presets_are_code_defined_and_editable(admin_client):
    items = admin_client.get("/api/admin/rewards/items").json()
    assert len(items) == 7
    assert all(item["price_crystals"] == 1 for item in items)
    assert admin_client.post("/api/admin/rewards/items", json={"title": "Своя"}).status_code == 405

    discount = _preset(admin_client, "zakaz_discount")
    response = admin_client.put(
        f"/api/admin/rewards/items/{discount['id']}",
        json={
            "title": "Скидка постоянного игрока",
            "description": "Новое описание",
            "price_crystals": 4,
            "is_active": True,
            "effect_config": {"percent": 12},
        },
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Скидка постоянного игрока"
    assert response.json()["price_crystals"] == 4
    assert response.json()["effect_config"] == {"percent": 12}


def test_buy_creates_inventory_without_promo_code(admin_client, db):
    item = _preset(admin_client, "second_task")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        response = player.get("/api/rewards")
    purchase = next(row for row in response.json()["purchases"] if row["id"] == purchase_id)
    assert purchase["status"] == "available"
    assert purchase["effect_type"] == "extra_active_task"
    assert "code" not in purchase


def test_reduce_penalty(admin_client, db, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))
    _, cards = _finished_holiday(admin_client)
    item = _preset(admin_client, "penalty_half")
    with make_user_client(123) as player:
        task = player.post("/api/shop/take", json={"card_id": cards[0]}).json()
        purchase_id = _buy(db, player, item["id"])
        response = _use(player, purchase_id, task_id=task["task_id"])
        assert _use(player, purchase_id).status_code == 409

    assert response.status_code == 200, response.text
    assert db.get(Task, task["task_id"]).required_crosses == 500
    assert db.get(RewardPurchase, purchase_id).status == "used"


def test_second_task_allows_two_and_ends_after_report(admin_client, db, uploads_tmp):
    _, cards = _active_cards(admin_client, 3)
    item = _preset(admin_client, "second_task")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        assert _use(player, purchase_id).status_code == 200
        first = player.post(f"/api/game/cards/{cards[0]}/take").json()
        second = player.post(f"/api/game/cards/{cards[1]}/take").json()
        assert player.post(f"/api/game/cards/{cards[2]}/take").status_code == 409
        state = player.get("/api/game/state").json()
        assert len(state["active_tasks"]) == 2
        assert state["can_take_task"] is False

        response = player.post(
            f"/api/game/tasks/{first['id']}/report",
            data={"amount": "300", "mode": "norm"},
            files={"photo_before": ("b.png", _png_bytes(), "image/png"), "photo_after": ("a.png", _png_bytes(), "image/png")},
        )
        assert response.status_code == 200
        state = player.get("/api/game/state").json()
        assert len(state["active_tasks"]) == 1
        assert state["active_tasks"][0]["id"] == second["id"]
        assert state["extra_task_active"] is False
        assert player.post(f"/api/game/cards/{cards[2]}/take").status_code == 409
    assert db.get(RewardPurchase, purchase_id).status == "used"
    detail = admin_client.get("/api/admin/players/123").json()
    assert len(detail["active_tasks"]) == 1


def test_shop_always_open_until_next_holiday(admin_client, db, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(0))
    _finished_holiday(admin_client)
    item = _preset(admin_client, "shop_always")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        assert _use(player, purchase_id).status_code == 200
        assert player.get("/api/shop").json()["open"] is True
    admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Новый"))
    with make_user_client(123) as player:
        assert player.get("/api/shop").json()["open"] is False
    assert db.get(RewardPurchase, purchase_id).status == "used"


def test_shop_without_penalty_uses_category_norm(admin_client, db, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))
    _, cards = _finished_holiday(admin_client)
    item = _preset(admin_client, "shop_norm")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        assert _use(player, purchase_id).status_code == 200
        card = player.get("/api/shop").json()["holidays"][0]["cards"][0]
        assert card["penalty_crosses"] == 500
        task = player.post("/api/shop/take", json={"card_id": cards[0]}).json()
    assert task["required_crosses"] == 500


def test_complete_shop_card_without_task_or_report(admin_client, db, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))
    _, cards = _finished_holiday(admin_client, cards=("Тыква",))
    item = _preset(admin_client, "shop_free_card")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        response = _use(player, purchase_id, card_id=cards[0])

    assert response.status_code == 200, response.text
    collected = db.query(UserCard).filter_by(user_id=123, card_id=cards[0]).one()
    assert collected.source == "reward"
    assert db.query(Task).count() == 0
    assert db.get(RewardPurchase, purchase_id).status == "used"


def test_external_reward_success_and_retryable_failure(admin_client, db, monkeypatch):
    discount = _preset(admin_client, "zakaz_discount")
    admin_client.put(
        f"/api/admin/rewards/items/{discount['id']}",
        json={"title": discount["title"], "price_crystals": 1, "is_active": True, "effect_config": {"percent": 7}},
    )
    calls = []

    def success(effect, purchase_id, vk_id, payload):
        calls.append(payload)
        return {"id": 77, "percent": payload["percent"]}

    monkeypatch.setattr("routes.rewards.apply_external_reward", success)
    with make_user_client(123) as player:
        first_id = _buy(db, player, discount["id"])
        assert _use(player, first_id).status_code == 200
        assert calls == [{"percent": 7}]
        assert db.get(RewardPurchase, first_id).status == "used"

        monkeypatch.setattr("routes.rewards.apply_external_reward", lambda *args: (_ for _ in ()).throw(IntegrationError("Нет связи")))
        second_id = _buy(db, player, discount["id"])
        assert _use(player, second_id).status_code == 502
    purchase = db.get(RewardPurchase, second_id)
    assert purchase.status == "available"
    assert purchase.last_error == "Нет связи"


def test_admin_lists_and_revokes_active_reward(admin_client, db):
    item = _preset(admin_client, "second_task")
    with make_user_client(123) as player:
        purchase_id = _buy(db, player, item["id"])
        assert _use(player, purchase_id).status_code == 200
    purchases = admin_client.get("/api/admin/rewards/purchases").json()
    assert purchases[0]["user_id"] == 123

    assert admin_client.post(f"/api/admin/rewards/purchases/{purchase_id}/revoke").status_code == 200
    assert db.get(RewardPurchase, purchase_id).status == "revoked"
