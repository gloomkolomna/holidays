import datetime

import config
import services.vk_group_member as member_svc
from models import User
from services.vk_sign import _calc_sign
from tests.conftest import make_user_client


def test_health(client):
    resp = client.get("/api/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "holidays-api"


def test_session_requires_vk_user_id(client):
    resp = client.post("/api/auth/session", json={"params": {}})
    assert resp.status_code == 401


def test_session_dev_login_creates_player(client, db):
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 123}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["vk_id"] == 123
    assert data["role"] == "player"
    assert data["token"]
    assert db.query(User).filter(User.vk_id == 123).count() == 1


def test_session_admin_gets_admin_role(client):
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_session_idempotent(client, db):
    for _ in range(2):
        resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 123}})
        assert resp.status_code == 200
    assert db.query(User).filter(User.vk_id == 123).count() == 1


def test_session_promotes_existing_to_admin(client, db):
    client.post("/api/auth/session", json={"params": {"vk_user_id": 123}})
    client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}})
    user = db.query(User).filter(User.vk_id == 123).first()
    assert user.role == "player"
    admin = db.query(User).filter(User.vk_id == 400977).first()
    assert admin.role == "admin"


def test_session_blocked_user_rejected(client, db):
    db.add(User(vk_id=321, role="player", status="blocked"))
    db.commit()
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 321}})
    assert resp.status_code == 403
    assert "заблокирован" in resp.json()["detail"]


def _signed_params(vk_user_id: int) -> dict:
    params = {"vk_user_id": str(vk_user_id), "vk_app_id": "777"}
    pairs = sorted((k, v) for k, v in params.items())
    query = "&".join(f"{k}={v}" for k, v in pairs)
    params["sign"] = _calc_sign(query)
    return params


def test_session_correct_signature(client, monkeypatch):
    monkeypatch.setattr(config, "DEV_LOGIN_ENABLED", False)
    resp = client.post("/api/auth/session", json={"params": _signed_params(123)})
    assert resp.status_code == 200
    assert resp.json()["vk_id"] == 123


def test_session_wrong_signature(client, monkeypatch):
    monkeypatch.setattr(config, "DEV_LOGIN_ENABLED", False)
    params = _signed_params(123)
    params["sign"] = "invalid-sign"
    resp = client.post("/api/auth/session", json={"params": params})
    assert resp.status_code == 401


def test_member_gate_blocks_new_user(client, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 555}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "members_only"


def test_member_gate_allows_member(client, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: True)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 555}})
    assert resp.status_code == 200


def test_member_gate_admin_bypasses(client, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_member_gate_existing_user_cached_member(client, db, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    db.add(User(
        vk_id=556, role="player",
        is_member=True, member_cached_at=datetime.datetime.utcnow(),
    ))
    db.commit()
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 556}})
    assert resp.status_code == 200


def test_member_gate_existing_user_stale_cache_refetch(client, db, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    db.add(User(
        vk_id=557, role="player",
        is_member=True, member_cached_at=datetime.datetime.utcnow() - datetime.timedelta(days=2),
    ))
    db.commit()
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 557}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "members_only"


def test_member_gate_failopen_when_vk_api_unavailable(client, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: None)
    resp = client.post("/api/auth/session", json={"params": {"vk_user_id": 558}})
    assert resp.status_code == 200


def test_me_member_gate_lazy_recheck_blocks(raw_client, db, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: True)
    token = raw_client.post("/api/auth/session", json={"params": {"vk_user_id": 123}}).json()["token"]
    user = db.query(User).filter(User.vk_id == 123).first()
    user.is_member = False
    user.member_cached_at = datetime.datetime.utcnow()
    db.commit()
    resp = raw_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "members_only"


def test_me_member_gate_lazy_recheck_refetch(raw_client, db, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: True)
    token = raw_client.post("/api/auth/session", json={"params": {"vk_user_id": 124}}).json()["token"]
    user = db.query(User).filter(User.vk_id == 124).first()
    user.is_member = True
    user.member_cached_at = datetime.datetime.utcnow() - datetime.timedelta(days=2)
    db.commit()
    monkeypatch.setattr(member_svc, "fetch_is_member", lambda vk_id: False)
    resp = raw_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    user = db.query(User).filter(User.vk_id == 124).first()
    assert user.is_member is False


def test_me_member_gate_admin_bypasses(raw_client, monkeypatch):
    monkeypatch.setattr(config, "MEMBER_GATE_ENABLED", True)

    def _unexpected(vk_id):
        raise AssertionError("VK API не должен вызываться для admin")

    monkeypatch.setattr(member_svc, "fetch_is_member", _unexpected)
    token = raw_client.post("/api/auth/session", json={"params": {"vk_user_id": 400977}}).json()["token"]
    resp = raw_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
