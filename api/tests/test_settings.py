import config
import services.vk_group_member as member_svc
from models import Setting, User
from services.game_access import GAME_OPEN_KEY


def _set_game_open(db, value: bool) -> None:
    row = db.query(Setting).filter(Setting.key == GAME_OPEN_KEY).first()
    if row is None:
        db.add(Setting(key=GAME_OPEN_KEY, value="1" if value else "0"))
    else:
        row.value = "1" if value else "0"
    db.commit()


def _drop_game_open(db) -> None:
    db.query(Setting).filter(Setting.key == GAME_OPEN_KEY).delete()
    db.commit()


def test_closed_by_default_blocks_player_and_skips_registration(client, db):
    _drop_game_open(db)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 777}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "game_closed"
    assert db.query(User).filter(User.vk_id == 777).count() == 0


def test_closed_by_default_admin_enters(client, db):
    _drop_game_open(db)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
    assert db.query(User).filter(User.vk_id == 400977).count() == 1


def test_toggle_off_blocks_player_and_skips_registration(client, db):
    _set_game_open(db, False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 777}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "game_closed"
    assert db.query(User).filter(User.vk_id == 777).count() == 0


def test_open_allows_player_registration(client, db):
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 777}})
    assert resp.status_code == 200
    assert resp.json()["role"] == "player"
    assert db.query(User).filter(User.vk_id == 777).count() == 1


def test_game_closed_checked_before_members_only(client, db, monkeypatch):
    _set_game_open(db, False)
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 777}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "game_closed"


def test_me_player_token_blocked_when_closed(raw_client, db):
    token = raw_client.post("/api/auth/session", json={"params": {"vk_user_id": 123}}).json()["token"]
    _set_game_open(db, False)
    resp = raw_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "game_closed"


def test_me_admin_token_ok_when_closed(raw_client, db):
    token = raw_client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}}).json()["token"]
    _set_game_open(db, False)
    resp = raw_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_game_state_endpoints_forbidden_for_player(player_client):
    assert player_client.get("/api/admin/settings/game").status_code == 403
    assert player_client.put("/api/admin/settings/game", json={"game_open": False}).status_code == 403


def test_admin_reads_and_writes_game_state(admin_client, db):
    resp = admin_client.get("/api/admin/settings/game")
    assert resp.status_code == 200
    assert resp.json()["game_open"] is True

    resp = admin_client.put("/api/admin/settings/game", json={"game_open": False})
    assert resp.status_code == 200
    assert resp.json()["game_open"] is False
    assert db.query(Setting).filter(Setting.key == GAME_OPEN_KEY).first().value == "0"


def test_toggle_controls_login(client, admin_client, db):
    admin_client.put("/api/admin/settings/game", json={"game_open": False})
    assert client.post("/api/auth/session", json={"params": {"vk_user_id": 777}}).status_code == 403

    admin_client.put("/api/admin/settings/game", json={"game_open": True})
    assert client.post("/api/auth/session", json={"params": {"vk_user_id": 777}}).status_code == 200
