"""
Brightway Consulting — Telegram Bot (polling, pyTelegramBotAPI)
Uses Django ORM for all database operations.

Run with:
    cd /path/to/bwc
    DJANGO_SETTINGS_MODULE=bwc.settings python bot/bot.py
"""

import os
import sys
from pathlib import Path

# Bootstrap Django before importing models
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bwc.settings")

import django
django.setup()

import telebot
from telebot import types
from django.conf import settings
from django.utils import timezone

from core.models import TgUser, Case, Document
from bot.services import t, detect_service, ask_ai

bot = telebot.TeleBot(settings.BOT_TOKEN, parse_mode="HTML")


# ── ORM helpers ───────────────────────────────────────────────────────────────

def get_or_create_tg_user(tg_id: int) -> TgUser:
    user, _ = TgUser.objects.get_or_create(
        tg_id=tg_id,
        defaults={"language": "en", "chat_mode": "menu"},
    )
    return user


def get_active_case(user: TgUser) -> "Case | None":
    return Case.objects.filter(user=user, status="active").order_by("-created_at").first()


def get_or_open_case(user: TgUser, service: str) -> Case:
    case = get_active_case(user)
    if case:
        if case.service == "general" and service != "general":
            case.service = service
            case.save(update_fields=["service", "updated_at"])
        return case
    return Case.objects.create(user=user, service=service)


# ── Keyboards ─────────────────────────────────────────────────────────────────

def lang_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="lang_uz"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
    )
    return kb


# ── Handlers ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def handle_start(message):
    user = get_or_create_tg_user(message.from_user.id)
    bot.send_message(message.chat.id, t(user.language, "welcome"), reply_markup=lang_keyboard())


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_chat_action(message.chat.id, "typing")
    user = get_or_create_tg_user(message.from_user.id)
    bot.send_message(message.chat.id, t(user.language, "help_text"))


@bot.message_handler(commands=["mycase", "case"])
def handle_my_case(message):
    bot.send_chat_action(message.chat.id, "typing")
    user = get_or_create_tg_user(message.from_user.id)
    case = get_active_case(user)
    if not case:
        bot.send_message(message.chat.id, t(user.language, "case_none"))
        return
    doc_count = Document.objects.filter(case=case).count()
    bot.send_message(
        message.chat.id,
        t(user.language, "case_info",
          service=case.service, status=case.status,
          payment=case.payment_status, doc_count=doc_count),
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    text = (message.text or "").strip()
    if not text:
        return

    user    = get_or_create_tg_user(message.from_user.id)
    case    = get_active_case(user)
    service = detect_service(text) or (case.service if case else "general")
    case    = get_or_open_case(user, service)

    case.add_message("user", text)
    conv  = case.get_conversation()
    reply = ask_ai(conv, case.service, user.language)
    if reply:
        case.add_message("assistant", reply)
        bot.send_message(message.chat.id, reply)
    else:
        bot.send_message(message.chat.id, t(user.language, "ai_error"))


@bot.message_handler(content_types=["document", "photo"])
def handle_document(message):
    bot.send_chat_action(message.chat.id, "typing")
    user = get_or_create_tg_user(message.from_user.id)
    case = get_active_case(user) or get_or_open_case(user, "general")

    if message.document:
        file_id        = message.document.file_id
        file_unique_id = message.document.file_unique_id
        filename       = getattr(message.document, "file_name", "document")
        media_type     = "document"
    else:
        photo          = message.photo[-1]
        file_id        = photo.file_id
        file_unique_id = photo.file_unique_id
        filename       = "photo.jpg"
        media_type     = "photo"

    Document.objects.create(
        case=case, doc_type=filename, filename=filename,
        file_id=file_id, file_unique_id=file_unique_id, media_type=media_type,
    )
    case.add_message("user", f"[FILE:{file_unique_id}:{filename}:{media_type}]")

    conv  = case.get_conversation()
    reply = ask_ai(conv, case.service, user.language)
    if reply:
        case.add_message("assistant", reply)
        bot.send_message(message.chat.id, reply)
    else:
        bot.send_message(message.chat.id, t(user.language, "doc_received"))


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user = get_or_create_tg_user(call.from_user.id)
    if call.data.startswith("lang_"):
        lang_code       = call.data.split("_")[1]
        user.language   = lang_code
        user.save(update_fields=["language"])
        bot.edit_message_text(
            t(lang_code, "intro"),
            call.message.chat.id,
            call.message.message_id,
        )
        return
    bot.answer_callback_query(call.id)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Brightway AI bot…")
    print(f"Bot token: {'✓' if settings.BOT_TOKEN else '✗ missing'}")
    print(f"OpenAI:    {'✓' if settings.OPENAI_API_KEY else '✗ missing'}")
    bot.infinity_polling()
