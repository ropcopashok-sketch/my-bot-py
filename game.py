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

# фон подарка: (название, множитель цены, шанс в %)
BACKGROUNDS = {
    "plain":   ("Обычный", 1.0, 75),
    "neon":    ("Неон",    1.3, 18),
    "gold":    ("Золото",  2.0, 6),
    "rainbow": ("Радуга",  5.0, 1),
}

# кейсы: цена (0 = бесплатный по таймеру) и шансы редкостей в %
CASES = {
    "free":    {"title": "Бесплатный", "price": 0,    "odds": {"common": 80, "uncommon": 17, "rare": 3}},
    "basic":   {"title": "Базовый",    "price": 150,  "odds": {"common": 60, "uncommon": 30, "rare": 8.5,
                                                               "epic": 1.4, "legendary": 0.1}},
    "premium": {"title": "Премиум",    "price": 1200, "odds": {"uncommon": 40, "rare": 40, "epic": 17,
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
def item_value(gift: str, bg: str) -> int:
    return int(round(GIFTS[gift][3] * BACKGROUNDS[bg][1]))


def roll_background() -> str:
    keys = list(BACKGROUNDS)
    return rng.choices(keys, weights=[BACKGROUNDS[k][2] for k in keys])[0]


def roll_case(case: str) -> tuple[str, str]:
    """Возвращает (gift_id, background_id)."""
    odds = CASES[case]["odds"]
    tier = rng.choices(list(odds), weights=list(odds.values()))[0]
    gift = rng.choice([g for g, v in GIFTS.items() if v[2] == tier])
    return gift, roll_background()


def case_expected_value(case: str) -> float:
    """Средняя ценность выпадения (для проверки баланса)."""
    odds = CASES[case]["odds"]
    bg_mult = sum(b[1] * b[2] for b in BACKGROUNDS.values()) / 100
    total = 0.0
    for tier, pct in odds.items():
        vals = [v[3] for v in GIFTS.values() if v[2] == tier]
        total += pct / 100 * sum(vals) / len(vals)
    return total * bg_mult


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
    chance = upgrade_chance(input_value, item_value(target, "plain"))
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
        "backgrounds": {k: {"name": v[0], "mult": v[1], "pct": v[2]} for k, v in BACKGROUNDS.items()},
        "cases": CASES, "free_cooldown": FREE_CASE_COOLDOWN,
        "edge": UPGRADE_EDGE, "max_chance": UPGRADE_MAX_CHANCE, "min_chance": UPGRADE_MIN_CHANCE,
        "max_items": UPGRADE_MAX_ITEMS, "daily": DAILY_REWARDS, "start_coins": START_COINS,
        "ref_inviter": REF_BONUS_INVITER, "ref_invitee": REF_BONUS_INVITEE, "shop": SHOP,
    }
