from __future__ import annotations
import datetime

import httpx

import config

CACHE_TTL_HOURS = 24
VK_API_URL = "https://api.vk.com/method/groups.isMember"
VK_API_VERSION = "5.199"


def fetch_is_member(vk_id: int) -> bool | None:
    """Спрашивает VK API, подписан ли игрок на группу.

    Возвращает True/False, либо None — VK API недоступен или токен
    не настроен. None трактуется как fail-open: доступ не блокируем.
    """
    if not config.VK_SERVICE_TOKEN or not config.VK_GROUP_ID:
        return None
    try:
        resp = httpx.get(
            VK_API_URL,
            params={
                "group_id": config.VK_GROUP_ID,
                "user_id": vk_id,
                "v": VK_API_VERSION,
                "access_token": config.VK_SERVICE_TOKEN,
            },
            timeout=10,
        )
        data = resp.json()
    except Exception:
        return None
    if "error" in data:
        return None
    return data.get("response") in (1, True)


def _cache_fresh(user) -> bool:
    if user.member_cached_at is None:
        return False
    age = datetime.datetime.utcnow() - user.member_cached_at
    return age.total_seconds() < CACHE_TTL_HOURS * 3600


def refresh_membership(db, user) -> bool:
    value = fetch_is_member(user.vk_id)
    if value is None:
        return bool(user.is_member) if user.member_cached_at is not None else True
    user.is_member = value
    user.member_cached_at = datetime.datetime.utcnow()
    db.commit()
    return value


def get_membership(db, user) -> bool:
    """Членство с кэшем: не чаще одного запроса к VK API в сутки."""
    if _cache_fresh(user):
        return bool(user.is_member)
    return refresh_membership(db, user)
