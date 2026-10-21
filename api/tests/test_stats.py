

def test_daily_stats_requires_admin(player_client):
    assert player_client.get("/api/admin/stats/daily").status_code == 403


def test_daily_stats_counts_cards(admin_client, db):
    from models import UserCard
    from services.msk_time import now_msk

    hid, card_ids = _finished_holiday(admin_client, cards=("Тыква",))
    today = now_msk().date().isoformat()
    for uid in (123, 124, 125):
        db.add(UserCard(user_id=uid, card_id=card_ids[0]))
    db.commit()

    resp = admin_client.get(f"/api/admin/stats/daily?day={today}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["day"] == today
    assert data["total_players"] == 3
    row = [r for r in data["rows"] if r["card_id"] == card_ids[0]][0]
    assert row["count"] == 3
    assert row["title"] == "Тыква"

    empty = admin_client.get("/api/admin/stats/daily?day=2020-01-01").json()
    assert empty["rows"] == []
    assert empty["total_players"] == 0

    bad = admin_client.get("/api/admin/stats/daily?day=01-01-2020")
    assert bad.status_code == 400


from tests.test_shop import _finished_holiday  # noqa: E402
