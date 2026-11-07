from __future__ import annotations

import json

from models import RewardItem

REWARD_PRESETS = (
    {
        "preset_key": "penalty_half",
        "effect_type": "reduce_penalty",
        "title": "Смягчение штрафа",
        "description": "Уменьшает стоимость текущего штрафного задания на 50%.",
        "effect_config": {"percent": 50},
    },
    {
        "preset_key": "second_task",
        "effect_type": "extra_active_task",
        "title": "Второе задание",
        "description": "Позволяет держать два активных задания. Эффект заканчивается после сдачи одного из них.",
        "effect_config": {},
    },
    {
        "preset_key": "shop_always",
        "effect_type": "shop_always_open",
        "title": "Магазин всегда открыт",
        "description": "Открывает магазин не только по выходным — до начала нового праздника.",
        "effect_config": {},
    },
    {
        "preset_key": "shop_norm",
        "effect_type": "shop_without_penalty",
        "title": "Магазин без штрафа",
        "description": "До следующего праздника выкупленные карточки требуют обычную норму категории вместо 1000 крестиков.",
        "effect_config": {},
    },
    {
        "preset_key": "shop_free_card",
        "effect_type": "complete_shop_card",
        "title": "Выкуп без отшива",
        "description": "Мгновенно добавляет выбранную карточку из магазина в коллекцию без задания и отчёта.",
        "effect_config": {},
    },
    {
        "preset_key": "bestiary_egg",
        "effect_type": "external_bestiary_egg",
        "title": "Яйцо дракона в игру «Бестиарий»",
        "description": "Бронирует случайное яйцо по вашему VK ID. Оно появится сразу или при первом входе в «Бестиарий».",
        "effect_config": {},
    },
    {
        "preset_key": "zakaz_discount",
        "effect_type": "external_zakaz_discount",
        "title": "Единоразовая скидка в «Магазине игр»",
        "description": "Даёт скидку на один любой заказ в «Магазине игр» по вашему VK ID.",
        "effect_config": {"percent": 5},
    },
)


def ensure_reward_presets(db):
    existing = {row.preset_key: row for row in db.query(RewardItem).filter(RewardItem.preset_key.isnot(None)).all()}
    changed = False
    for preset in REWARD_PRESETS:
        item = existing.get(preset["preset_key"])
        if item is None:
            item = RewardItem(
                preset_key=preset["preset_key"],
                effect_type=preset["effect_type"],
                effect_config=json.dumps(preset["effect_config"], ensure_ascii=False),
                title=preset["title"],
                description=preset["description"],
                price_crystals=1,
                is_active=True,
            )
            db.add(item)
            changed = True
        elif item.effect_type != preset["effect_type"]:
            item.effect_type = preset["effect_type"]
            changed = True
    if changed:
        db.commit()


def config_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def config_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)
