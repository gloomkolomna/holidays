import datetime

import pytest

import routes.shop as shop_module
from models import Task, UserCard
from services.msk_time import MSK, now_msk
from tests.conftest import make_user_client
from tests.test_holidays import _multi_day_holiday_payload, _png_bytes


def _shop_now_at(weekday: int) -> datetime.datetime:
    """Ближайшая (включая сегодня) заданная дата в 12:00 МСК."""
    now = datetime.datetime.now(MSK)
    offset = (weekday - now.weekday()) % 7
    return (now + datetime.timedelta(days=offset)).replace(hour=12, minute=0, second=0, microsecond=0)


@pytest.fixture(autouse=True)
def _open_shop(monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))


def _finished_holiday(admin_client, title="Прошедший", shop=True, cards=("Тыква", "Кот")):
    payload = _multi_day_holiday_payload(title)
    now = now_msk().replace(tzinfo=None)
    payload["starts_at"] = (now - datetime.timedelta(days=6)).isoformat()
    payload["ends_at"] = (now - datetime.timedelta(days=1)).isoformat()
    payload["shop_enabled"] = shop
    hid = admin_client.post("/api/admin/holidays", json=payload).json()["id"]
    cat = admin_client.post(
        f"/api/admin/holidays/{hid}/categories", json={"title": "Кат", "norm_crosses": 500},
    ).json()
    filled_ids = []
    slots = [c for c in admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"] if c["id"] == cat["id"]][0]["cards"]
    for slot, title_card in zip(slots, cards):
        filled = admin_client.put(
            f"/api/admin/holidays/{hid}/cards/{slot['id']}", json={"title": title_card},
        ).json()
        filled_ids.append(filled["id"])
    return hid, filled_ids


def test_shop_requires_auth(client):
    assert client.get("/api/shop").status_code == 401


def test_shop_open_days(monkeypatch):
    for weekday, expected in ((5, True), (6, True), (0, False), (4, False)):
        monkeypatch.setattr(shop_module, "now_msk", lambda w=weekday: _shop_now_at(w))
        assert shop_module._shop_open() is expected


def test_shop_closed_while_holiday_active(admin_client, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(5))
    hid, card_ids = _finished_holiday(admin_client)
    admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Идущий"))

    with make_user_client(123) as player:
        data = player.get("/api/shop").json()
        resp = player.post("/api/shop/take", json={"card_id": card_ids[0]})
    assert data["open"] is False
    assert data["reason"] == "holiday_active"
    assert data["active_holiday_title"] == "Идущий"
    assert data["active_holiday_ends_at"] is not None
    assert resp.status_code == 400
    assert "после завершения" in resp.json()["detail"]


def test_shop_closed_on_weekday(admin_client, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(0))
    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква", "Кот"))
    with make_user_client(123) as player:
        data = player.get("/api/shop").json()
        resp = player.post("/api/shop/take", json={"card_id": card_ids[0]})
    assert data["open"] is False
    assert data["reason"] == "weekday"
    assert data["holidays"] == []
    assert resp.status_code == 400
    assert "субботам" in resp.json()["detail"]


def test_shop_open_on_weekend(admin_client, monkeypatch):
    monkeypatch.setattr(shop_module, "now_msk", lambda: _shop_now_at(6))
    hid, card_ids = _finished_holiday(admin_client)
    with make_user_client(123) as player:
        data = player.get("/api/shop").json()
        resp = player.post("/api/shop/take", json={"card_id": card_ids[0]})
    assert data["open"] is True
    assert data["reason"] == "open"
    assert len(data["holidays"]) == 1
    assert resp.status_code == 200


def test_shop_lists_finished_holidays_uncollected_cards(admin_client, db):
    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква", "Кот", "Привидение"))
    db.add(UserCard(user_id=123, card_id=card_ids[0]))
    db.commit()

    with make_user_client(123) as player:
        resp = player.get("/api/shop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["penalty_crosses"] == 1000
    assert len(data["holidays"]) == 1
    shop_holiday = data["holidays"][0]
    assert shop_holiday["holiday_id"] == hid
    titles = {c["title"] for c in shop_holiday["cards"]}
    assert titles == {"Кот", "Привидение"}
    assert all(c["penalty_crosses"] == 1000 for c in shop_holiday["cards"])


def test_shop_hides_disabled_and_upcoming(admin_client):
    _finished_holiday(admin_client, title="Закрытый", shop=False)
    _finished_holiday(admin_client, title="Открытый", shop=True)
    now = now_msk().replace(tzinfo=None)
    payload = _multi_day_holiday_payload("Будущий")
    payload["starts_at"] = (now + datetime.timedelta(days=3)).isoformat()
    payload["ends_at"] = (now + datetime.timedelta(days=8)).isoformat()
    admin_client.post("/api/admin/holidays", json=payload)

    with make_user_client(123) as player:
        data = player.get("/api/shop").json()
    assert data["open"] is True
    titles = {h["title"] for h in data["holidays"]}
    assert titles == {"Открытый"}


def test_shop_take_happy_path(admin_client, db):
    hid, card_ids = _finished_holiday(admin_client)
    with make_user_client(123) as player:
        resp = player.post("/api/shop/take", json={"card_id": card_ids[0]})
    assert resp.status_code == 200
    assert resp.json()["required_crosses"] == 1000

    task = db.query(Task).filter(Task.user_id == 123).first()
    assert task.kind == "penalty"
    assert task.status == "active"
    assert task.required_crosses == 1000


def test_shop_take_conflicts_with_active_task(admin_client):
    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква", "Кот"))
    with make_user_client(123) as player:
        assert player.post("/api/shop/take", json={"card_id": card_ids[0]}).status_code == 200
        resp = player.post("/api/shop/take", json={"card_id": card_ids[1]})
    assert resp.status_code == 409


def test_shop_take_collected_conflict(admin_client, db):
    hid, card_ids = _finished_holiday(admin_client)
    db.add(UserCard(user_id=123, card_id=card_ids[0]))
    db.commit()
    with make_user_client(123) as player:
        resp = player.post("/api/shop/take", json={"card_id": card_ids[0]})
    assert resp.status_code == 409


def test_shop_take_unfinished_holiday_rejected(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Идущий")).json()["id"]
    cat = admin_client.post(
        f"/api/admin/holidays/{hid}/categories", json={"title": "Кат", "norm_crosses": 500},
    ).json()
    slot = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]
    card = admin_client.put(f"/api/admin/holidays/{hid}/cards/{slot['id']}", json={"title": "Днём"}).json()

    with make_user_client(123) as player:
        resp = player.post("/api/shop/take", json={"card_id": card["id"]})
    assert resp.status_code == 400


def test_shop_take_unknown_card_404(admin_client):
    with make_user_client(123) as player:
        resp = player.post("/api/shop/take", json={"card_id": 999999})
    assert resp.status_code == 404


def test_penalty_task_reportable_and_collects_card(admin_client, db, uploads_tmp):
    hid, card_ids = _finished_holiday(admin_client)
    with make_user_client(123) as player:
        task = player.post("/api/shop/take", json={"card_id": card_ids[0]}).json()
        resp = player.post(
            f"/api/game/tasks/{task['task_id']}/report",
            data={"amount": "1000", "mode": "norm"},
            files={
                "photo_before": ("b.png", _png_bytes((1, 1, 1)), "image/png"),
                "photo_after": ("a.png", _png_bytes((2, 2, 2)), "image/png"),
            },
        )
        assert resp.status_code == 200

    uc = db.query(UserCard).filter(UserCard.user_id == 123, UserCard.card_id == card_ids[0]).first()
    assert uc is not None
    assert uc.source == "penalty"


def test_penalty_task_cannot_be_abandoned(admin_client, db):
    hid, card_ids = _finished_holiday(admin_client)
    with make_user_client(123) as player:
        task = player.post("/api/shop/take", json={"card_id": card_ids[0]}).json()
        resp = player.post(f"/api/game/tasks/{task['task_id']}/abandon")
    assert resp.status_code == 409
    assert "нельзя отказаться" in resp.json()["detail"]

    task_row = db.query(Task).filter(Task.user_id == 123).first()
    assert task_row.status == "active"


def test_penalty_task_rejects_penalty_mode(admin_client, uploads_tmp):
    hid, card_ids = _finished_holiday(admin_client)
    with make_user_client(123) as player:
        task = player.post("/api/shop/take", json={"card_id": card_ids[0]}).json()
        resp = player.post(
            f"/api/game/tasks/{task['task_id']}/report",
            data={"amount": "2000", "mode": "penalty"},
            files={
                "photo_before": ("b.png", _png_bytes(), "image/png"),
                "photo_after": ("a.png", _png_bytes(), "image/png"),
            },
        )
    assert resp.status_code == 400
    assert "норме" in resp.json()["detail"]


def test_shop_take_race_returns_409_not_500(admin_client, monkeypatch):
    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква", "Кот"))
    with make_user_client(123) as player:
        assert player.post("/api/shop/take", json={"card_id": card_ids[0]}).status_code == 200
        monkeypatch.setattr(shop_module, "has_active_task", lambda db, uid: False)
        resp = player.post("/api/shop/take", json={"card_id": card_ids[1]})
    assert resp.status_code == 409
    assert "новое взять нельзя" in resp.json()["detail"]


def test_shop_lists_extra_cards(admin_client, db):
    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква",))
    cat_id = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["id"]
    admin_client.post(f"/api/admin/holidays/{hid}/extra-cards", json={"category_id": cat_id, "title": "Бонусная"})

    with make_user_client(123) as player:
        data = player.get("/api/shop").json()
    cards = {c["title"]: c for h in data["holidays"] if h["holiday_id"] == hid for c in h["cards"]}
    assert set(cards) == {"Тыква", "Бонусная"}
    assert "is_trophy" not in cards["Бонусная"]
    assert cards["Бонусная"]["day"] is None
