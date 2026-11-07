from __future__ import annotations

import httpx

import config


class IntegrationError(Exception):
    pass


def _post(url: str, key: str, payload: dict) -> dict:
    if not url or not key:
        raise IntegrationError("Интеграция пока не настроена администратором")
    try:
        response = httpx.post(url, json=payload, headers={"X-Integration-Key": key}, timeout=10)
    except httpx.HTTPError:
        raise IntegrationError("Не удалось связаться с другим приложением — попробуйте ещё раз")
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Внешнее приложение отклонило награду")
        except ValueError:
            detail = "Внешнее приложение отклонило награду"
        if not isinstance(detail, str):
            detail = detail.get("message", "Внешнее приложение отклонило награду")
        raise IntegrationError(detail)
    return response.json()


def apply_external_reward(effect_type: str, purchase_id: int, vk_id: int, payload: dict) -> dict:
    external_id = f"holidays:purchase:{purchase_id}"
    if effect_type == "external_bestiary_egg":
        return _post(
            f"{config.BESTIARY_API_URL}/api/internal/rewards/dragon-egg",
            config.BESTIARY_INTEGRATION_KEY,
            {"vk_id": vk_id, "external_reward_id": external_id},
        )
    if effect_type == "external_zakaz_discount":
        return _post(
            f"{config.ZAKAZ_API_URL}/api/internal/rewards/discount",
            config.ZAKAZ_INTEGRATION_KEY,
            {"vk_id": vk_id, "external_reward_id": external_id, "percent": payload.get("percent", 5)},
        )
    raise IntegrationError("Неизвестный тип внешней награды")


def revoke_external_reward(effect_type: str, purchase_id: int):
    external_id = f"holidays:purchase:{purchase_id}"
    if effect_type == "external_bestiary_egg":
        return _post(
            f"{config.BESTIARY_API_URL}/api/internal/rewards/dragon-egg/revoke",
            config.BESTIARY_INTEGRATION_KEY,
            {"external_reward_id": external_id},
        )
    if effect_type == "external_zakaz_discount":
        return _post(
            f"{config.ZAKAZ_API_URL}/api/internal/rewards/discount/revoke",
            config.ZAKAZ_INTEGRATION_KEY,
            {"external_reward_id": external_id},
        )
    return {"ok": True}
