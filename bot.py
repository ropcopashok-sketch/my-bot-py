"""GIFT LAB — Telegram-бот + сервер для Mini App.

Один процесс делает всё:
  * отвечает в Telegram (/start, рефералы, оплата Telegram Stars);
  * раздаёт index.html и API игры по HTTP (aiohttp).

Запуск:  BOT_TOKEN=... WEBAPP_URL=https://твой-домен python bot.py
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice,
                           Message, PreCheckoutQuery, WebAppInfo)
from aiohttp import web

import game

# ------------------------------------------------------------------ настройки
BASE_DIR = Path(__file__).parent
try:  # .env необязателен
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")          # https-адрес, где открыт index.html
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "giftlab.db"))
DEV_MODE = os.getenv("DEV_MODE") == "1"           # разрешает открыть игру в браузере без Telegram

log = logging.getLogger("gift-lab")


# ------------------------------------------------------------------ база данных
class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                coins INTEGER NOT NULL DEFAULT 0,
                refs INTEGER NOT NULL DEFAULT 0,
                referrer INTEGER,
                last_free REAL NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT NOT NULL DEFAULT '',
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner INTEGER NOT NULL,
                gift TEXT NOT NULL,
                bg TEXT NOT NULL,
                serial INTEGER NOT NULL,
                value INTEGER NOT NULL,
                created REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner);
            CREATE TABLE IF NOT EXISTS minted (gift TEXT PRIMARY KEY, n INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, name TEXT, kind TEXT, data TEXT
            );
            CREATE TABLE IF NOT EXISTS payments (
                charge_id TEXT PRIMARY KEY, user_id INTEGER, item TEXT, stars INTEGER, ts REAL
            );
        """)
        # новые колонки для старых баз (профиль игрока)
        for col in ("xp", "cases", "up_total", "up_won"):
            try:
                self.conn.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # колонка уже есть
        self.conn.commit()
        self.lock = asyncio.Lock()

    # пользователи
    def user(self, uid: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def update_user(self, uid: int, **cols) -> None:
        sets = ", ".join(f"{k}=?" for k in cols)
        self.conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*cols.values(), uid))

    def add_coins(self, uid: int, amount: int) -> None:
        self.conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (amount, uid))

    # предметы
    def mint(self, owner: int, gift: str, bg: str) -> dict:
        """Создаёт новый экземпляр подарка с порядковым номером."""
        self.conn.execute("INSERT INTO minted(gift, n) VALUES (?, 1) "
                          "ON CONFLICT(gift) DO UPDATE SET n = n + 1", (gift,))
        serial = self.conn.execute("SELECT n FROM minted WHERE gift=?", (gift,)).fetchone()[0]
        value = game.item_value(gift, bg)
        cur = self.conn.execute(
            "INSERT INTO items(owner, gift, bg, serial, value, created) VALUES (?,?,?,?,?,?)",
            (owner, gift, bg, serial, value, time.time()))
        return {"id": cur.lastrowid, "gift": gift, "bg": bg, "serial": serial, "value": value}

    def items(self, owner: int) -> list[dict]:
        rows = self.conn.execute("SELECT id, gift, bg, serial, value FROM items WHERE owner=? "
                                 "ORDER BY value DESC, id DESC", (owner,)).fetchall()
        return [dict(r) for r in rows]

    def take_items(self, owner: int, ids: list[int]) -> list[sqlite3.Row] | None:
        """Возвращает предметы, только если ВСЕ принадлежат игроку."""
        ids = list(dict.fromkeys(int(i) for i in ids))
        if not ids:
            return None
        q = ",".join("?" * len(ids))
        rows = self.conn.execute(f"SELECT * FROM items WHERE owner=? AND id IN ({q})", (owner, *ids)).fetchall()
        return rows if len(rows) == len(ids) else None

    def delete_items(self, ids: list[int]) -> None:
        q = ",".join("?" * len(ids))
        self.conn.execute(f"DELETE FROM items WHERE id IN ({q})", ids)

    # лента и рейтинг
    def add_feed(self, name: str, kind: str, data: dict) -> None:
        self.conn.execute("INSERT INTO feed(ts, name, kind, data) VALUES (?,?,?,?)",
                          (time.time(), name, kind, json.dumps(data)))
        self.conn.execute("DELETE FROM feed WHERE id < (SELECT MAX(id) - 200 FROM feed)")

    def feed(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM feed ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r["id"], "name": r["name"], "kind": r["kind"], **json.loads(r["data"])} for r in rows]

    def top(self, limit: int = 50) -> list[sqlite3.Row]:
        return self.conn.execute("""
            SELECT u.id, u.name, COALESCE(SUM(i.value), 0) AS worth, COUNT(i.id) AS cnt
            FROM users u LEFT JOIN items i ON i.owner = u.id
            GROUP BY u.id ORDER BY worth DESC LIMIT ?""", (limit,)).fetchall()


db: DB  # создаётся в main()


def get_or_create(uid: int, name: str, ref_param: str | None = None) -> tuple[sqlite3.Row, bool]:
    """Возвращает пользователя; при первом входе даёт стартовые кристаллы и реферальные бонусы."""
    row = db.user(uid)
    if row:
        if name and row["name"] != name:
            db.update_user(uid, name=name)
            db.conn.commit()
        return db.user(uid), False
    db.conn.execute("INSERT INTO users(id, name, coins, created) VALUES (?,?,?,?)",
                    (uid, name, game.START_COINS, time.time()))
    if ref_param and ref_param.startswith("ref_"):
        try:
            ref_id = int(ref_param[4:])
        except ValueError:
            ref_id = 0
        inviter = db.user(ref_id) if ref_id and ref_id != uid else None
        if inviter:
            db.update_user(uid, referrer=ref_id)
            db.add_coins(uid, game.REF_BONUS_INVITEE)
            db.add_coins(ref_id, game.REF_BONUS_INVITER)
            db.update_user(ref_id, refs=inviter["refs"] + 1)
    db.conn.commit()
    return db.user(uid), True


# ------------------------------------------------------------------ проверка Telegram initData
def check_init_data(init_data: str) -> dict | None:
    """Проверяет подпись данных от Telegram Mini App.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app"""
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        return None
    if time.time() - int(pairs.get("auth_date", 0)) > 24 * 3600:
        return None
    pairs["user"] = json.loads(pairs.get("user", "{}"))
    return pairs


def display_name(user: dict) -> str:
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    return name or user.get("username") or f"Игрок {user.get('id')}"


# ------------------------------------------------------------------ HTTP API
@web.middleware
async def cors(request: web.Request, handler):
    resp = web.Response(status=204) if request.method == "OPTIONS" else await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def auth(request: web.Request) -> dict:
    data = check_init_data(request.headers.get("X-Init-Data", ""))
    if data and data["user"].get("id"):
        return data
    if DEV_MODE:
        return {"user": {"id": 1, "first_name": "Dev"}, "start_param": None}
    raise web.HTTPUnauthorized(text="Открой игру через Telegram")


async def body(request: web.Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def user_view(uid: int) -> dict:
    u = db.user(uid)
    today = date.today().isoformat()
    return {
        "coins": u["coins"], "refs": u["refs"], "streak": u["streak"],
        "xp": u["xp"], "cases": u["cases"], "up_total": u["up_total"], "up_won": u["up_won"],
        "daily_ready": u["last_daily"] != today,
        "free_in": max(0, int(u["last_free"] + game.FREE_CASE_COOLDOWN - time.time())),
        "items": db.items(uid),
    }


def ok(user_id: int, **extra) -> web.Response:
    return web.json_response({"ok": True, "user": user_view(user_id), **extra})


def fail(uid: int, error: str) -> web.Response:
    return web.json_response({"ok": False, "error": error, "user": user_view(uid)})


async def api_state(request: web.Request) -> web.Response:
    data = auth(request)
    async with db.lock:
        row, _ = get_or_create(data["user"]["id"], display_name(data["user"]), data.get("start_param"))
    if "bot_username" not in request.app:
        request.app["bot_username"] = (await request.app["bot"].get_me()).username
    return ok(row["id"], config=game.config(), uid=row["id"],
              bot_username=request.app["bot_username"], feed=db.feed())


async def api_case(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    case = str(payload.get("case"))
    if case not in game.CASES:
        raise web.HTTPBadRequest(text="Нет такого кейса")
    name = display_name(data["user"])
    async with db.lock:
        u, _ = get_or_create(data["user"]["id"], name)
        price = game.CASES[case]["price"]
        if price == 0:
            if time.time() - u["last_free"] < game.FREE_CASE_COOLDOWN:
                return fail(u["id"], "Бесплатный кейс ещё перезаряжается")
            db.update_user(u["id"], last_free=time.time())
        elif u["coins"] < price:
            return fail(u["id"], "Не хватает кристаллов")
        else:
            db.add_coins(u["id"], -price)
        db.conn.execute("UPDATE users SET cases = cases + 1, xp = xp + ? WHERE id=?",
                        (max(5, price // 10), u["id"]))
        gift, bg = game.roll_case(case)
        item = db.mint(u["id"], gift, bg)
        if game.GIFTS[gift][2] in ("epic", "legendary") or bg in ("gold", "rainbow"):
            db.add_feed(name, "drop", {"gift": gift, "bg": bg, "serial": item["serial"], "case": case})
        db.conn.commit()
    return ok(u["id"], item=item)


async def api_sell(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    async with db.lock:
        u, _ = get_or_create(data["user"]["id"], display_name(data["user"]))
        rows = db.take_items(u["id"], payload.get("ids") or [])
        if not rows:
            return fail(u["id"], "Выбери свои подарки")
        total = sum(r["value"] for r in rows)
        db.delete_items([r["id"] for r in rows])
        db.add_coins(u["id"], total)
        db.conn.commit()
    return ok(u["id"], sold=total)


async def api_upgrade(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    name = display_name(data["user"])
    async with db.lock:
        u, _ = get_or_create(data["user"]["id"], name)
        ids = payload.get("ids") or []
        if len(ids) > game.UPGRADE_MAX_ITEMS:
            return fail(u["id"], f"Максимум {game.UPGRADE_MAX_ITEMS} подарков за раз")
        rows = db.take_items(u["id"], ids)
        if not rows:
            return fail(u["id"], "Выбери свои подарки")
        input_value = sum(r["value"] for r in rows)
        target = str(payload.get("target"))
        res = game.do_upgrade(input_value, target)
        if "error" in res:
            return fail(u["id"], res["error"])
        db.delete_items([r["id"] for r in rows])
        db.conn.execute("UPDATE users SET up_total = up_total + 1, up_won = up_won + ?, xp = xp + ? WHERE id=?",
                        (int(res["win"]), max(5, input_value // 20), u["id"]))
        item = db.mint(u["id"], target, "plain") if res["win"] else None
        if res["win"] or input_value >= 500:  # в ленту — победы и крупные проигрыши
            db.add_feed(name, "upgrade", {
                "from": [r["gift"] for r in rows][:3], "gift": target, "win": res["win"],
                "chance": round(res["chance"] * 100, 1)})
        db.conn.commit()
    return ok(u["id"], win=res["win"], roll=res["roll"], chance=res["chance"], item=item)


async def api_daily(request: web.Request) -> web.Response:
    data = auth(request)
    async with db.lock:
        u, _ = get_or_create(data["user"]["id"], display_name(data["user"]))
        reward, streak, last = game.claim_daily(u["streak"], u["last_daily"])
        if reward:
            db.update_user(u["id"], streak=streak, last_daily=last)
            db.add_coins(u["id"], reward)
            db.conn.commit()
    return ok(u["id"], reward=reward)


async def api_feed(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "feed": db.feed()})


async def api_top(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "top": [
        {"id": r["id"], "name": r["name"], "worth": r["worth"], "count": r["cnt"]} for r in db.top()]})


async def api_invoice(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    pack = str(payload.get("item"))
    if pack not in game.SHOP:
        raise web.HTTPBadRequest(text="Нет такого товара")
    p = game.SHOP[pack]
    link = await request.app["bot"].create_invoice_link(
        title=p["title"], description=f"{p['title']} для GIFT LAB",
        payload=f"{pack}:{data['user']['id']}", currency="XTR",
        prices=[LabeledPrice(label=p["title"], amount=p["stars"])])
    return web.json_response({"ok": True, "link": link})


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(BASE_DIR / "index.html")


def build_app(bot: Bot) -> web.Application:
    app = web.Application(middlewares=[cors])
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_static("/assets", BASE_DIR / "assets")
    posts = {"state": api_state, "case": api_case, "sell": api_sell, "upgrade": api_upgrade,
             "daily": api_daily, "invoice": api_invoice}
    for name, handler in posts.items():
        app.router.add_post(f"/api/{name}", handler)
        app.router.add_route("OPTIONS", f"/api/{name}", lambda r: web.Response())
    app.router.add_get("/api/feed", api_feed)
    app.router.add_get("/api/top", api_top)
    return app


# ------------------------------------------------------------------ Telegram-бот
dp = Dispatcher()


def play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎁 Открыть GIFT LAB", web_app=WebAppInfo(url=WEBAPP_URL))]])


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot) -> None:
    user = message.from_user
    async with db.lock:
        row, is_new = get_or_create(user.id, user.full_name, command.args)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user.id}"
    text = (
        "<b>GIFT LAB</b> 🎁\n\n"
        "Открывай кейсы, собирай подарки с номерами и <b>апгрейдь</b> их в более дорогие. "
        "Чем больше разница в цене — тем меньше шанс, но тем круче выигрыш.\n\n"
        f"👥 Друг по твоей ссылке: тебе +{game.REF_BONUS_INVITER}💎, ему +{game.REF_BONUS_INVITEE}💎\n"
        f"<code>{ref_link}</code>"
    )
    if is_new and row["referrer"]:
        text += f"\n\n🎉 Ты пришёл по приглашению: +{game.REF_BONUS_INVITEE}💎 уже на балансе!"
        try:
            await bot.send_message(row["referrer"], f"👥 {user.full_name} присоединился по твоей ссылке! "
                                                    f"+{game.REF_BONUS_INVITER}💎")
        except Exception:
            pass
    await message.answer(text, reply_markup=play_keyboard() if WEBAPP_URL else None)


@dp.message(Command("top"))
async def cmd_top(message: Message) -> None:
    lines = [f"{i}. {r['name']} — {r['worth']:,}💎 ({r['cnt']} шт.)".replace(",", " ")
             for i, r in enumerate(db.top(10), 1)]
    await message.answer("🏆 <b>Топ коллекционеров</b>\n\n" + ("\n".join(lines) or "Пока пусто — стань первым!"))


@dp.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    # Telegram требует от ботов со Stars команду поддержки по платежам
    await message.answer("По вопросам оплаты напиши сюда в чат, опиши проблему и приложи "
                         "чек из Telegram — ответим в течение 24 часов.")


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    pack = query.invoice_payload.split(":")[0]
    await query.answer(ok=pack in game.SHOP, error_message="Товар недоступен")


@dp.message(F.successful_payment)
async def paid(message: Message) -> None:
    sp = message.successful_payment
    pack = sp.invoice_payload.split(":")[0]
    uid = message.from_user.id
    async with db.lock:
        if db.conn.execute("SELECT 1 FROM payments WHERE charge_id=?",
                           (sp.telegram_payment_charge_id,)).fetchone():
            return  # уже учли
        get_or_create(uid, message.from_user.full_name)
        db.add_coins(uid, game.SHOP[pack]["coins"])
        db.conn.execute("INSERT INTO payments VALUES (?,?,?,?,?)",
                        (sp.telegram_payment_charge_id, uid, pack, sp.total_amount, time.time()))
        db.conn.commit()
    await message.answer(f"✅ Оплата прошла: +{game.SHOP[pack]['coins']:,}💎. Удачных апгрейдов!".replace(",", " "),
                         reply_markup=play_keyboard() if WEBAPP_URL else None)


# ------------------------------------------------------------------ запуск
async def main() -> None:
    global db
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise SystemExit("Укажи BOT_TOKEN (токен от @BotFather) в .env или переменных окружения")
    db = DB(DB_PATH)

    from aiogram.client.default import DefaultBotProperties
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    runner = web.AppRunner(build_app(bot))
    await runner.setup()
    await web.TCPSite(runner, HOST, PORT).start()
    log.info("Игра доступна на http://%s:%s", HOST, PORT)
    if not WEBAPP_URL:
        log.warning("WEBAPP_URL не задан — кнопка в боте не появится")

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
