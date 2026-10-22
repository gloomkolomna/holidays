

def test_players_requires_admin(player_client):
    assert player_client.get("/api/admin/players").status_code == 403
    assert player_client.get("/api/admin/players/123").status_code == 403


def test_players_search_requires_admin(player_client):
    assert player_client.get("/api/admin/players", params={"search": "а"}).status_code == 403


def test_players_search_case_insensitive(admin_client, db):
    from models import User as U

    db.add(U(vk_id=123, role="player", display_name="Анна Петрова"))
    db.add(U(vk_id=124, role="player", display_name="Ivan Ivanov"))
    db.add(U(vk_id=125, role="player"))
    db.commit()

    def ids(q):
        return sorted(p["vk_id"] for p in admin_client.get("/api/admin/players", params={"search": q}).json())

    assert ids("анн") == [123]
    assert ids("АНН") == [123]
    assert ids("петрова") == [123]
    assert ids("IVAN") == [124]
    assert ids("12") == [123, 124, 125]
    assert ids("игрок 125") == [125]
    assert ids("нет такого") == []


def test_player_detail_not_found(admin_client):
    assert admin_client.get("/api/admin/players/999").status_code == 404


def test_player_detail_with_task_and_collection(admin_client, db, uploads_tmp):
    from models import Task, User as U, UserCard as UC
    from tests.test_holidays import _multi_day_holiday_payload

    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Праздник Б")).json()["id"]
    admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Кат", "norm_crosses": 300})
    slots = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]
    card_ids = [
        admin_client.put(
            f"/api/admin/holidays/{hid}/cards/{slot['id']}",
            json={"title": "К-" + slot["day"]},
        ).json()["id"]
        for slot in slots[:2]
    ]

    db.add(U(vk_id=123, role="player", display_name="Анна"))
    db.add(Task(user_id=123, holiday_id=hid, card_id=card_ids[0], kind="daily", required_crosses=300))
    db.add(UC(user_id=123, card_id=card_ids[1]))
    db.commit()

    resp = admin_client.get("/api/admin/players/123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player"]["display_name"] == "Анна"
    assert data["player"]["cards_total"] == 1

    task = data["active_task"]
    assert task is not None
    assert task["kind"] == "daily"
    assert task["required_crosses"] == 300
    assert task["holiday_title"] == "Праздник Б"
    assert task["card_title"].startswith("К-")

    assert [c["card_id"] for c in data["cards"]] == [card_ids[1]]
    assert data["cards"][0]["category_title"] == "Кат"
    assert data["cards"][0]["holiday_title"] == "Праздник Б"
    assert data["cards"][0]["source"] == "daily"


def test_player_detail_without_task(admin_client, db):
    from models import User as U

    db.add(U(vk_id=130, role="player", display_name="Пётр"))
    db.commit()

    data = admin_client.get("/api/admin/players/130").json()
    assert data["active_task"] is None
    assert data["cards"] == []


def test_players_list_with_collections(admin_client, db, uploads_tmp):
    from models import User as U, UserCard as UC
    from tests.test_holidays import _multi_day_holiday_payload, _png_bytes

    hid = admin_client.post("/api/admin/holidays", json=_multi_day_holiday_payload("Праздник А")).json()["id"]
    admin_client.post(f"/api/admin/holidays/{hid}/categories", json={"title": "Кат", "norm_crosses": 300})
    slots = admin_client.get(f"/api/admin/holidays/{hid}").json()["categories"][0]["cards"]
    card_ids = []
    for slot in slots[:2]:
        card = admin_client.put(f"/api/admin/holidays/{hid}/cards/{slot['id']}", json={"title": "К-" + slot["day"]}).json()
        card_ids.append(card["id"])

    db.add(U(vk_id=123, role="player", display_name="Анна"))
    db.add(U(vk_id=124, role="player"))
    db.add(UC(user_id=123, card_id=card_ids[0]))
    db.commit()

    resp = admin_client.get("/api/admin/players")
    assert resp.status_code == 200
    players = {p["vk_id"]: p for p in resp.json()}
    assert {123, 124}.issubset(set(players))
    assert players[123]["display_name"] == "Анна"
    assert players[124]["display_name"] == "Игрок 124"

    coll_a = [c for c in players[123]["collections"] if c["holiday_id"] == hid][0]
    assert coll_a["collected"] == 1
    assert coll_a["total"] == 2
    assert coll_a["full"] is False
    assert players[123]["cards_total"] == 1


def test_auth_resolves_vk_name(client, db, monkeypatch):
    import services.vk_names as vk_names

    monkeypatch.setattr(
        vk_names, "resolve_vk_names",
        lambda ids: {777: {"first_name": "Ольга", "last_name": "Иванова"}},
    )
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 777}})
    assert resp.status_code == 200

    from models import User

    user = db.query(User).filter(User.vk_id == 777).first()
    assert user is not None
    assert user.display_name == "Ольга Иванова"
