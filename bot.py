"""RGB ELITE: Neon Core — Telegram-бот + сервер для Mini App.

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
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "game.db"))
DEV_MODE = os.getenv("DEV_MODE") == "1"           # разрешает открыть игру в браузере без Telegram

log = logging.getLogger("rgb-elite")


# ------------------------------------------------------------------ база данных
class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL,
                total REAL NOT NULL DEFAULT 0,
                referrer INTEGER,
                refs INTEGER NOT NULL DEFAULT 0,
                last_sync REAL NOT NULL DEFAULT 0,
                created REAL NOT NULL
            )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_total ON users(total DESC)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                charge_id TEXT PRIMARY KEY, user_id INTEGER, item TEXT, stars INTEGER, ts REAL
            )""")
        self.conn.commit()
        self.lock = asyncio.Lock()

    def get(self, uid: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def create(self, uid: int, name: str) -> sqlite3.Row:
        now = time.time()
        self.conn.execute(
            "INSERT OR IGNORE INTO users(id, name, state, last_sync, created) VALUES (?,?,?,?,?)",
            (uid, name, json.dumps(game.new_state(now)), now, now))
        self.conn.commit()
        return self.get(uid)

    def save(self, uid: int, state: dict, **extra) -> None:
        cols = {"state": json.dumps(state), "total": state["total"], **extra}
        sets = ", ".join(f"{k}=?" for k in cols)
        self.conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*cols.values(), uid))
        self.conn.commit()

    def top(self, limit: int = 50) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, name, total FROM users ORDER BY total DESC LIMIT ?", (limit,)).fetchall()

    def rank(self, total: float) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM users WHERE total > ?", (total,)).fetchone()[0] + 1


db: DB  # создаётся в main()


async def get_or_create(uid: int, name: str, ref_param: str | None = None) -> tuple[sqlite3.Row, bool]:
    """Возвращает пользователя; при первом входе начисляет реферальные бонусы."""
    row = db.get(uid)
    if row:
        if name and row["name"] != name:
            db.conn.execute("UPDATE users SET name=? WHERE id=?", (name, uid))
            db.conn.commit()
        return row, False
    row = db.create(uid, name)
    if ref_param and ref_param.startswith("ref_"):
        try:
            ref_id = int(ref_param[4:])
        except ValueError:
            ref_id = 0
        inviter = db.get(ref_id) if ref_id and ref_id != uid else None
        if inviter:
            st = json.loads(row["state"])
            st["coins"] += game.REF_BONUS_INVITEE
            st["total"] += game.REF_BONUS_INVITEE
            db.save(uid, st, referrer=ref_id)
            ist = json.loads(inviter["state"])
            ist["coins"] += game.REF_BONUS_INVITER
            ist["total"] += game.REF_BONUS_INVITER
            db.save(ref_id, ist, refs=inviter["refs"] + 1)
            row = db.get(uid)
    return row, True


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
        return await request.json()
    except Exception:
        return {}


def respond(row: sqlite3.Row, state: dict, **extra) -> web.Response:
    view = game.public_view(state)
    view["refs"] = row["refs"]
    view["rank"] = db.rank(state["total"])
    return web.json_response({"ok": True, "state": view, **extra})


async def api_state(request: web.Request) -> web.Response:
    data = auth(request)
    user = data["user"]
    async with db.lock:
        row, _ = await get_or_create(user["id"], display_name(user), data.get("start_param"))
        state = json.loads(row["state"])
        game.tick(state)
        db.save(row["id"], state, last_sync=time.time())
        row = db.get(row["id"])
    if "bot_username" not in request.app:
        request.app["bot_username"] = (await request.app["bot"].get_me()).username
    return respond(row, state, config=game.config(), uid=row["id"],
                   bot_username=request.app["bot_username"])


async def api_sync(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    async with db.lock:
        row, _ = await get_or_create(data["user"]["id"], display_name(data["user"]))
        state = json.loads(row["state"])
        now = time.time()
        combo = {int(k): int(v) for k, v in (payload.get("combo") or {}).items() if str(k).isdigit()}
        game.apply_taps(state, payload.get("taps", 0), combo, now - row["last_sync"], now)
        db.save(row["id"], state, last_sync=now)
    return respond(row, state)


async def api_buy(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    async with db.lock:
        row, _ = await get_or_create(data["user"]["id"], display_name(data["user"]))
        state = json.loads(row["state"])
        err = game.buy_upgrade(state, str(payload.get("key")))
        db.save(row["id"], state)
    return respond(row, state, error=err)


async def api_daily(request: web.Request) -> web.Response:
    data = auth(request)
    async with db.lock:
        row, _ = await get_or_create(data["user"]["id"], display_name(data["user"]))
        state = json.loads(row["state"])
        game.tick(state)
        reward = game.claim_daily(state)
        db.save(row["id"], state)
    return respond(row, state, reward=reward)


async def api_top(request: web.Request) -> web.Response:
    rows = db.top()
    return web.json_response({"ok": True, "top": [
        {"name": r["name"], "total": int(r["total"]), "league": game.league(r["total"])} for r in rows]})


async def api_invoice(request: web.Request) -> web.Response:
    data, payload = auth(request), await body(request)
    item = str(payload.get("item"))
    if item not in game.SHOP:
        raise web.HTTPBadRequest(text="Нет такого товара")
    shop = game.SHOP[item]
    bot: Bot = request.app["bot"]
    link = await bot.create_invoice_link(
        title=shop["title"], description=shop["desc"],
        payload=f"{item}:{data['user']['id']}", currency="XTR",
        prices=[LabeledPrice(label=shop["title"], amount=shop["stars"])])
    return web.json_response({"ok": True, "link": link})


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(BASE_DIR / "index.html")


def build_app(bot: Bot) -> web.Application:
    app = web.Application(middlewares=[cors])
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_post("/api/state", api_state)
    app.router.add_post("/api/sync", api_sync)
    app.router.add_post("/api/buy", api_buy)
    app.router.add_post("/api/daily", api_daily)
    app.router.add_get("/api/top", api_top)
    app.router.add_post("/api/invoice", api_invoice)
    for path in ("/api/state", "/api/sync", "/api/buy", "/api/daily", "/api/invoice"):
        app.router.add_route("OPTIONS", path, lambda r: web.Response())
    return app


# ------------------------------------------------------------------ Telegram-бот
dp = Dispatcher()


def play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚡ Играть", web_app=WebAppInfo(url=WEBAPP_URL))]])


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot) -> None:
    user = message.from_user
    async with db.lock:
        row, is_new = await get_or_create(user.id, user.full_name, command.args)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user.id}"
    text = (
        "<b>RGB ELITE: Neon Core</b> ⚡\n\n"
        "Тапай по ядру, лови комбо, когда цвет ядра совпадает с целью, "
        "прокачивай майнер и поднимайся из Бронзы в <b>RGB Элиту</b>.\n\n"
        f"👥 Друг по твоей ссылке: тебе +{game.REF_BONUS_INVITER}💎, ему +{game.REF_BONUS_INVITEE}💎\n"
        f"<code>{ref_link}</code>"
    )
    if is_new and row["referrer"]:
        text += f"\n\n🎁 Ты пришёл по приглашению: +{game.REF_BONUS_INVITEE}💎 уже на балансе!"
        try:
            await bot.send_message(row["referrer"], f"👥 {user.full_name} присоединился по твоей ссылке! "
                                                    f"+{game.REF_BONUS_INVITER}💎")
        except Exception:
            pass
    await message.answer(text, reply_markup=play_keyboard() if WEBAPP_URL else None)


@dp.message(Command("top"))
async def cmd_top(message: Message) -> None:
    lines = [f"{i}. {r['name']} — {int(r['total']):,}💎".replace(",", " ")
             for i, r in enumerate(db.top(10), 1)]
    await message.answer("🏆 <b>Топ-10 игроков</b>\n\n" + ("\n".join(lines) or "Пока пусто — стань первым!"))


@dp.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    # Telegram требует от ботов со Stars команду поддержки по платежам
    await message.answer("По вопросам оплаты напиши сюда в чат, опиши проблему и приложи "
                         "чек из Telegram — ответим в течение 24 часов.")


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    item = query.invoice_payload.split(":")[0]
    await query.answer(ok=item in game.SHOP, error_message="Товар недоступен")


@dp.message(F.successful_payment)
async def paid(message: Message) -> None:
    sp = message.successful_payment
    item = sp.invoice_payload.split(":")[0]
    uid = message.from_user.id
    async with db.lock:
        if db.conn.execute("SELECT 1 FROM payments WHERE charge_id=?",
                           (sp.telegram_payment_charge_id,)).fetchone():
            return  # уже учли
        row, _ = await get_or_create(uid, message.from_user.full_name)
        state = json.loads(row["state"])
        game.apply_shop_item(state, item)
        db.save(uid, state)
        db.conn.execute("INSERT INTO payments VALUES (?,?,?,?,?)",
                        (sp.telegram_payment_charge_id, uid, item, sp.total_amount, time.time()))
        db.conn.commit()
    await message.answer(f"✅ Оплата прошла: <b>{game.SHOP[item]['title']}</b>. Возвращайся в игру!",
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
        log.warning("WEBAPP_URL не задан — кнопка «Играть» в боте не появится")

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
