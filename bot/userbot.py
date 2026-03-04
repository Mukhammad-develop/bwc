"""
Brightway Consulting — Telegram Userbot (up to 2 personal accounts)
Uses Telethon + Django ORM for all database operations.

FIRST RUN (one-time auth per account):
    python bot/userbot.py --auth   # account 1 → sessions/userbot.session
    python bot/userbot.py --auth2  # account 2 → sessions/userbot2.session

NORMAL RUN:
    python bot/userbot.py          # runs both accounts
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bwc.settings")

import django
django.setup()

from django.conf import settings
from django.utils import timezone

from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    DocumentAttributeFilename,
    MessageMediaDocument,
    MessageMediaPhoto,
)

from core.models import TgUser, Case, Document, PendingSend, ImportRequest
from bot.services import t, detect_service, ask_ai

# ── Config ────────────────────────────────────────────────────────────────────
API_ID   = settings.TG_API_ID
API_HASH = settings.TG_API_HASH
PHONE    = settings.TG_PHONE
PHONE_2  = settings.TG_PHONE_2

SESSIONS_DIR = ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

SESSION   = str(SESSIONS_DIR / "userbot")
SESSION_2 = str(SESSIONS_DIR / "userbot2")

UPLOADS_DIR = settings.UPLOADS_DIR
UPLOADS_DIR.mkdir(exist_ok=True)

client1 = TelegramClient(SESSION,   API_ID, API_HASH)
client2 = TelegramClient(SESSION_2, API_ID, API_HASH)
CLIENTS = [client1, client2]

executor = ThreadPoolExecutor(max_workers=4)


# ── ORM helpers ───────────────────────────────────────────────────────────────

def _get_or_create_user(tg_id: int) -> TgUser:
    user, _ = TgUser.objects.get_or_create(
        tg_id=tg_id, defaults={"language": "en"}
    )
    return user


def _set_linked_account(tg_id: int, account_index: int):
    TgUser.objects.filter(tg_id=tg_id).update(linked_account=account_index)


def _get_active_case(user: TgUser) -> "Case | None":
    return Case.objects.filter(user=user, status="active").order_by("-created_at").first()


def _get_or_open_case(user: TgUser, service: str) -> Case:
    case = _get_active_case(user)
    if case:
        if case.service == "general" and service != "general":
            case.service = service
            case.save(update_fields=["service", "updated_at"])
        return case
    return Case.objects.create(user=user, service=service)


# ── Typing helpers ────────────────────────────────────────────────────────────

async def safe_typing(event):
    try:
        peer = await event.get_input_chat()
        return event.client.action(peer, "typing")
    except Exception:
        return _NullContext()


class _NullContext:
    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass


async def safe_send(event, text, **kwargs):
    try:
        await event.respond(text, **kwargs)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        await event.respond(text, **kwargs)


def lang_buttons():
    return [[
        Button.inline("🇬🇧 English", b"lang_en"),
        Button.inline("🇺🇿 O'zbek",  b"lang_uz"),
        Button.inline("🇷🇺 Русский", b"lang_ru"),
    ]]


# ── Register handlers for one client ─────────────────────────────────────────

def register_handlers(client, account_index: int):

    @client.on(events.NewMessage(pattern=r"^/start$", incoming=True, func=lambda e: e.is_private))
    async def handle_start(event):
        tg_id = event.sender_id
        user  = await asyncio.get_event_loop().run_in_executor(executor, _get_or_create_user, tg_id)
        await asyncio.get_event_loop().run_in_executor(executor, _set_linked_account, tg_id, account_index)
        await safe_send(event, t(user.language, "welcome"), buttons=lang_buttons())

    @client.on(events.NewMessage(pattern=r"^/help$", incoming=True, func=lambda e: e.is_private))
    async def handle_help(event):
        tg_id = event.sender_id
        async with await safe_typing(event):
            user = await asyncio.get_event_loop().run_in_executor(executor, _get_or_create_user, tg_id)
            await asyncio.get_event_loop().run_in_executor(executor, _set_linked_account, tg_id, account_index)
        await safe_send(event, t(user.language, "help_text"))

    @client.on(events.NewMessage(pattern=r"^/(mycase|case)$", incoming=True, func=lambda e: e.is_private))
    async def handle_mycase(event):
        tg_id = event.sender_id
        async with await safe_typing(event):
            user  = await asyncio.get_event_loop().run_in_executor(executor, _get_or_create_user, tg_id)
            await asyncio.get_event_loop().run_in_executor(executor, _set_linked_account, tg_id, account_index)
            case  = await asyncio.get_event_loop().run_in_executor(executor, _get_active_case, user)
            doc_count = Document.objects.filter(case=case).count() if case else 0
        if not case:
            await safe_send(event, t(user.language, "case_none"))
            return
        await safe_send(event, t(user.language, "case_info",
            service=case.service, status=case.status,
            payment=case.payment_status, doc_count=doc_count))

    @client.on(events.CallbackQuery(func=lambda e: e.is_private))
    async def handle_callback(event):
        data  = event.data.decode("utf-8")
        tg_id = event.sender_id
        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            def _set_lang():
                user = _get_or_create_user(tg_id)
                user.language = lang_code
                user.save(update_fields=["language"])
                _set_linked_account(tg_id, account_index)
            await asyncio.get_event_loop().run_in_executor(executor, _set_lang)
            try:
                await event.edit(t(lang_code, "intro"), buttons=None)
            except Exception:
                await safe_send(event, t(lang_code, "intro"))
        await event.answer()

    @client.on(events.NewMessage(incoming=True,
        func=lambda e: e.is_private and not e.message.media
                       and not (e.message.text or "").startswith("/")))
    async def handle_text(event):
        tg_id = event.sender_id
        text  = (event.message.text or "").strip()
        if not text:
            return
        async with await safe_typing(event):
            def _db_text():
                user     = _get_or_create_user(tg_id)
                _set_linked_account(tg_id, account_index)
                case     = _get_active_case(user)
                detected = detect_service(text)
                service  = detected or (case.service if case else "general")
                case     = _get_or_open_case(user, service)
                case.add_message("user", text)
                return user, case, case.get_conversation()
            user, case, conv = await asyncio.get_event_loop().run_in_executor(executor, _db_text)
            reply = await asyncio.get_event_loop().run_in_executor(executor, ask_ai, conv, case.service, user.language)
        if reply:
            await asyncio.get_event_loop().run_in_executor(executor, case.add_message, "assistant", reply)
            await safe_send(event, reply)
        else:
            await safe_send(event, t(user.language, "ai_error"))

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and bool(e.message.media)))
    async def handle_media(event):
        tg_id = event.sender_id
        msg   = event.message

        if isinstance(msg.media, MessageMediaPhoto):
            unique_id  = str(uuid.uuid4())
            filename   = f"{unique_id}.jpg"
            media_type = "photo"
        elif isinstance(msg.media, MessageMediaDocument):
            doc       = msg.media.document
            unique_id = str(uuid.uuid4())
            base_name = next(
                (a.file_name for a in doc.attributes if isinstance(a, DocumentAttributeFilename)),
                None,
            ) or f"document{mimetypes.guess_extension(doc.mime_type or '') or ''}"
            ext        = (Path(base_name).suffix or ".oga").lower()
            filename   = f"{unique_id}{ext}"
            media_type = "voice" if (doc.mime_type or "").startswith("audio") else "document"
        else:
            return

        async with await safe_typing(event):
            dest_path = UPLOADS_DIR / filename
            try:
                await msg.download_media(file=str(dest_path))
            except Exception as e:
                print(f"[Userbot] download error: {e}")
            file_id  = f"local:{filename}"
            file_uid = unique_id

            def _db_media():
                user = _get_or_create_user(tg_id)
                _set_linked_account(tg_id, account_index)
                case = _get_active_case(user) or _get_or_open_case(user, "general")
                Document.objects.create(
                    case=case, doc_type=filename, filename=filename,
                    file_id=file_id, file_unique_id=file_uid, media_type=media_type,
                )
                case.add_message("user", f"[FILE:{file_uid}:{filename}:{media_type}]")
                return user, case, case.get_conversation()
            user, case, conv = await asyncio.get_event_loop().run_in_executor(executor, _db_media)
            reply = await asyncio.get_event_loop().run_in_executor(executor, ask_ai, conv, case.service, user.language)

        if reply:
            await asyncio.get_event_loop().run_in_executor(executor, case.add_message, "assistant", reply)
            await safe_send(event, reply)
        else:
            await safe_send(event, t(user.language, "doc_received"))


# ── Import queue loop ─────────────────────────────────────────────────────────

async def process_import(req_id: int, user_tg_id: str):
    print(f"[Userbot] import #{req_id} → tg_id={user_tg_id}")
    try:
        peer = int(user_tg_id)
    except ValueError:
        peer = user_tg_id

    try:
        raw_msgs = await CLIENTS[0].get_messages(peer, limit=3000)
    except Exception as e:
        ImportRequest.objects.filter(pk=req_id).update(status="error", error_msg=str(e))
        return

    raw_msgs = list(reversed(raw_msgs))
    conv = []
    for msg in raw_msgs:
        text = getattr(msg, "text", "") or ""
        if not text and not getattr(msg, "media", None):
            continue
        role    = "admin" if msg.out else "user"
        ts      = msg.date.isoformat() if msg.date else datetime.utcnow().isoformat()
        content = text if text else "[media attachment]"
        conv.append({"role": role, "content": content, "timestamp": ts})

    def _save_import():
        tg_id_int = int(user_tg_id) if str(user_tg_id).lstrip("-").isdigit() else 0
        user  = _get_or_create_user(tg_id_int) if tg_id_int else None
        if user:
            case = Case.objects.create(user=user, service="general", conversation_history=json.dumps(conv))
        ImportRequest.objects.filter(pk=req_id).update(
            status="done", message_count=len(conv), completed_at=timezone.now()
        )
    await asyncio.get_event_loop().run_in_executor(executor, _save_import)
    print(f"[Userbot] import #{req_id} done — {len(conv)} messages")


async def import_queue_loop():
    print("[Userbot] import_queue_loop started")
    while True:
        await asyncio.sleep(5)
        try:
            pending = list(ImportRequest.objects.filter(status="pending"))
            for req in pending:
                ImportRequest.objects.filter(pk=req.pk).update(status="processing")
                await process_import(req.pk, req.user_tg_id)
        except Exception as e:
            print(f"[Userbot] import_queue_loop error: {e}")


# ── Send-queue loop ───────────────────────────────────────────────────────────

async def send_queue_loop():
    print("[Userbot] send_queue_loop started")
    while True:
        await asyncio.sleep(3)
        try:
            for account_index, client in enumerate(CLIENTS):
                rows = list(PendingSend.objects.filter(sent=False, account_index=account_index))
                for row in rows:
                    try:
                        await client.send_message(int(row.user_tg_id), row.message)
                        row.sent    = True
                        row.sent_at = timezone.now()
                        row.save(update_fields=["sent", "sent_at"])
                        print(f"[Userbot] account {account_index} → {row.user_tg_id}")
                    except Exception as e:
                        print(f"[Userbot] send error account {account_index} {row.user_tg_id}: {e}")
        except Exception as e:
            print(f"[Userbot] send_queue_loop error: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not API_ID or not API_HASH:
        print("[Userbot] ERROR: TG_API_ID / TG_API_HASH not set in .env")
        sys.exit(1)

    if "--auth" in sys.argv:
        print("[Userbot] Authenticating account 1…")
        await client1.start(phone=PHONE or input("Phone for account 1: "))
        print("[Userbot] Account 1 authenticated. Session saved.")
        return

    if "--auth2" in sys.argv:
        print("[Userbot] Authenticating account 2…")
        await client2.start(phone=PHONE_2 or input("Phone for account 2: "))
        print("[Userbot] Account 2 authenticated. Session saved.")
        return

    register_handlers(client1, account_index=0)
    register_handlers(client2, account_index=1)

    await client1.start()
    try:
        await client2.start()
        has_client2 = True
    except Exception as e:
        print(f"[Userbot] Account 2 unavailable: {e}")
        has_client2 = False

    me1 = await client1.get_me()
    print(f"[Userbot] Account 1: @{me1.username or me1.id}")
    if has_client2:
        me2 = await client2.get_me()
        print(f"[Userbot] Account 2: @{me2.username or me2.id}")

    tasks = [
        asyncio.create_task(client1.run_until_disconnected()),
        asyncio.create_task(send_queue_loop()),
        asyncio.create_task(import_queue_loop()),
    ]
    if has_client2:
        tasks.append(asyncio.create_task(client2.run_until_disconnected()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
