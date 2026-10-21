from models import User
from tests.conftest import make_user_client


def test_me_requires_auth(client):
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_me_player(player_client):
    resp = player_client.get("/api/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vk_id"] == 123
    assert data["role"] == "player"
    assert data["status"] == "active"
    assert data["crystals"] == 0
    assert data["is_member"] is None


def test_me_admin(admin_client):
    resp = admin_client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_me_created_at_set(db):
    db.add(User(vk_id=42, role="player"))
    db.commit()
    with make_user_client(42) as c:
        resp = c.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["created_at"] is not None


def test_music_toggle(player_client):
    me = player_client.get("/api/me").json()
    assert me["music_enabled"] is True

    resp = player_client.put("/api/me/music", json={"music_enabled": False})
    assert resp.status_code == 200
    assert resp.json()["music_enabled"] is False
    assert player_client.get("/api/me").json()["music_enabled"] is False

    assert player_client.put("/api/me/music", json={"music_enabled": True}).json()["music_enabled"] is True
