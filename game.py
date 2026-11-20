"""GIFT LAB — логика игры: кейсы, апгрейд подарков, продажа, награды.

Сервер — источник истины: все случайные числа выпадают здесь,
клиент только показывает анимацию уже известного результата.
Такая же логика продублирована в index.html для офлайн-демо.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

rng = random.SystemRandom()  # криптостойкий генератор — результат не предсказать

# ---------------------------------------------------------------- редкости
TIERS = {
    "common":    {"title": "Обычный",     "color": "#9ca3af"},
    "uncommon":  {"title": "Необычный",   "color": "#22c55e"},
    "rare":      {"title": "Редкий",      "color": "#3b82f6"},
    "epic":      {"title": "Эпический",   "color": "#a855f7"},
    "legendary": {"title": "Легендарный", "color": "#f59e0b"},
}

# ---------------------------------------------------------------- подарки
# id: (название, эмодзи, редкость, базовая цена в кристаллах)
GIFTS = {
    "bear":    ("Мишка",          "🧸", "common",    10),
    "rose":    ("Роза",           "🌹", "common",    15),
    "candy":   ("Леденец",        "🍭", "common",    20),
    "balloon": ("Шарик",          "🎈", "common",    25),
    "clover":  ("Клевер",         "🍀", "common",    30),
    "bouquet": ("Букет",          "💐", "uncommon",  60),
    "cake":    ("Торт",           "🎂", "uncommon",  80),
    "potion":  ("Зелье",          "🧪", "uncommon", 100),
    "box":     ("Сюрприз",        "🎁", "uncommon", 120),
    "ring":    ("Кольцо",         "💍", "rare",     250),
    "orb":     ("Шар судьбы",     "🔮", "rare",     350),
    "guitar":  ("Гитара",         "🎸", "rare",     450),
    "crown":   ("Корона",         "👑", "epic",    1000),
    "unicorn": ("Единорог",       "🦄", "epic",    1600),
    "dragon":  ("Дракон",         "🐉", "epic",    2500),
    "rocket":  ("Ракета",         "🚀", "legendary", 6000),
    "galaxy":  ("Галактика",      "🌌", "legendary", 12000),
    "trophy":  ("Кубок чемпиона", "🏆", "legendary", 25000),
}

# ---------------------------------------------------------------- атрибуты подарка
# Каждый экземпляр = подарок + модель + фон + узор. У каждой части свой шанс (%)
# и множитель цены. Цена экземпляра = базовая цена × все три множителя.

# модель: (название, множитель, шанс %)
MODELS = {
    "classic": ("Классика", 1.0, 70),
    "neon":    ("Неон",     1.3, 15),
    "ice":     ("Лёд",      1.6, 8),
    "shadow":  ("Тень",     2.0, 4.5),
    "gold":    ("Золото",   3.0, 2),
    "rainbow": ("Радуга",   5.0, 0.5),
}

# фон: (название, множитель, шанс %, цвет центра, цвет края, цвет узора)
BACKDROPS = {
    "midnight": ("Полночь",  1.0, 30,  "#3b4a8c", "#141a3a", "#8ea2ff"),
    "sapphire": ("Сапфир",   1.0, 20,  "#2f7fd8", "#0d2a5c", "#9fd0ff"),
    "emerald":  ("Изумруд",  1.0, 15,  "#2fae7a", "#0b3d2c", "#9cf2c9"),
    "ruby":     ("Рубин",    1.1, 12,  "#d8475e", "#4a0f1d", "#ffb0bd"),
    "amethyst": ("Аметист",  1.1, 10,  "#9b5de5", "#2e1452", "#e0c3ff"),
    "amber":    ("Янтарь",   1.2, 7,   "#e8a33a", "#5a2f05", "#ffe0a3"),
    "mint":     ("Мята",     1.3, 4,   "#5fe0c8", "#0f4a46", "#d2fff6"),
    "onyx":     ("Оникс",    1.6, 1.5, "#4a4a52", "#08080a", "#c9c9d6"),
    "aurora":   ("Аврора",   2.5, 0.5, "#ff6ad5", "#2a0b5c", "#ffffff"),
}

# узор вокруг подарка: (название, множитель, шанс %)
PATTERNS = {
    "stars":    ("Звёзды",     1.0,  30),
    "hearts":   ("Сердца",     1.0,  25),
    "sparkles": ("Искры",      1.0,  20),
    "bolts":    ("Молнии",     1.05, 12),
    "moons":    ("Луны",       1.1,  8),
    "diamonds": ("Бриллианты", 1.2,  4),
    "crowns":   ("Короны",     1.5,  1),
}

# кейсы: цена (0 = бесплатный по таймеру) и шансы редкостей в %
CASES = {
    "free":    {"title": "Бесплатный", "price": 0,    "odds": {"common": 80, "uncommon": 17, "rare": 3}},
    "basic":   {"title": "Базовый",    "price": 170,  "odds": {"common": 60, "uncommon": 30, "rare": 8.5,
                                                               "epic": 1.4, "legendary": 0.1}},
    "premium": {"title": "Премиум",    "price": 1400, "odds": {"uncommon": 40, "rare": 40, "epic": 17,
                                                               "legendary": 3}},
}
FREE_CASE_COOLDOWN = 4 * 3600

# апгрейд
UPGRADE_EDGE = 0.08        # 8% «налог» игры — иначе кристаллы бесконечно множатся
UPGRADE_MAX_CHANCE = 0.75
UPGRADE_MIN_CHANCE = 0.01
UPGRADE_MAX_ITEMS = 6

START_COINS = 300
DAILY_REWARDS = [100, 150, 250, 400, 600, 900, 1500]
REF_BONUS_INVITER = 500
REF_BONUS_INVITEE = 250

# покупка кристаллов за Telegram Stars (вывода денег нет — это не казино)
SHOP = {
    "pack_s": {"title": "1 000 кристаллов",  "coins": 1_000,  "stars": 15},
    "pack_m": {"title": "4 000 кристаллов",  "coins": 4_000,  "stars": 50},
    "pack_l": {"title": "15 000 кристаллов", "coins": 15_000, "stars": 150},
}


# ---------------------------------------------------------------- помощники
def _pick(table: dict, pct_index: int, only_base: bool = False) -> str:
    keys = [k for k, v in table.items() if not only_base or v[1] == 1.0]
    return rng.choices(keys, weights=[table[k][pct_index] for k in keys])[0]


def base_value(gift: str) -> int:
    return GIFTS[gift][3]


def item_value(gift: str, model: str = "classic", bg: str = "midnight", pattern: str = "stars") -> int:
    m = MODELS.get(model, MODELS["classic"])[1]
    b = BACKDROPS.get(bg, BACKDROPS["midnight"])[1]
    p = PATTERNS.get(pattern, PATTERNS["stars"])[1]
    return int(round(GIFTS[gift][3] * m * b * p))


def roll_looks(only_base: bool = False) -> dict:
    """Случайные модель, фон и узор. only_base — только варианты без наценки (для апгрейда)."""
    return {
        "model": "classic" if only_base else _pick(MODELS, 2),
        "bg": _pick(BACKDROPS, 2, only_base),
        "pattern": _pick(PATTERNS, 2, only_base),
    }


def roll_case(case: str) -> dict:
    """Возвращает {gift, model, bg, pattern}."""
    odds = CASES[case]["odds"]
    tier = rng.choices(list(odds), weights=list(odds.values()))[0]
    gift = rng.choice([g for g, v in GIFTS.items() if v[2] == tier])
    return {"gift": gift, **roll_looks()}


def _avg_mult(table: dict) -> float:
    return sum(v[1] * v[2] for v in table.values()) / sum(v[2] for v in table.values())


def case_expected_value(case: str) -> float:
    """Средняя ценность выпадения (для проверки баланса)."""
    odds = CASES[case]["odds"]
    looks = _avg_mult(MODELS) * _avg_mult(BACKDROPS) * _avg_mult(PATTERNS)
    total = 0.0
    for tier, pct in odds.items():
        vals = [v[3] for v in GIFTS.values() if v[2] == tier]
        total += pct / 100 * sum(vals) / len(vals)
    return total * looks


def is_rare_drop(it: dict) -> bool:
    """Попадает ли выпадение в общую ленту."""
    return (GIFTS[it["gift"]][2] in ("epic", "legendary") or MODELS[it["model"]][2] <= 2
            or BACKDROPS[it["bg"]][2] <= 1.5 or PATTERNS[it["pattern"]][2] <= 1)


def upgrade_chance(input_value: int, target_value: int) -> float:
    if target_value <= input_value or input_value <= 0:
        return 0.0
    chance = input_value / target_value * (1 - UPGRADE_EDGE)
    if chance < UPGRADE_MIN_CHANCE:
        return 0.0  # слишком большой разрыв — запрещаем, а не округляем шанс вверх
    return min(UPGRADE_MAX_CHANCE, chance)


def do_upgrade(input_value: int, target: str) -> dict:
    """Крутит колесо. roll — куда остановилась стрелка (0..1), выигрыш если roll < chance."""
    if target not in GIFTS:
        return {"error": "Нет такого подарка"}
    chance = upgrade_chance(input_value, base_value(target))
    if chance == 0:
        return {"error": "Цель должна быть дороже, но шанс — не меньше 1%"}
    roll = rng.random()
    return {"win": roll < chance, "roll": roll, "chance": chance}


def claim_daily(streak: int, last_daily: str, today: date | None = None) -> tuple[int, int, str]:
    """Возвращает (награда, новая серия, новая дата). Награда 0 — уже забирали."""
    today = today or date.today()
    if last_daily == today.isoformat():
        return 0, streak, last_daily
    yesterday = (today - timedelta(days=1)).isoformat()
    streak = streak + 1 if last_daily == yesterday else 1
    return DAILY_REWARDS[min(streak, len(DAILY_REWARDS)) - 1], streak, today.isoformat()


def config() -> dict:
    return {
        "tiers": TIERS,
        "gifts": {k: {"name": v[0], "emoji": v[1], "tier": v[2], "value": v[3]} for k, v in GIFTS.items()},
        "models": {k: {"name": v[0], "mult": v[1], "pct": v[2]} for k, v in MODELS.items()},
        "backdrops": {k: {"name": v[0], "mult": v[1], "pct": v[2], "c1": v[3], "c2": v[4], "pc": v[5]}
                      for k, v in BACKDROPS.items()},
        "patterns": {k: {"name": v[0], "mult": v[1], "pct": v[2]} for k, v in PATTERNS.items()},
        "cases": CASES, "free_cooldown": FREE_CASE_COOLDOWN,
        "edge": UPGRADE_EDGE, "max_chance": UPGRADE_MAX_CHANCE, "min_chance": UPGRADE_MIN_CHANCE,
        "max_items": UPGRADE_MAX_ITEMS, "daily": DAILY_REWARDS, "start_coins": START_COINS,
        "ref_inviter": REF_BONUS_INVITER, "ref_invitee": REF_BONUS_INVITEE, "shop": SHOP,
    }


# ---------------------------------------------------------------- синхронизация с index.html
def sync_index(path: str = "index.html") -> None:
    """Вписывает актуальный config() в офлайн-копию CFG внутри index.html.
    Запускай `python game.py` после любых изменений баланса."""
    import json
    from pathlib import Path
    p = Path(__file__).with_name(path)
    html = p.read_text(encoding="utf-8")
    start, end = "/*CFG-START*/", "/*CFG-END*/"
    a, b = html.index(start) + len(start), html.index(end)
    p.write_text(html[:a] + json.dumps(config(), ensure_ascii=False) + html[b:], encoding="utf-8")
    print(f"{path}: конфиг обновлён")


if __name__ == "__main__":
    sync_index()
