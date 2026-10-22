import os

from tests.conftest import make_user_client
from tests.test_holidays import _png_bytes


def test_appearance_requires_auth(client):
    assert client.get("/api/appearance").status_code == 401


def test_appearance_empty_by_default(player_client):
    resp = player_client.get("/api/appearance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_bg_url"] is None
    assert data["collection_bg_url"] is None


def test_upload_game_bg(admin_client, uploads_tmp):
    resp = admin_client.post(
        "/api/admin/appearance/game_bg/image",
        files={"file": ("bg.png", _png_bytes((40, 20, 60)), "image/png")},
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("/api/uploads/appearance_game_bg")

    with make_user_client(123) as player:
        data = player.get("/api/appearance").json()
    assert data["game_bg_url"] == url
    assert data["collection_bg_url"] is None


def test_upload_collection_bg(admin_client, uploads_tmp):
    resp = admin_client.post(
        "/api/admin/appearance/collection_bg/image",
        files={"file": ("coll.png", _png_bytes((90, 60, 30)), "image/png")},
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("/api/uploads/appearance_collection_bg")

    data = admin_client.get("/api/appearance").json()
    assert data["collection_bg_url"] == url


def test_upload_replaces_old_file(admin_client, uploads_tmp):
    first = admin_client.post(
        "/api/admin/appearance/game_bg/image",
        files={"file": ("bg1.png", _png_bytes((1, 2, 3)), "image/png")},
    ).json()["url"]
    first_name = first.rsplit("/", 1)[-1]
    assert os.path.isfile(os.path.join(uploads_tmp, first_name))

    second = admin_client.post(
        "/api/admin/appearance/game_bg/image",
        files={"file": ("bg2.png", _png_bytes((4, 5, 6)), "image/png")},
    ).json()["url"]

    assert second != first
    assert not os.path.exists(os.path.join(uploads_tmp, first_name))
    assert admin_client.get("/api/appearance").json()["game_bg_url"] == second


def test_clear_appearance(admin_client, uploads_tmp):
    url = admin_client.post(
        "/api/admin/appearance/game_bg/image",
        files={"file": ("bg.png", _png_bytes(), "image/png")},
    ).json()["url"]
    name = url.rsplit("/", 1)[-1]
    assert os.path.isfile(os.path.join(uploads_tmp, name))

    assert admin_client.delete("/api/admin/appearance/game_bg/image").status_code == 200
    assert admin_client.get("/api/appearance").json()["game_bg_url"] is None
    assert not os.path.exists(os.path.join(uploads_tmp, name))


def test_upload_unknown_kind_404(admin_client, uploads_tmp):
    resp = admin_client.post(
        "/api/admin/appearance/unknown/image",
        files={"file": ("x.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 404


def test_upload_forbidden_for_player(player_client, uploads_tmp):
    resp = player_client.post(
        "/api/admin/appearance/game_bg/image",
        files={"file": ("bg.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 403


def test_admin_logs_requires_admin(player_client):
    assert player_client.get("/api/admin/logs").status_code == 403


def test_admin_logs_skip_401_and_info(raw_client, db):
    from models import Log

    assert raw_client.get("/api/me").status_code == 401

    rows = db.query(Log).all()
    assert all(r.status_code != 401 for r in rows)
    assert all(r.level != "info" for r in rows)


def test_auth_logs_do_not_leak_sign(raw_client, db):
    from models import Log

    resp = raw_client.post("/api/auth/session", json={"params": "not-a-dict", "sign": "SECRET-SIGN-123"})
    assert resp.status_code == 422

    rows = db.query(Log).filter(Log.path == "/api/auth/session").all()
    assert rows
    for row in rows:
        assert "SECRET-SIGN-123" not in (row.message or "")
        assert "SECRET-SIGN-123" not in (row.details or "")


def test_cleanup_old_logs_removes_expired(db):
    import datetime

    from models import Log
    from services.logging_svc import cleanup_old_logs

    old = Log(source="server", level="warn", message="old", created_at=datetime.datetime.utcnow() - datetime.timedelta(days=40))
    db.add(old)
    db.commit()
    old_id = old.id

    deleted = cleanup_old_logs(db, 30)
    assert deleted >= 1
    assert db.query(Log).filter(Log.id == old_id).count() == 0


def test_gate_misconfigured_flag(monkeypatch):
    import config
    from services.vk_group_member import gate_misconfigured

    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(config, "VK_SERVICE_TOKEN", "")
    monkeypatch.setattr(config, "VK_GROUP_ID", 0)
    assert gate_misconfigured() is True

    monkeypatch.setattr(config, "VK_SERVICE_TOKEN", "token")
    monkeypatch.setattr(config, "VK_GROUP_ID", 123)
    assert gate_misconfigured() is False


def test_admin_logs_lists_entries(admin_client):
    from tests.conftest import make_user_client

    with make_user_client(123) as player:
        player.get("/api/nonexistent-endpoint")

    resp = admin_client.get("/api/admin/logs")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    entry = rows[0]
    assert entry["path"] == "/api/nonexistent-endpoint"
    assert entry["status_code"] == 404
    assert entry["level"] == "warn"
    assert "created_at" in entry


def test_admin_logs_level_filter(admin_client):
    from tests.conftest import make_user_client

    with make_user_client(123) as player:
        player.get("/api/also-missing")

    errors = admin_client.get("/api/admin/logs?level=error").json()
    assert all(r["level"] == "error" for r in errors)
    warns = admin_client.get("/api/admin/logs?level=warn").json()
    assert len(warns) > 0
    assert any(r["path"] == "/api/also-missing" for r in warns)


def test_admin_logs_limit(admin_client):
    from tests.conftest import make_user_client

    with make_user_client(123) as player:
        for _ in range(5):
            player.get("/api/limit-probe")

    rows = admin_client.get("/api/admin/logs?limit=3").json()
    assert len(rows) == 3
