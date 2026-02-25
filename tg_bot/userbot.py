"""
Brightway Consulting — Telegram Userbot (personal account)
Uses Telethon (MTProto) to connect a real Telegram account.

FIRST RUN (one-time authentication):
    python userbot.py --auth
  Telethon will ask for your phone number, then the OTP code sent by Telegram.
  After that it saves a session file (userbot.session) and never asks again.

NORMAL RUN:
    python userbot.py
"""

import asyncio
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

DB_PATH     = os.getenv("DB_PATH", "bot.db")
_raw        = DB_PATH
DB_PATH     = _raw if _raw.startswith("/") else str(ROOT / "bot.db")

API_ID      = int(os.getenv("TG_API_ID",   "30176806"))
API_HASH    = os.getenv("TG_API_HASH",      "dade2446e3317ce1de17b0d0cf45ef4a")
PHONE       = os.getenv("TG_PHONE",         "").strip()   # e.g. +998901234567

SESSION     = str(ROOT / "userbot")
UPLOADS_DIR = ROOT / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

db.init_db(DB_PATH)

client   = TelegramClient(SESSION, API_ID, API_HASH)
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
            Button.inline("🇺🇿 O'zbek",  b"lang_uz"),
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
        return client.action(peer, "typing")
    except Exception:
        return _NullContext()


class _NullContext:
    """No-op async context manager used as a fallback when typing fails."""
    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass


async def safe_send(event, text, **kwargs):
    """Reply in the same chat, retrying once on flood wait."""
    try:
        await event.respond(text, **kwargs)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        await event.respond(text, **kwargs)


# ── /start handler ────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern=r"^/start$", incoming=True, func=lambda e: e.is_private))
async def handle_start(event):
    tg_id = event.sender_id
    with db.connect(DB_PATH) as conn:
        db.get_or_create_user(conn, tg_id)
        lang = db.get_language(conn, tg_id)
    await safe_send(event, t(lang, "welcome"), buttons=lang_buttons())


# ── /help handler ─────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern=r"^/help$", incoming=True, func=lambda e: e.is_private))
async def handle_help(event):
    tg_id = event.sender_id
    async with await safe_typing(event):
        with db.connect(DB_PATH) as conn:
            db.get_or_create_user(conn, tg_id)
            lang = db.get_language(conn, tg_id)
    await safe_send(event, t(lang, "help_text"))


# ── /mycase handler ────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern=r"^/(mycase|case)$", incoming=True, func=lambda e: e.is_private))
async def handle_mycase(event):
    tg_id = event.sender_id
    async with await safe_typing(event):
        with db.connect(DB_PATH) as conn:
            user_id   = db.get_or_create_user(conn, tg_id)
            lang      = db.get_language(conn, tg_id)
            case      = db.get_active_case(conn, user_id)
            doc_count = len(db.list_documents(conn, case["id"])) if case else 0
    if not case or not case["service"]:
        await safe_send(event, t(lang, "case_none"))
        return
    await safe_send(
        event,
        t(lang, "case_info",
          service=case["service"],
          status=case["status"],
          payment=case["payment_status"],
          doc_count=doc_count),
    )


# ── Inline keyboard callback (language selection) ─────────────────────────────

@client.on(events.CallbackQuery(func=lambda e: e.is_private))
async def handle_callback(event):
    data = event.data.decode("utf-8")
    tg_id = event.sender_id

    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        with db.connect(DB_PATH) as conn:
            db.get_or_create_user(conn, tg_id)
            db.set_language(conn, tg_id, lang_code)
        # Replace the language-selection message with the intro text (no buttons)
        try:
            await event.edit(t(lang_code, "intro"), buttons=None)
        except Exception:
            await safe_send(event, t(lang_code, "intro"))

    await event.answer()


# ── Text message handler ──────────────────────────────────────────────────────

@client.on(events.NewMessage(
    incoming=True,
    func=lambda e: e.is_private and not e.message.media and not (e.message.text or "").startswith("/")
))
async def handle_text(event):
    tg_id = event.sender_id
    text  = (event.message.text or "").strip()
    if not text:
        return

    lang = "en"
    case = None
    async with await safe_typing(event):
        with db.connect(DB_PATH) as conn:
            user_id  = db.get_or_create_user(conn, tg_id)
            lang     = db.get_language(conn, tg_id)
            case     = db.get_active_case(conn, user_id)
            detected = detect_service(text)
            service  = detected or (case["service"] if case and case["service"] else "general")
            case     = _get_or_open_case(conn, user_id, service)

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


# ── Document / photo handler ──────────────────────────────────────────────────

@client.on(events.NewMessage(
    incoming=True,
    func=lambda e: e.is_private and bool(e.message.media)
))
async def handle_media(event):
    tg_id = event.sender_id
    msg   = event.message

    # Determine filename, media type, a unique ID
    if isinstance(msg.media, MessageMediaPhoto):
        unique_id  = str(uuid.uuid4())
        filename   = f"{unique_id}.jpg"
        media_type = "photo"
    elif isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        # Try to get the original filename from attributes
        filename = None
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break
        if not filename:
            # Guess extension from mime type
            ext = mimetypes.guess_extension(doc.mime_type or "") or ""
            filename = f"document{ext}"
        unique_id  = str(uuid.uuid4())
        media_type = "document"
    else:
        # Voice, video notes, stickers etc — ignore silently
        return

    lang = "en"
    case = None
    async with await safe_typing(event):
        # Download file to uploads dir
        dest_path = UPLOADS_DIR / filename
        try:
            await msg.download_media(file=str(dest_path))
        except Exception as e:
            print(f"[Userbot] download error: {e}")
            filename  = f"file_{unique_id}"
            dest_path = UPLOADS_DIR / filename

        file_id  = f"local:{filename}"
        file_uid = unique_id

        with db.connect(DB_PATH) as conn:
            user_id  = db.get_or_create_user(conn, tg_id)
            lang     = db.get_language(conn, tg_id)
            case     = db.get_active_case(conn, user_id)
            if not case or not case["service"]:
                case = _get_or_open_case(conn, user_id, "general")

            db.add_document(conn, case["id"], filename, file_id, file_uid,
                            filename=filename, media_type=media_type)
            db.add_conversation_message(
                conn, case["id"], "user",
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


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    if not API_ID or not API_HASH:
        print("[Userbot] ERROR: TG_API_ID / TG_API_HASH not set in .env")
        return

    if "--auth" in sys.argv:
        print("[Userbot] Starting first-time authentication...")
        print("  You will be asked for your phone number and OTP code.")
        await client.start()
        me = await client.get_me()
        print(f"[Userbot] Authenticated as @{me.username} ({me.first_name})")
        print(f"[Userbot] Session saved to: {SESSION}.session")
        print("[Userbot] Run without --auth to start normally.")
        return

    if PHONE:
        await client.start(phone=PHONE)
    else:
        await client.start()

    me = await client.get_me()
    print(f"[Userbot] Running as @{me.username} ({me.first_name})")
    print(f"[Userbot] DB: {DB_PATH}")
    print("[Userbot] Listening for messages…")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
