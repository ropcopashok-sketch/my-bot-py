"""Игровая логика RGB ELITE: Neon Core.

Сервер — источник истины: клиент только присылает, сколько раз тапнул,
а начисления, энергия и покупки считаются здесь. Такая же логика
продублирована в index.html для офлайн-режима (без сервера).
"""
from __future__ import annotations

import time
from datetime import date, timedelta

# ---------------------------------------------------------------- баланс игры
BASE_ENERGY = 500          # стартовый запас энергии
ENERGY_PER_LEVEL = 250     # +энергии за уровень «Батарея»
ENERGY_REGEN = 2.0         # восстановление энергии в секунду
MAX_TAPS_PER_SEC = 20      # защита от автокликеров
MAX_COMBO = 3              # максимальный множитель комбо
OFFLINE_CAP_SEC = 3 * 3600 # пассивный доход копится максимум 3 часа
TURBO_MULT = 2             # множитель «Турбо»
REF_BONUS_INVITER = 1000
REF_BONUS_INVITEE = 500

UPGRADES = {
    "tap":  {"title": "Сила тапа",  "desc": "+1 кристалл за тап",       "base": 50,  "growth": 1.6, "max": 30},
    "cap":  {"title": "Батарея",    "desc": f"+{ENERGY_PER_LEVEL} к энергии", "base": 100, "growth": 1.7, "max": 20},
    "auto": {"title": "Авто-майнер", "desc": "+0.5 кристалла в секунду", "base": 200, "growth": 1.8, "max": 40},
}

LEAGUES = [  # (порог total_earned, название)
    (0, "Бронза"), (5_000, "Серебро"), (25_000, "Золото"),
    (100_000, "Платина"), (500_000, "Алмаз"), (2_000_000, "RGB Элита"),
]

DAILY_REWARDS = [500, 1000, 2000, 3500, 5000, 7500, 12000]  # дни 1..7 подряд

SHOP = {  # покупки за Telegram Stars (XTR)
    "turbo":  {"title": "Турбо x2 на 1 час", "desc": "Все тапы и пассивный доход x2 целый час", "stars": 25},
    "refill": {"title": "Полная энергия",     "desc": "Мгновенно восстанавливает всю энергию",  "stars": 10},
    "pack":   {"title": "Мешок кристаллов",   "desc": "+50 000 кристаллов сразу",               "stars": 50},
}


def upgrade_cost(key: str, level: int) -> int:
    u = UPGRADES[key]
    return int(u["base"] * u["growth"] ** level)


def max_energy(s: dict) -> int:
    return BASE_ENERGY + ENERGY_PER_LEVEL * s["cap_lvl"]


def tap_power(s: dict) -> int:
    return 1 + s["tap_lvl"]


def auto_rate(s: dict) -> float:
    return 0.5 * s["auto_lvl"]


def league(total: float) -> str:
    name = LEAGUES[0][1]
    for threshold, title in LEAGUES:
        if total >= threshold:
            name = title
    return name


def new_state(now: float | None = None) -> dict:
    now = now or time.time()
    return {
        "coins": 0.0, "total": 0.0,
        "energy": float(BASE_ENERGY), "ts": now,
        "tap_lvl": 0, "cap_lvl": 0, "auto_lvl": 0,
        "turbo_until": 0.0, "streak": 0, "last_daily": "",
    }


def _earn(s: dict, amount: float) -> None:
    s["coins"] += amount
    s["total"] += amount


def tick(s: dict, now: float | None = None) -> float:
    """Начисляет восстановление энергии и пассивный доход с момента s['ts'].
    Возвращает, сколько кристаллов принёс авто-майнер."""
    now = now or time.time()
    dt = max(0.0, now - s["ts"])
    s["energy"] = min(max_energy(s), s["energy"] + dt * ENERGY_REGEN)
    passive_dt = min(dt, OFFLINE_CAP_SEC)
    mult = TURBO_MULT if s["turbo_until"] > now else 1
    gained = auto_rate(s) * passive_dt * mult
    _earn(s, gained)
    s["ts"] = now
    return gained


def apply_taps(s: dict, taps: int, combo_taps: dict[int, int] | None, elapsed: float,
               now: float | None = None) -> float:
    """taps — всего тапов; combo_taps — {множитель: сколько тапов с ним}.
    Всё, что не влезает в лимиты, отбрасывается."""
    now = now or time.time()
    tick(s, now)
    taps = max(0, int(taps))
    taps = min(taps, int(s["energy"]), int(max(elapsed, 1) * MAX_TAPS_PER_SEC))
    if taps == 0:
        return 0.0
    # раскладываем тапы по множителям, но не больше чем taps суммарно
    remaining = taps
    weighted = 0
    for mult, n in sorted((combo_taps or {}).items(), reverse=True):
        mult = max(1, min(MAX_COMBO, int(mult)))
        n = max(0, min(int(n), remaining))
        weighted += mult * n
        remaining -= n
    weighted += remaining  # оставшиеся тапы — без комбо
    turbo = TURBO_MULT if s["turbo_until"] > now else 1
    gained = weighted * tap_power(s) * turbo
    s["energy"] -= taps
    _earn(s, gained)
    return gained


def buy_upgrade(s: dict, key: str, now: float | None = None) -> str | None:
    """Возвращает текст ошибки или None при успехе."""
    if key not in UPGRADES:
        return "Нет такого улучшения"
    tick(s, now)
    lvl_key = f"{key}_lvl"
    if s[lvl_key] >= UPGRADES[key]["max"]:
        return "Максимальный уровень"
    cost = upgrade_cost(key, s[lvl_key])
    if s["coins"] < cost:
        return "Не хватает кристаллов"
    s["coins"] -= cost
    s[lvl_key] += 1
    return None


def claim_daily(s: dict, today: date | None = None) -> int:
    """Возвращает награду (0, если сегодня уже забирали)."""
    today = today or date.today()
    if s["last_daily"] == today.isoformat():
        return 0
    yesterday = (today - timedelta(days=1)).isoformat()
    s["streak"] = s["streak"] + 1 if s["last_daily"] == yesterday else 1
    s["last_daily"] = today.isoformat()
    reward = DAILY_REWARDS[min(s["streak"], len(DAILY_REWARDS)) - 1]
    _earn(s, reward)
    return reward


def apply_shop_item(s: dict, item: str, now: float | None = None) -> None:
    now = now or time.time()
    tick(s, now)
    if item == "turbo":
        s["turbo_until"] = max(s["turbo_until"], now) + 3600
    elif item == "refill":
        s["energy"] = float(max_energy(s))
    elif item == "pack":
        _earn(s, 50_000)


def public_view(s: dict, now: float | None = None) -> dict:
    """То, что отдаём клиенту."""
    now = now or time.time()
    return {
        "coins": int(s["coins"]), "total": int(s["total"]),
        "energy": int(s["energy"]), "max_energy": max_energy(s),
        "tap_power": tap_power(s), "auto_rate": auto_rate(s),
        "levels": {k: s[f"{k}_lvl"] for k in UPGRADES},
        "costs": {k: upgrade_cost(k, s[f"{k}_lvl"]) for k in UPGRADES},
        "turbo_left": max(0, int(s["turbo_until"] - now)),
        "streak": s["streak"],
        "daily_ready": s["last_daily"] != date.today().isoformat(),
        "league": league(s["total"]),
    }


def config() -> dict:
    return {
        "upgrades": UPGRADES, "leagues": LEAGUES, "daily": DAILY_REWARDS,
        "shop": SHOP, "regen": ENERGY_REGEN, "max_combo": MAX_COMBO,
        "ref_inviter": REF_BONUS_INVITER, "ref_invitee": REF_BONUS_INVITEE,
    }
