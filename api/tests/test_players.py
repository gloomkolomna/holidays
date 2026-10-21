

def test_players_requires_admin(player_client):
    assert player_client.get("/api/admin/players").status_code == 403


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
