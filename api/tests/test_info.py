def test_info_requires_auth(client):
    assert client.get("/api/info").status_code == 401


def test_info_requires_admin_for_put(player_client):
    assert player_client.put("/api/admin/info", json={"blocks": []}).status_code == 403


def test_info_default_blocks(player_client):
    data = player_client.get("/api/info").json()
    assert len(data["blocks"]) == 2
    assert data["blocks"][0]["title"] == "🧵 Пересчёт для полукреста"
    assert "500 крестиков = 750 полукрестов" in data["blocks"][0]["text"]
    assert data["blocks"][1]["title"] == "🔑 Кодовое слово"
    assert data["blocks"][1]["text"] == "Кодовое слово — название карточки"


def test_info_save_and_read(admin_client):
    from tests.conftest import make_user_client

    blocks = [
        {"title": "Новый блок", "text": "строка 1\nстрока 2"},
        {"title": "🧵 Пересчёт для полукреста", "text": "норма ×1,5"},
    ]
    resp = admin_client.put("/api/admin/info", json={"blocks": blocks})
    assert resp.status_code == 200
    assert [b["title"] for b in resp.json()["blocks"]] == ["Новый блок", "🧵 Пересчёт для полукреста"]

    with make_user_client(123) as player:
        data = player.get("/api/info").json()
    assert data["blocks"][0]["text"] == "строка 1\nстрока 2"


def test_info_reject_empty_list(admin_client):
    resp = admin_client.put("/api/admin/info", json={"blocks": []})
    assert resp.status_code == 400


def test_info_reject_empty_title(admin_client):
    resp = admin_client.put("/api/admin/info", json={"blocks": [{"title": "", "text": "текст"}]})
    assert resp.status_code == 422
