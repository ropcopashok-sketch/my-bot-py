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
    "legendary": {"title": "Коллекционный", "color": "#f59e0b"},
}

# ---------------------------------------------------------------- подарки
# Цены как у подарков в Telegram: 1 ⭐ = 1 💎.
# id: (название, эмодзи, редкость, базовая цена в кристаллах)
GIFTS = {
    # обычные подарки — тот же набор и те же цены, что в Telegram (рисунки свои)
    "heart":     ("Сердце",      "💝", "common",     15),
    "bear":      ("Мишка",       "🧸", "common",     15),
    "box":       ("Подарок",     "🎁", "uncommon",   25),
    "rose":      ("Роза",        "🌹", "uncommon",   25),
    "cake":      ("Торт",        "🎂", "rare",       50),
    "bouquet":   ("Букет",       "💐", "rare",       50),
    "rocket":    ("Ракета",      "🚀", "rare",       50),
    "champagne": ("Шампанское",  "🍾", "rare",       50),
    "trophy":    ("Кубок",       "🏆", "epic",      100),
    "ring":      ("Кольцо",      "💍", "epic",      100),
    "diamond":   ("Алмаз",       "💎", "epic",      100),
    # коллекционные — свои, как «маркет»-подарки в Telegram (от 443)
    "candy":     ("Леденец",     "🍭", "legendary", 443),
    "balloon":   ("Шарик",       "🎈", "legendary", 443),
    "clover":    ("Клевер",      "🍀", "legendary", 443),
    "potion":    ("Зелье",       "🧪", "legendary", 443),
    "orb":       ("Шар судьбы",  "🔮", "legendary", 520),
    "guitar":    ("Гитара",      "🎸", "legendary", 600),
    "crown":     ("Корона",      "👑", "legendary", 759),
    "unicorn":   ("Единорог",    "🦄", "legendary", 900),
    "dragon":    ("Дракон",      "🐉", "legendary", 1200),
    "galaxy":    ("Галактика",   "🌌", "legendary", 1500),
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
    "free":    {"title": "Бесплатный", "price": 0,   "odds": {"common": 85, "uncommon": 15}},
    "basic":   {"title": "Базовый",    "price": 45,  "odds": {"common": 50, "uncommon": 34, "rare": 13,
                                                              "epic": 2.6, "legendary": 0.4}},
    "premium": {"title": "Премиум",    "price": 250, "odds": {"rare": 45, "epic": 43, "legendary": 12}},
}
FREE_CASE_COOLDOWN = 24 * 3600

# апгрейд
UPGRADE_EDGE = 0.08        # 8% «налог» игры — иначе кристаллы бесконечно множатся
UPGRADE_MAX_CHANCE = 0.75
UPGRADE_MIN_CHANCE = 0.01
UPGRADE_MAX_ITEMS = 6

START_COINS = 50
DAILY_REWARDS = [5, 10, 15, 20, 30, 40, 60]
REF_BONUS_INVITER = 25
REF_BONUS_INVITEE = 15

# покупка кристаллов за Telegram Stars (вывода денег нет — это не казино)
SHOP = {  # 1 ⭐ = 1 💎
    "pack_50":   {"title": "50 кристаллов",    "coins": 50,    "stars": 50},
    "pack_100":  {"title": "100 кристаллов",   "coins": 100,   "stars": 100},
    "pack_250":  {"title": "250 кристаллов",   "coins": 250,   "stars": 250},
    "pack_500":  {"title": "500 кристаллов",   "coins": 500,   "stars": 500},
    "pack_1000": {"title": "1 000 кристаллов", "coins": 1_000, "stars": 1_000},
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
