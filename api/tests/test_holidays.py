import datetime
import io

from PIL import Image

from models import HolidayCard
from services.msk_time import now_msk
from tests.conftest import make_user_client


def _iso(dt: datetime.datetime) -> str:
    return dt.replace(tzinfo=None).isoformat()


def _future_holiday_payload(title: str = "Хеллоуин") -> dict:
    now = now_msk().replace(tzinfo=None)
    return {
        "title": title,
        "starts_at": _iso(now + datetime.timedelta(days=1)),
        "ends_at": _iso(now + datetime.timedelta(days=8)),
    }


def _multi_day_holiday_payload(title: str = "Хеллоуин") -> dict:
    """Праздник на 5 дней: вчера..послезавтра+2 (сегодня внутри)."""
    now = now_msk().replace(tzinfo=None)
    start = (now - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    end = (now + datetime.timedelta(days=4)).replace(hour=12, minute=0, second=0, microsecond=0)
    return {
        "title": title,
        "starts_at": _iso(start),
        "ends_at": _iso(end),
    }


def _expected_days() -> list[str]:
    today = now_msk().date()
    return [(today + datetime.timedelta(days=i)).isoformat() for i in range(-1, 5)]


def _png_bytes(color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (60, 60), color).save(buf, format="PNG")
    return buf.getvalue()


def _create_category(admin_client, holiday_id: int, title: str = "Тыквы", norm: int = 500) -> int:
    resp = admin_client.post(
        f"/api/admin/holidays/{holiday_id}/categories",
        json={"title": title, "norm_crosses": norm},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_holidays_requires_auth(client):
    assert client.get("/api/holidays").status_code == 401


def test_create_holiday_happy_path(admin_client):
    resp = admin_client.post("/api/admin/holidays", json=_future_holiday_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Хеллоуин"
    assert data["status"] == "upcoming"
    assert data["categories_count"] == 0
    assert data["cards_count"] == 0
    assert data["shop_enabled"] is True


def test_create_holiday_forbidden_for_player(player_client):
    resp = player_client.post("/api/admin/holidays", json=_future_holiday_payload())
    assert resp.status_code == 403


def test_create_holiday_bad_dates(admin_client):
    payload = _future_holiday_payload()
    payload["ends_at"] = payload["starts_at"]
    resp = admin_client.post("/api/admin/holidays", json=payload)
    assert resp.status_code == 400


def test_active_holiday_endpoint(admin_client):
    with make_user_client(123) as player:
        assert player.get("/api/holidays/active").status_code == 404
    admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload())
    with make_user_client(123) as player:
        resp = player.get("/api/holidays/active")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_list_holidays_with_status_filter(admin_client):
    admin_client.post("/api/admin/holidays", json=_future_holiday_payload("Будущий"))
    admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Текущий"))
    with make_user_client(123) as player:
        all_holidays = player.get("/api/holidays").json()
    assert {h["title"] for h in all_holidays} == {"Будущий", "Текущий"}
    active_only = admin_client.get("/api/admin/holidays?status=active").json()
    assert [h["title"] for h in active_only] == ["Текущий"]


def test_update_holiday(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_future_holiday_payload()).json()["id"]
    resp = admin_client.put(f"/api/admin/holidays/{hid}", json=_future_holiday_payload("Новое название"))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Новое название"


def test_delete_holiday(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_future_holiday_payload()).json()["id"]
    assert admin_client.delete(f"/api/admin/holidays/{hid}").status_code == 200
    assert admin_client.get(f"/api/admin/holidays/{hid}").status_code == 404


def test_holiday_not_found(admin_client):
    assert admin_client.get("/api/admin/holidays/999").status_code == 404


def test_category_generates_day_grid(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid, "Наряды", norm=500)

    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    category = detail["categories"][0]
    assert [c["day"] for c in category["cards"]] == _expected_days()
    assert all(c["title"] == "" for c in category["cards"])
    assert all(c["norm_crosses"] == 500 for c in category["cards"])


def test_category_crud(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid, "Наряды", norm=500)
    cat2 = _create_category(admin_client, hid, "Декор", norm=800)

    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    assert [c["title"] for c in detail["categories"]] == ["Наряды", "Декор"]
    assert all(len(c["cards"]) == 6 for c in detail["categories"])

    updated = admin_client.put(
        f"/api/admin/holidays/{hid}/categories/{cat_id}",
        json={"title": "Костюмы", "norm_crosses": 600},
    ).json()
    assert updated["title"] == "Костюмы"
    assert updated["norm_crosses"] == 600

    assert admin_client.delete(f"/api/admin/holidays/{hid}/categories/{cat2}").status_code == 200
    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    assert len(detail["categories"]) == 1


def test_category_validation(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/categories",
        json={"title": "  ", "norm_crosses": 500},
    )
    assert resp.status_code == 400
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/categories",
        json={"title": "Наряды", "norm_crosses": 0},
    )
    assert resp.status_code == 400


def test_holiday_dates_change_syncs_grid(admin_client, db):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid)

    today = now_msk().date()
    slots = {c["day"]: c["id"] for c in admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]}
    assert len(slots) == 6

    admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{slots[today.isoformat()]}",
        json={"title": "Заполненная", "task_text": "задание"},
    )

    payload = _multi_day_holiday_payload()
    payload["starts_at"] = _iso((now_msk().replace(tzinfo=None) + datetime.timedelta(days=1)).replace(hour=12))
    resp = admin_client.put(f"/api/admin/holidays/{hid}", json=payload)
    assert resp.status_code == 200

    cards_after = resp.json()["categories"][0]["cards"]
    days = {c["day"] for c in cards_after}
    today_cards = [c for c in cards_after if c["day"] == today.isoformat()]
    assert len(today_cards) == 1
    assert today_cards[0]["title"] == "Заполненная"
    kept = db.query(HolidayCard).filter(HolidayCard.id == slots[today.isoformat()]).first()
    assert kept is not None
    assert kept.title == "Заполненная"

    empty_removed = db.query(HolidayCard).filter(HolidayCard.category_id == cat_id).all()
    assert all(c.day in days or c.title.strip() for c in empty_removed)


def test_fill_card_slot(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid, "Угощения", norm=300)
    slots = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]
    slot = slots[0]

    resp = admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{slot['id']}",
        json={"title": "Тыквенный пирог", "task_text": "Вышейте пирог 40×40"},
    )
    assert resp.status_code == 200
    card = resp.json()
    assert card["title"] == "Тыквенный пирог"
    assert card["task_text"] == "Вышейте пирог 40×40"
    assert card["day"] == slot["day"]
    assert card["norm_crosses"] == 300

    cleared = admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{slot['id']}",
        json={"title": "", "task_text": None},
    ).json()
    assert cleared["title"] == ""


def test_public_detail_hides_drafts(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid)
    slots = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]
    admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{slots[0]['id']}",
        json={"title": "Готовая карточка"},
    )

    with make_user_client(123) as player:
        public = player.get(f"/api/holidays/{hid}").json()
    admin = admin_client.get(f"/api/admin/holidays/{hid}").json()

    assert len(admin["categories"][0]["cards"]) == 6
    assert len(public["categories"][0]["cards"]) == 1
    assert public["categories"][0]["cards"][0]["title"] == "Готовая карточка"


def test_card_image_upload_and_clear(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    _create_category(admin_client, hid)
    slot = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]

    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/cards/{slot['id']}/image",
        files={"file": ("cat.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    url = resp.json()["image_url"]
    assert url.startswith("/api/uploads/card_")

    assert admin_client.delete(f"/api/admin/holidays/{hid}/cards/{slot['id']}/image").status_code == 200
    slot_after = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]
    assert slot_after["image_url"] is None


def test_card_image_upload_rejects_non_image(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    _create_category(admin_client, hid)
    slot = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/cards/{slot['id']}/image",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_cards_forbidden_for_player(player_client):
    resp = player_client.put("/api/admin/holidays/1/cards/1", json={"title": "X"})
    assert resp.status_code == 403


def test_holiday_bg_image_upload(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/bg-image",
        files={"file": ("bg.png", _png_bytes((90, 60, 120)), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["bg_image_url"].startswith("/api/uploads/holiday_")


def test_public_holiday_detail(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid, "Наряды", norm=500)
    slot = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"][0]
    admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{slot['id']}",
        json={"title": "Тыква", "task_text": "задание"},
    )
    with make_user_client(123) as player:
        resp = player.get(f"/api/holidays/{hid}")
    assert resp.status_code == 200
    card = resp.json()["categories"][0]["cards"][0]
    assert card["title"] == "Тыква"
    assert card["norm_crosses"] == 500


def _white_bg_png(inner=(20, 20, 20), size=60) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([size // 4, size // 4, size * 3 // 4, size * 3 // 4], fill=inner)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_animation_upload_strips_white_background(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/animation",
        files={"file": ("silhouette.png", _white_bg_png(), "image/png")},
    )
    assert resp.status_code == 200
    url = resp.json()["animation_url"]
    assert url.endswith(".png")

    from PIL import Image
    import os

    saved = Image.open(os.path.join(uploads_tmp, url.rsplit("/", 1)[-1])).convert("RGBA")
    assert saved.getpixel((2, 2))[3] == 0
    assert saved.getpixel((30, 30))[3] == 255

    assert admin_client.delete(f"/api/admin/holidays/{hid}/animation").status_code == 200
    assert admin_client.get(f"/api/admin/holidays/{hid}").json()["animation_url"] is None


def test_animation_upload_keeps_existing_alpha(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    from PIL import Image

    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    for x in range(15, 25):
        for y in range(15, 25):
            img.putpixel((x, y), (200, 30, 30, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/animation",
        files={"file": ("alpha.png", buf.getvalue(), "image/png")},
    )
    assert resp.status_code == 200
    import os

    saved = Image.open(os.path.join(uploads_tmp, resp.json()["animation_url"].rsplit("/", 1)[-1])).convert("RGBA")
    assert saved.getpixel((2, 2))[3] == 0
    assert saved.getpixel((20, 20))[3] == 255
    assert saved.getpixel((20, 20))[:3] == (200, 30, 30)


def test_animation_rejects_non_image(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/animation",
        files={"file": ("a.mp3", b"audio", "audio/mpeg")},
    )
    assert resp.status_code == 400


def test_animation_size_validation(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    payload = _multi_day_holiday_payload()
    payload["animation_size"] = 5
    assert admin_client.put(f"/api/admin/holidays/{hid}", json=payload).status_code == 400
    payload["animation_size"] = 75
    resp = admin_client.put(f"/api/admin/holidays/{hid}", json=payload)
    assert resp.status_code == 200
    assert resp.json()["animation_size"] == 75


def test_audio_upload(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/audio",
        files={"file": ("theme.mp3", b"ID3_audio_bytes", "audio/mpeg")},
    )
    assert resp.status_code == 200
    url = resp.json()["audio_url"]
    assert url.endswith(".mp3")

    assert admin_client.delete(f"/api/admin/holidays/{hid}/audio").status_code == 200
    assert admin_client.get(f"/api/admin/holidays/{hid}").json()["audio_url"] is None


def test_audio_rejects_non_audio(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/audio",
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 400


def test_animation_upload_strips_grayish_background(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (60, 60), (230, 230, 230))
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, 44, 44], fill=(40, 40, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/animation",
        files={"file": ("gray.png", buf.getvalue(), "image/png")},
    )
    assert resp.status_code == 200

    from PIL import Image
    import os

    saved = Image.open(os.path.join(uploads_tmp, resp.json()["animation_url"].rsplit("/", 1)[-1])).convert("RGBA")
    assert saved.getpixel((2, 2))[3] == 0
    assert saved.getpixel((30, 30))[3] == 255


def test_animation_upload_keeps_dark_background(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (60, 60), (20, 10, 40))
    draw = ImageDraw.Draw(img)
    draw.ellipse([15, 15, 44, 44], fill=(240, 200, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/animation",
        files={"file": ("dark.png", buf.getvalue(), "image/png")},
    )
    assert resp.status_code == 200

    from PIL import Image
    import os

    saved = Image.open(os.path.join(uploads_tmp, resp.json()["animation_url"].rsplit("/", 1)[-1])).convert("RGBA")
    assert saved.getpixel((2, 2))[3] == 255


def test_trophy_image_upload(admin_client, uploads_tmp):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    resp = admin_client.post(
        f"/api/admin/holidays/{hid}/trophy-image",
        files={"file": ("cup.png", _white_bg_png((255, 200, 20)), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["trophy_image_url"].endswith(".png")
    assert admin_client.get(f"/api/admin/holidays/{hid}").json()["trophy_image_url"]

    assert admin_client.delete(f"/api/admin/holidays/{hid}/trophy-image").status_code == 200
    assert admin_client.get(f"/api/admin/holidays/{hid}").json()["trophy_image_url"] is None


def test_extra_cards_crud(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    cat_id = _create_category(admin_client, hid)

    extra = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Бонусная", "task_text": "только магазин", "is_trophy": False},
    ).json()
    assert extra["day"] is None
    assert extra["is_trophy"] is False

    trophy = admin_client.post(
        f"/api/admin/holidays/{hid}/extra-cards",
        json={"category_id": cat_id, "title": "Кубковая", "is_trophy": True},
    ).json()
    assert trophy["is_trophy"] is True
    assert trophy["day"] is None

    detail = admin_client.get(f"/api/admin/holidays/{hid}").json()
    titles = [c["title"] for c in detail["categories"][0]["cards"]]
    assert "Бонусная" in titles and "Кубковая" in titles

    upd = admin_client.put(
        f"/api/admin/holidays/{hid}/cards/{extra['id']}",
        json={"title": "Бонусная 2", "task_text": None, "is_trophy": True},
    ).json()
    assert upd["title"] == "Бонусная 2"
    assert upd["is_trophy"] is True

    assert admin_client.delete(f"/api/admin/holidays/{hid}/cards/{extra['id']}").status_code == 200

    day_card = [c for c in detail["categories"][0]["cards"] if c["day"]][0]
    resp = admin_client.delete(f"/api/admin/holidays/{hid}/cards/{day_card['id']}")
    assert resp.status_code == 400


def test_holiday_bg_color(admin_client):
    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload()).json()["id"]
    payload = _multi_day_holiday_payload()
    payload["bg_color"] = "#1b3a1b"
    resp = admin_client.put(f"/api/admin/holidays/{hid}", json=payload)
    assert resp.status_code == 200
    assert resp.json()["bg_color"] == "#1b3a1b"

    payload["bg_color"] = "   "
    resp = admin_client.put(f"/api/admin/holidays/{hid}", json=payload)
    assert resp.json()["bg_color"] is None
