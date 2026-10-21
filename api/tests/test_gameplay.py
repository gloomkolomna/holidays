import datetime
import io

import services.cards_grid as cards_grid
import services.msk_time as msk_time
from models import Task, UserCard
from services.msk_time import now_msk
from tests.conftest import make_user_client
from tests.test_holidays import _multi_day_holiday_payload, _png_bytes


def _create_holiday_with_filled_days(
    admin_client,
    categories=(("Наряды", 500), ("Декор", 900)),
):
    """Праздник 5 дней (вчера..+3), карточки заполнены на все дни."""
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    today = now_msk().date().isoformat()
    cards_by_day: dict[str, dict[str, dict]] = {}
    detail = admin_client.get(f"/api/admin/holidays/{hid}")
    for cat_title, norm in categories:
        cat = admin_client.post(
            f"/api/admin/holidays/{hid}/categories",
            json={"title": cat_title, "norm_crosses": norm},
        ).json()
        slots = [
            c for c in admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"]
            if c["id"] == cat["id"]
        ][0]["cards"]
        for slot in slots:
            filled = admin_client.put(
                f"/api/admin/holidays/{hid}/cards/{slot['id']}",
                json={"title": f"{cat_title}-{slot['day']}", "task_text": f"Задание {cat_title} {slot['day']}"},
            ).json()
            cards_by_day.setdefault(slot["day"], {})[cat_title] = filled
    return hid, today, cards_by_day


def test_state_no_holiday(player_client):
    resp = player_client.get("/api/game/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["holiday_id"] is None
    assert data["today_cards"] == []


def test_state_shows_only_todays_cards(admin_client):
    hid, today, _ = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        state = player.get("/api/game/state").json()
    assert state["holiday_id"] == hid
    titles = {c["card"]["title"] for c in state["today_cards"]}
    assert titles == {f"Наряды-{today}", f"Декор-{today}"}
    norms = {c["card"]["norm_crosses"] for c in state["today_cards"]}
    assert norms == {500, 900}
    assert all(c["card"]["task_text"] for c in state["today_cards"])
    assert all(not c["collected"] and not c["is_current"] for c in state["today_cards"])
    assert state["active_task"] is None
    assert state["cards_total"] == 12
    assert state["collected_count"] == 0


def test_take_card_happy_path(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    card_id = cards[today]["Наряды"]["id"]
    with make_user_client(123) as player:
        resp = player.post(f"/api/game/cards/{card_id}/take")
        assert resp.status_code == 200
        task = resp.json()
        assert task["required_crosses"] == 500

        state = player.get("/api/game/state").json()
        assert state["active_task"]["id"] == task["id"]
        current = [c for c in state["today_cards"] if c["is_current"]]
        assert len(current) == 1 and current[0]["card"]["id"] == card_id


def test_take_second_while_active_conflict(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        assert player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").status_code == 200
        resp = player.post(f"/api/game/cards/{cards[today]['Декор']['id']}/take")
    assert resp.status_code == 409


def test_take_past_day_card_rejected(admin_client, db):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    yesterday = (now_msk().date() - datetime.timedelta(days=1)).isoformat()
    past_card = cards[yesterday]["Наряды"]
    with make_user_client(123) as player:
        state = player.get("/api/game/state").json()
        assert all(c["card"]["id"] != past_card["id"] for c in state["today_cards"])
        resp = player.post(f"/api/game/cards/{past_card['id']}/take")
    assert resp.status_code == 400


def test_take_draft_card_404(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    admin_client.post(
        f"/api/admin/holidays/{hid}/categories", json={"title": "Наряды", "norm_crosses": 500},
    )
    slot = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]
    with make_user_client(123) as player:
        resp = player.post(f"/api/game/cards/{slot['id']}/take")
    assert resp.status_code == 404


def test_take_collected_card_conflict(admin_client, db, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    card_id = cards[today]["Наряды"]["id"]
    db.add(UserCard(user_id=123, card_id=card_id))
    db.commit()
    with make_user_client(123) as player:
        resp = player.post(f"/api/game/cards/{card_id}/take")
    assert resp.status_code == 409


def test_take_unknown_card_404(admin_client):
    _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        resp = player.post("/api/game/cards/999999/take")
    assert resp.status_code == 404


def _report(player, task_id, amount, mode="norm"):
    return player.post(
        f"/api/game/tasks/{task_id}/report",
        data={"amount": str(amount), "mode": mode},
        files={
            "photo_before": ("b.png", _png_bytes((10, 10, 10)), "image/png"),
            "photo_after": ("a.png", _png_bytes((20, 200, 20)), "image/png"),
        },
    )


def test_abandon_and_take_other(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = player.post(f"/api/game/tasks/{task['id']}/abandon")
        assert resp.status_code == 200

        state = player.get("/api/game/state").json()
        assert state["active_task"] is None
        assert all(not c["is_current"] for c in state["today_cards"])

        resp2 = player.post(f"/api/game/cards/{cards[today]['Декор']['id']}/take")
        assert resp2.status_code == 200


def test_abandon_and_retake_same_card(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        assert player.post(f"/api/game/tasks/{task['id']}/abandon").status_code == 200
        resp = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take")
        assert resp.status_code == 200
        assert resp.json()["id"] != task["id"]


def test_abandon_closed_task_conflict(admin_client, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        assert _report(player, task["id"], amount=500).status_code == 200
        resp = player.post(f"/api/game/tasks/{task['id']}/abandon")
    assert resp.status_code == 409


def test_abandon_foreign_task_404(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
    with make_user_client(124) as other:
        resp = other.post(f"/api/game/tasks/{task['id']}/abandon")
    assert resp.status_code == 404


def test_report_and_take_same_day_second_card(admin_client, db, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = _report(player, task["id"], amount=500)
        assert resp.status_code == 200
        assert resp.json()["collected"] is True

        state = player.get("/api/game/state").json()
        assert state["active_task"] is None
        assert state["collected_count"] == 1
        taken_flag = [c for c in state["today_cards"] if c["card"]["id"] == task["card"]["id"]]
        assert taken_flag[0]["collected"] is True

        resp2 = player.post(f"/api/game/cards/{cards[today]['Декор']['id']}/take")
        assert resp2.status_code == 200
        assert resp2.json()["required_crosses"] == 900


def test_report_below_norm(admin_client, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = _report(player, task["id"], amount=499)
    assert resp.status_code == 400
    assert "норм" in resp.json()["detail"].lower()


def test_report_after_holiday_closed(admin_client, db, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()

    from models import Holiday

    holiday = db.query(Holiday).filter(Holiday.id == hid).first()
    holiday.ends_at = now_msk().replace(tzinfo=None) - datetime.timedelta(minutes=1)
    db.commit()

    with make_user_client(123) as player:
        resp = _report(player, task["id"], amount=500)
    assert resp.status_code == 200
    assert db.query(UserCard).filter(UserCard.user_id == 123).count() == 1


def test_next_day_shows_next_cards(admin_client, monkeypatch):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    tomorrow = (now_msk().date() + datetime.timedelta(days=1)).isoformat()
    import routes.gameplay as gameplay_mod

    with make_user_client(123) as player:
        monkeypatch.setattr(cards_grid, "today_msk", lambda: __import__("datetime").date.fromisoformat(tomorrow))
        monkeypatch.setattr(gameplay_mod, "today_msk", lambda: __import__("datetime").date.fromisoformat(tomorrow))
        state = player.get("/api/game/state").json()
    titles = {c["card"]["title"] for c in state["today_cards"]}
    assert titles == {f"Наряды-{tomorrow}", f"Декор-{tomorrow}"}


def test_collection_counts_all_slots_grouped_by_category(admin_client, db):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat1 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Наряды", "norm_crosses": 500}).json()
    cat2 = admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Декор", "norm_crosses": 900}).json()
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    by_cat = {c["id"]: c["cards"] for c in detail["categories"]}
    first_slot = by_cat[cat1["id"]][0]
    admin_client.put(f"/api/admin/holidays/{hid}/cards/{first_slot['id']}", json={"title": "Единственная"})

    with make_user_client(123) as player:
        state = player.get("/api/game/state").json()
        resp = player.get(f"/api/game/collection?holiday_id={hid}")
    data = resp.json()

    assert data["total"] == 12
    assert data["collected"] == 0
    assert len(data["categories"]) == 2
    titles = {c["title"] for c in data["categories"]}
    assert titles == {"Наряды", "Декор"}
    cat_cards = data["categories"][0]["cards"]
    assert len(cat_cards) == 6
    assert any(c["card"]["title"] == "Единственная" for c in cat_cards)
    assert state["cards_total"] == 12
    complete_by_id = {c["id"]: c["complete"] for c in data["categories"]}
    assert complete_by_id == {cat1["id"]: False, cat2["id"]: False}

    db.add(UserCard(user_id=123, card_id=first_slot["id"]))
    db.commit()
    with make_user_client(123) as player:
        after = player.get(f"/api/game/collection?holiday_id={hid}").json()
        state2 = player.get("/api/game/state").json()
    assert after["collected"] == 1
    assert state2["collected_count"] == 1
    assert state2["cards_total"] == 12
    complete_by_id = {c["id"]: c["complete"] for c in after["categories"]}
    assert complete_by_id == {cat1["id"]: True, cat2["id"]: False}


def test_game_requires_auth(client):
    assert client.get("/api/game/state").status_code == 401


def _heic_bytes() -> bytes | None:
    try:
        from PIL import Image
        import pillow_heif

        buf = io.BytesIO()
        Image.new("RGB", (40, 40), (10, 120, 10)).save(buf, format="HEIF")
        return buf.getvalue()
    except Exception:
        return None


def test_report_penalty_mode(admin_client, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()

        resp = _report(player, task["id"], amount=1000, mode="penalty")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "penalty"
        assert resp.json()["collected"] is True


def test_report_penalty_below_double(admin_client, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = _report(player, task["id"], amount=999, mode="penalty")
    assert resp.status_code == 400
    assert "штраф" in resp.json()["detail"]


def test_report_invalid_mode(admin_client, uploads_tmp):
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = _report(player, task["id"], amount=500, mode="cheat")
    assert resp.status_code == 400


def test_report_accepts_heic(admin_client, db, uploads_tmp):
    heic = _heic_bytes()
    if heic is None:
        import pytest
        pytest.skip("pillow-heif не умеет создавать HEIF")
    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = player.post(
            f"/api/game/tasks/{task['id']}/report",
            data={"amount": "500", "mode": "norm"},
            files={
                "photo_before": ("b.heic", heic, "image/heic"),
                "photo_after": ("a.heic", heic, "image/heic"),
            },
        )
    assert resp.status_code == 200
    assert resp.json()["collected"] is True


def test_report_photos_go_to_s3_when_enabled(admin_client, db, uploads_tmp, monkeypatch):
    import config
    import services.s3_storage as s3_mod

    uploaded = []

    def fake_upload(key, data, content_type="image/jpeg"):
        uploaded.append(key)
        return f"https://s3.example.com/{key}"

    monkeypatch.setattr(config, "S3_ENABLED", True)
    monkeypatch.setattr(config, "S3_PUBLIC_URL", "https://s3.example.com")
    monkeypatch.setattr(s3_mod, "upload_bytes", fake_upload)

    hid, today, cards = _create_holiday_with_filled_days(admin_client)
    with make_user_client(123) as player:
        task = player.post(f"/api/game/cards/{cards[today]['Наряды']['id']}/take").json()
        resp = _report(player, task["id"], amount=500)
    assert resp.status_code == 200

    from models import StitchReport

    report = db.query(StitchReport).filter(StitchReport.task_id == task["id"]).first()
    assert report.photo_before.startswith("https://s3.example.com/123/")
    assert report.photo_after.startswith("https://s3.example.com/123/")
    assert len(uploaded) == 2


def test_extra_cards_not_in_slider(admin_client):
    hid, today, cards = _create_holiday_with_filled_days(admin_client, categories=(("Наряды", 500),))
    cat_id = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["id"]
    admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Магазинная"},
    )
    with make_user_client(123) as player:
        state = player.get("/api/game/state").json()
        titles = {c["card"]["title"] for c in state["today_cards"]}
    assert "Магазинная" not in titles
    assert state["cards_total"] == 7

    extra_id = [
        c for c in admin_client.get(f"/api/holidays/{hid}").json()["categories"][0]["cards"]
        if c["title"] == "Магазинная"
    ][0]["id"]
    with make_user_client(123) as player:
        resp = player.post(f"/api/game/cards/{extra_id}/take")
    assert resp.status_code == 400
