from __future__ import annotations
import time

import httpx

VK_TIMEOUT = 8
VK_API_VERSION = "5.199"
_NAME_CACHE: dict[int, dict] = {}
_NAME_MISS_CACHE: dict[int, float] = {}
_NAME_MISS_TTL = 300.0


def _vk_users_get(user_ids: str) -> list[dict] | None:
    import config
    from services.logging_svc import record_log

    if not config.VK_SERVICE_TOKEN or not user_ids:
        return None
    try:
        resp = httpx.post(
            "https://api.vk.ru/method/users.get",
            data={
                "user_ids": user_ids,
                "fields": "first_name,last_name",
                "lang": "ru",
                "access_token": config.VK_SERVICE_TOKEN,
                "v": VK_API_VERSION,
            },
            timeout=VK_TIMEOUT,
        )
    except Exception as e:
        record_log("vk", "error", event="vk_api", message=f"users.get failed: {e}")
        return None
    if resp.status_code != 200:
        record_log("vk", "error", event="vk_api", message=f"users.get http {resp.status_code}")
        return None
    try:
        body = resp.json()
    except ValueError:
        record_log("vk", "error", event="vk_api", message="users.get bad json")
        return None
    if "error" in body:
        record_log("vk", "error", event="vk_api", message=body["error"].get("error_msg", "vk error"))
        return None
    return body.get("response") or []


def resolve_vk_names(vk_ids: list[int]) -> dict[int, dict]:
    import config
    from services.logging_svc import record_log

    if not config.VK_SERVICE_TOKEN or not vk_ids:
        return {}

    now = time.monotonic()
    ids_to_request = []
    for x in vk_ids[:1000]:
        x = int(x)
        if x in _NAME_CACHE:
            continue
        miss_at = _NAME_MISS_CACHE.get(x)
        if miss_at is not None and now - miss_at < _NAME_MISS_TTL:
            continue
        ids_to_request.append(x)
    if not ids_to_request:
        return {k: dict(v) for k, v in _NAME_CACHE.items()}

    resolved: dict[int, dict] = {}
    for start in range(0, len(ids_to_request), 100):
        chunk = ids_to_request[start:start + 100]
        ids_str = ",".join(str(x) for x in chunk)
        users = _vk_users_get(ids_str)
        if users is None:
            record_log("vk", "warn", event="vk_api", message="users.get failed", details={"count": len(chunk)})
            continue
        returned = set()
        for u in users:
            uid = int(u["id"])
            returned.add(uid)
            resolved[uid] = {
                "first_name": u.get("first_name", ""),
                "last_name": u.get("last_name", ""),
            }
        for uid in chunk:
            if uid not in returned:
                _NAME_MISS_CACHE[uid] = now

    _NAME_CACHE.update(resolved)
    return {k: dict(v) for k, v in _NAME_CACHE.items()}


def vk_display_name(user) -> str:
    if user.display_name:
        return user.display_name
    full = ""
    try:
        nm = resolve_vk_names([user.vk_id]).get(user.vk_id, {})
        full = f"{nm.get('first_name', '')} {nm.get('last_name', '')}".strip()
    except Exception:
        full = ""
    return full or f"Игрок {user.vk_id}"
