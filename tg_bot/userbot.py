"""
Brightway Consulting — Telegram Userbot (up to 2 personal accounts)
Uses Telethon to connect one or two real Telegram accounts.

FIRST RUN (one-time auth per account):
    python userbot.py --auth   # account 1 → userbot.session
    python userbot.py --auth2  # account 2 → userbot2.session
  Set TG_PHONE and optionally TG_PHONE_2 in .env to auto-login.

NORMAL RUN:
    python userbot.py   # runs both accounts; web UI unchanged.
"""

import asyncio
import json
import mimetypes
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    DocumentAttributeFilename,
    MessageMediaDocument,
    MessageMediaPhoto,
)

# ── Paths & env ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
load_dotenv()
load_dotenv(ROOT.parent / ".env")

sys.path.insert(0, str(ROOT))
import db
from services import t, detect_service, ask_ai

DB_PATH = os.getenv("DB_PATH", "bot.db")
_raw = DB_PATH
DB_PATH = _raw if _raw.startswith("/") else str(ROOT / "bot.db")

API_ID = int(os.getenv("TG_API_ID", "30176806"))
API_HASH = os.getenv("TG_API_HASH", "dade2446e3317ce1de17b0d0cf45ef4a")
PHONE = os.getenv("TG_PHONE", "").strip()  # e.g. +998901234567
PHONE_2 = os.getenv("TG_PHONE_2", "").strip()  # second account (optional)
SESSION = str(ROOT / "userbot")
SESSION_2 = str(ROOT / os.getenv("TG_SESSION_2", "userbot2"))

UPLOADS_DIR = ROOT / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

db.init_db(DB_PATH)

# Two Telegram accounts: same handlers, replies go from the account that received the chat
client1 = TelegramClient(SESSION, API_ID, API_HASH)
client2 = TelegramClient(SESSION_2, API_ID, API_HASH)
CLIENTS = [client1, client2]
executor = ThreadPoolExecutor(max_workers=4)


# ── Helpers ───────────────────────────────────────────────────────────────────


def run_sync(fn, *args):
    """Run a blocking function in the thread-pool so the event loop stays free."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, fn, *args)


def _get_or_open_case(conn, user_id: int, service: str):
    case = db.get_active_case(conn, user_id)
    if case and case["service"]:
        if case["service"] == "general" and service != "general":
            db.update_case(conn, case["id"], service=service)
            return db.get_active_case(conn, user_id)
        return case
    db.create_case(conn, user_id, service)
    return db.get_active_case(conn, user_id)


def lang_buttons():
    return [
        [
            Button.inline("🇬🇧 English", b"lang_en"),
            Button.inline("🇺🇿 O'zbek", b"lang_uz"),
            Button.inline("🇷🇺 Русский", b"lang_ru"),
        ]
    ]


async def safe_typing(event):
    """
    Return a typing context manager using the properly resolved input peer.
    Falls back silently if entity can't be resolved.
    """
    try:
        peer = await event.get_input_chat()
        return event.client.action(peer, "typing")
    except Exception:
        return _NullContext()


class _NullContext:
    """No-op async context manager used as a fallback when typing fails."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


async def safe_send(event, text, **kwargs):
    """Reply in the same chat, retrying once on flood wait."""
    try:
        await event.respond(text, **kwargs)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        await event.respond(text, **kwargs)


# ── Register handlers for one client (account_index 0 or 1) ───────────────────


def register_handlers(client, account_index: int):
    """Attach all message handlers to this client; user is linked to this account."""

    @client.on(
        events.NewMessage(
            pattern=r"^/start$", incoming=True, func=lambda e: e.is_private
        )
    )
    async def handle_start(event):
        tg_id = event.sender_id
        with db.connect(DB_PATH) as conn:
            db.get_or_create_user(conn, tg_id)
            db.set_user_linked_account(conn, tg_id, account_index)
            lang = db.get_language(conn, tg_id)
        await safe_send(event, t(lang, "welcome"), buttons=lang_buttons())

    @client.on(
        events.NewMessage(
            pattern=r"^/help$", incoming=True, func=lambda e: e.is_private
        )
    )
    async def handle_help(event):
        tg_id = event.sender_id
        async with await safe_typing(event):
            with db.connect(DB_PATH) as conn:
                db.get_or_create_user(conn, tg_id)
                db.set_user_linked_account(conn, tg_id, account_index)
                lang = db.get_language(conn, tg_id)
        await safe_send(event, t(lang, "help_text"))

    @client.on(
        events.NewMessage(
            pattern=r"^/(mycase|case)$", incoming=True, func=lambda e: e.is_private
        )
    )
    async def handle_mycase(event):
        tg_id = event.sender_id
        async with await safe_typing(event):
            with db.connect(DB_PATH) as conn:
                user_id = db.get_or_create_user(conn, tg_id)
                db.set_user_linked_account(conn, tg_id, account_index)
                lang = db.get_language(conn, tg_id)
                case = db.get_active_case(conn, user_id)
                doc_count = len(db.list_documents(conn, case["id"])) if case else 0
        if not case or not case["service"]:
            await safe_send(event, t(lang, "case_none"))
            return
        await safe_send(
            event,
            t(
                lang,
                "case_info",
                service=case["service"],
                status=case["status"],
                payment=case["payment_status"],
                doc_count=doc_count,
            ),
        )

    @client.on(events.CallbackQuery(func=lambda e: e.is_private))
    async def handle_callback(event):
        data = event.data.decode("utf-8")
        tg_id = event.sender_id
        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            with db.connect(DB_PATH) as conn:
                db.get_or_create_user(conn, tg_id)
                db.set_user_linked_account(conn, tg_id, account_index)
                db.set_language(conn, tg_id, lang_code)
            try:
                await event.edit(t(lang_code, "intro"), buttons=None)
            except Exception:
                await safe_send(event, t(lang_code, "intro"))
        await event.answer()

    @client.on(
        events.NewMessage(
            incoming=True,
            func=lambda e: e.is_private
            and not e.message.media
            and not (e.message.text or "").startswith("/"),
        )
    )
    async def handle_text(event):
        tg_id = event.sender_id
        text = (event.message.text or "").strip()
        if not text:
            return
        lang = "en"
        case = None
        async with await safe_typing(event):
            with db.connect(DB_PATH) as conn:
                user_id = db.get_or_create_user(conn, tg_id)
                db.set_user_linked_account(conn, tg_id, account_index)
                lang = db.get_language(conn, tg_id)
                case = db.get_active_case(conn, user_id)
                detected = detect_service(text)
                service = detected or (
                    case["service"] if case and case["service"] else "general"
                )
                case = _get_or_open_case(conn, user_id, service)
                db.add_conversation_message(conn, case["id"], "user", text)
                conversation = db.get_conversation(conn, case["id"])
            reply = await asyncio.get_event_loop().run_in_executor(
                executor, ask_ai, conversation, case["service"], lang
            )
        with db.connect(DB_PATH) as conn:
            if reply:
                db.add_conversation_message(conn, case["id"], "assistant", reply)
                await safe_send(event, reply)
            else:
                await safe_send(event, t(lang, "ai_error"))

    @client.on(
        events.NewMessage(
            incoming=True, func=lambda e: e.is_private and bool(e.message.media)
        )
    )
    async def handle_media(event):
        tg_id = event.sender_id
        msg = event.message
        if isinstance(msg.media, MessageMediaPhoto):
            unique_id = str(uuid.uuid4())
            filename = f"{unique_id}.jpg"
            media_type = "photo"
        elif isinstance(msg.media, MessageMediaDocument):
            doc = msg.media.document
            unique_id = str(uuid.uuid4())
            base_name = None
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    base_name = attr.file_name
                    break
            if not base_name:
                ext = mimetypes.guess_extension(doc.mime_type or "") or ""
                base_name = f"document{ext}"
            ext = (Path(base_name).suffix or "").lower() or ".oga"
            filename = f"{unique_id}{ext}"
            media_type = "document"
        else:
            return
        lang = "en"
        case = None
        async with await safe_typing(event):
            dest_path = UPLOADS_DIR / filename
            try:
                await msg.download_media(file=str(dest_path))
            except Exception as e:
                print(f"[Userbot] download error: {e}")
                filename = f"file_{unique_id}"
                dest_path = UPLOADS_DIR / filename
            file_id = f"local:{filename}"
            file_uid = unique_id
            with db.connect(DB_PATH) as conn:
                user_id = db.get_or_create_user(conn, tg_id)
                db.set_user_linked_account(conn, tg_id, account_index)
                lang = db.get_language(conn, tg_id)
                case = db.get_active_case(conn, user_id)
                if not case or not case["service"]:
                    case = _get_or_open_case(conn, user_id, "general")
                db.add_document(
                    conn,
                    case["id"],
                    filename,
                    file_id,
                    file_uid,
                    filename=filename,
                    media_type=media_type,
                )
                db.add_conversation_message(
                    conn,
                    case["id"],
                    "user",
                    f"[FILE:{file_uid}:{filename}:{media_type}]",
                )
                conversation = db.get_conversation(conn, case["id"])
            reply = await asyncio.get_event_loop().run_in_executor(
                executor, ask_ai, conversation, case["service"], lang
            )
        with db.connect(DB_PATH) as conn:
            if reply:
                db.add_conversation_message(conn, case["id"], "assistant", reply)
                await safe_send(event, reply)
            else:
                await safe_send(event, t(lang, "doc_received"))


# ── Chat import loop (uses first account) ─────────────────────────────────────


async def process_import(req_id: int, user_tg_id: str):
    """
    Fetch full message history between this personal account and user_tg_id
    from Telegram, then save it as a case in the database.
    """
    print(f"[Userbot] import #{req_id} → tg_id={user_tg_id}")
    try:
        peer = int(user_tg_id)
    except ValueError:
        peer = user_tg_id  # username string

    try:
        raw_msgs = await CLIENTS[0].get_messages(peer, limit=3000)
    except Exception as e:
        with db.connect(DB_PATH) as conn:
            db.update_import_status(conn, req_id, "error", error_msg=str(e))
        print(f"[Userbot] import #{req_id} error fetching: {e}")
        return

    # Oldest first
    raw_msgs = list(reversed(raw_msgs))

    conv = []
    for msg in raw_msgs:
        text = getattr(msg, "text", "") or ""
        has_media = bool(getattr(msg, "media", None))
        if not text and not has_media:
            continue
        role = "admin" if msg.out else "user"
        ts = msg.date.isoformat() if msg.date else _now_iso_sync()
        content = text if text else "[media attachment]"
        conv.append({"role": role, "content": content, "timestamp": ts})

    with db.connect(DB_PATH) as conn:
        user_db_id = db.get_or_create_user(
            conn, int(user_tg_id) if str(user_tg_id).lstrip("-").isdigit() else 0
        )
        # Use an existing case or create a new one tagged as imported
        case_id = db.create_case(conn, user_db_id, "general")
        db.update_case(conn, case_id, conversation_history=json.dumps(conv))
        db.update_import_status(conn, req_id, "done", message_count=len(conv))

    print(f"[Userbot] import #{req_id} done — {len(conv)} messages")


def _now_iso_sync() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat()


async def import_queue_loop():
    """Poll import_requests table every 5 seconds and process pending imports."""
    print("[Userbot] import_queue_loop started")
    while True:
        await asyncio.sleep(5)
        try:
            with db.connect(DB_PATH) as conn:
                rows = db.get_pending_imports(conn)
            for row in rows:
                # Mark as processing immediately so we don't double-process
                with db.connect(DB_PATH) as conn:
                    db.update_import_status(conn, row["id"], "processing")
                await process_import(row["id"], row["user_tg_id"])
        except Exception as e:
            print(f"[Userbot] import_queue_loop error: {e}")


# ── Admin → user send-queue loop (per-account) ────────────────────────────────


async def send_queue_loop():
    """Poll pending_sends and send via the correct account (0 or 1)."""
    print("[Userbot] send_queue_loop started (2 accounts)")
    while True:
        await asyncio.sleep(3)
        try:
            for account_index, c in enumerate(CLIENTS):
                with db.connect(DB_PATH) as conn:
                    rows = db.get_pending_sends(conn, account_index=account_index)
                for row in rows:
                    try:
                        tg_id = int(row["user_tg_id"])
                        await c.send_message(tg_id, row["message"])
                        with db.connect(DB_PATH) as conn:
                            db.mark_send_done(conn, row["id"])
                        print(f"[Userbot] account {account_index} → {tg_id}")
                    except Exception as e:
                        print(
                            f"[Userbot] send_queue error account {account_index} {row['user_tg_id']}: {e}"
                        )
        except Exception as e:
            print(f"[Userbot] send_queue_loop error: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────


async def main():
    if not API_ID or not API_HASH:
        print("[Userbot] ERROR: TG_API_ID / TG_API_HASH not set in .env")
        return

    # First-time auth: one account at a time
    if "--auth" in sys.argv:
        print("[Userbot] Auth account 1…")
        await client1.start()
        me = await client1.get_me()
        print(f"[Userbot] Account 1: @{me.username} ({me.first_name})")
        print("[Userbot] Run without --auth to start.")
        return
    if "--auth2" in sys.argv:
        print("[Userbot] Auth account 2…")
        await client2.start()
        me = await client2.get_me()
        print(f"[Userbot] Account 2: @{me.username} ({me.first_name})")
        print("[Userbot] Run without --auth2 to start.")
        return

    # Start both accounts
    if PHONE:
        await client1.start(phone=PHONE)
    else:
        await client1.start()
    if PHONE_2:
        await client2.start(phone=PHONE_2)
    else:
        await client2.start()

    me1 = await client1.get_me()
    me2 = await client2.get_me()
    print(f"[Userbot] Account 1: @{me1.username} | Account 2: @{me2.username}")
    print(f"[Userbot] DB: {DB_PATH}")
    register_handlers(client1, 0)
    register_handlers(client2, 1)

    await asyncio.gather(
        client1.run_until_disconnected(),
        client2.run_until_disconnected(),
        send_queue_loop(),
        import_queue_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
