import telebot
from telebot import types

import db
from config import BOT_TOKEN, DB_PATH
from services import t, detect_service, ask_ai, build_system_prompt  # noqa: F401 (build_system_prompt kept for potential direct use)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db.init_db(DB_PATH)

# ─────────────────────────────── KEYBOARD ────────────────────────────────────

def lang_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="lang_uz"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
    )
    return kb


# ─────────────────────────────── HELPERS ─────────────────────────────────────

def extract_file_ids(message):
    if message.document:
        return message.document.file_id, message.document.file_unique_id
    if message.photo:
        p = message.photo[-1]
        return p.file_id, p.file_unique_id
    return None, None


def get_or_open_case(conn, user_id: int, service: str):
    """Return existing active case or create one for the given service."""
    case = db.get_active_case(conn, user_id)
    if case and case["service"]:
        # Upgrade from 'general' if we now know the service
        if case["service"] == "general" and service != "general":
            db.update_case(conn, case["id"], service=service)
            return db.get_active_case(conn, user_id)
        return case
    db.create_case(conn, user_id, service)
    return db.get_active_case(conn, user_id)


# ──────────────────────────────── HANDLERS ───────────────────────────────────

@bot.message_handler(commands=["start"])
def handle_start(message):
    with db.connect(DB_PATH) as conn:
        db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
    bot.send_message(message.chat.id, t(lang, "welcome"), reply_markup=lang_keyboard())


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
    bot.send_message(message.chat.id, t(lang, "help_text"))


@bot.message_handler(commands=["mycase", "case"])
def handle_my_case(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang   = db.get_language(conn, message.from_user.id)
        case   = db.get_active_case(conn, user_id)
        if not case or not case["service"]:
            bot.send_message(message.chat.id, t(lang, "case_none"))
            return
        doc_count = len(db.list_documents(conn, case["id"]))
        bot.send_message(
            message.chat.id,
            t(lang, "case_info",
              service=case["service"],
              status=case["status"],
              payment=case["payment_status"],
              doc_count=doc_count),
        )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    text = (message.text or "").strip()
    if not text:
        return

    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang    = db.get_language(conn, message.from_user.id)
        case    = db.get_active_case(conn, user_id)

        # Detect service from user message
        detected = detect_service(text)
        service  = detected or (case["service"] if case and case["service"] else "general")

        # Open or continue case
        case = get_or_open_case(conn, user_id, service)

        # Log user message
        db.add_conversation_message(conn, case["id"], "user", text)
        conversation = db.get_conversation(conn, case["id"])

        # Get AI reply
        reply = ask_ai(conversation, case["service"], lang)
        if reply:
            db.add_conversation_message(conn, case["id"], "assistant", reply)
            bot.send_message(message.chat.id, reply)
        else:
            bot.send_message(message.chat.id, t(lang, "ai_error"))


@bot.message_handler(content_types=["document", "photo"])
def handle_document(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang    = db.get_language(conn, message.from_user.id)
        case    = db.get_active_case(conn, user_id)

        if not case or not case["service"]:
            case = get_or_open_case(conn, user_id, "general")

        # Save file
        file_id, file_unique_id = extract_file_ids(message)
        if message.document:
            filename   = getattr(message.document, "file_name", "document")
            media_type = "document"
        else:
            filename   = "photo.jpg"
            media_type = "photo"
        db.add_document(conn, case["id"], filename, file_id, file_unique_id,
                        filename=filename, media_type=media_type)

        # Add structured file event to conversation
        db.add_conversation_message(
            conn, case["id"], "user",
            f"[FILE:{file_unique_id}:{filename}:{media_type}]",
        )
        conversation = db.get_conversation(conn, case["id"])

        reply = ask_ai(conversation, case["service"], lang)
        if reply:
            db.add_conversation_message(conn, case["id"], "assistant", reply)
            bot.send_message(message.chat.id, reply)
        else:
            bot.send_message(message.chat.id, t(lang, "doc_received"))


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    with db.connect(DB_PATH) as conn:
        db.get_or_create_user(conn, call.from_user.id)

        if call.data.startswith("lang_"):
            lang_code = call.data.split("_")[1]
            db.set_language(conn, call.from_user.id, lang_code)
            # Remove the language buttons and send the text intro — no more buttons
            bot.edit_message_text(
                t(lang_code, "intro"),
                call.message.chat.id,
                call.message.message_id,
            )
            return

        bot.answer_callback_query(call.id)


# ───────────────────────────────── MAIN ──────────────────────────────────────

if __name__ == "__main__":
    print("Starting Brightway AI bot…")
    print(f"OpenAI: {'✓' if OPENAI_API_KEY else '✗ missing'}")
    bot.infinity_polling()
