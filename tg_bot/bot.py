import json
import telebot
from telebot import types

import db
from config import BOT_TOKEN, DB_PATH, OPENAI_API_KEY

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db.init_db(DB_PATH)

# ───────────────────────────── TRANSLATIONS ──────────────────────────────────

T = {
    "en": {
        "welcome": "Welcome to Brightway Consulting 👋\nPlease choose your language:",
        "intro": (
            "Hi there! 👋 I'm your AI assistant at Brightway Consulting.\n\n"
            "We help clients with:\n"
            "• 🎓 UK Student Visa\n"
            "• 💷 PAYE Tax Refund\n"
            "• 🧾 Self-Employed Tax / Self Assessment\n"
            "• 🏢 Company Accounting\n\n"
            "What do you need help with today? Just tell me in your own words."
        ),
        "ai_error": "Sorry, something went wrong on my end. Please try again in a moment.",
        "case_none": "You don't have an active case yet. Just tell me what you need help with and we'll get started.",
        "case_info": (
            "Here's your current case:\n"
            "• Service: {service}\n"
            "• Status: {status}\n"
            "• Payment: {payment}\n"
            "• Documents uploaded: {doc_count}"
        ),
        "help_text": (
            "I can help you with UK student visas, PAYE tax refunds, "
            "self-employed tax returns, or company accounting.\n\n"
            "Just type your question or describe your situation and I'll take it from there."
        ),
        "doc_received": "Got your file ✅",
    },
    "uz": {
        "welcome": "Brightway Consultingga xush kelibsiz 👋\nIltimos, tilni tanlang:",
        "intro": (
            "Salom! 👋 Men Brightway Consulting AI yordamchisiman.\n\n"
            "Quyidagi xizmatlarda yordam beramiz:\n"
            "• 🎓 UK talaba vizasi\n"
            "• 💷 PAYE soliq qaytimi\n"
            "• 🧾 Mustaqil ishlovchi solig'i / Self Assessment\n"
            "• 🏢 Kompaniya hisobi\n\n"
            "Bugun qanday masalada yordam kerak? Oddiy so'z bilan yozing."
        ),
        "ai_error": "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        "case_none": "Hali faol ishingiz yo'q. Nima kerakligi haqida yozing — boshlaymiz.",
        "case_info": (
            "Joriy ishingiz:\n"
            "• Xizmat: {service}\n"
            "• Status: {status}\n"
            "• To'lov: {payment}\n"
            "• Hujjatlar: {doc_count} ta"
        ),
        "help_text": (
            "UK viza, PAYE soliq qaytimi, mustaqil ishlovchi solig'i yoki "
            "kompaniya hisobi bo'yicha yordam beraman.\n\n"
            "Savolingizni yoki vaziyatingizni yozing."
        ),
        "doc_received": "Fayl qabul qilindi ✅",
    },
    "ru": {
        "welcome": "Добро пожаловать в Brightway Consulting 👋\nВыберите язык:",
        "intro": (
            "Привет! 👋 Я ваш AI-помощник в Brightway Consulting.\n\n"
            "Мы помогаем с:\n"
            "• 🎓 UK студенческая виза\n"
            "• 💷 Возврат налога PAYE\n"
            "• 🧾 Налог для самозанятых / Self Assessment\n"
            "• 🏢 Учёт компании\n\n"
            "Что вас интересует? Напишите в свободной форме."
        ),
        "ai_error": "Извините, что-то пошло не так. Попробуйте ещё раз.",
        "case_none": "У вас пока нет активного дела. Напишите что нужно — начнём.",
        "case_info": (
            "Ваше текущее дело:\n"
            "• Услуга: {service}\n"
            "• Статус: {status}\n"
            "• Оплата: {payment}\n"
            "• Документов загружено: {doc_count}"
        ),
        "help_text": (
            "Помогаю с UK визами, возвратом PAYE, налогом для самозанятых "
            "и учётом компании.\n\n"
            "Напишите вопрос или опишите ситуацию."
        ),
        "doc_received": "Файл получен ✅",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = T.get(lang, T["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ─────────────────────────── SERVICE DETECTION ───────────────────────────────

SERVICE_KEYWORDS = {
    "student": [
        "student", "visa", "university", "uni", "study", "degree", "masters",
        "bachelor", "postgraduate", "foundation", "college", "talaba", "viza",
        "o'qish", "университет", "студент", "виза", "учёба",
    ],
    "paye": [
        "paye", "employed", "employee", "p60", "p45", "payslip", "refund",
        "tax refund", "hmrc", "ni number", "national insurance", "income tax",
        "ish haqi", "soliq qaytimi", "возврат налога", "ндфл", "работаю",
    ],
    "self": [
        "self employed", "self-employed", "freelance", "freelancer",
        "sole trader", "utr", "self assessment", "deliveroo", "uber",
        "contractor", "mustaqil", "фрилансер", "самозанятый",
    ],
    "company": [
        "company", "limited", "ltd", "accounting", "bookkeeping", "vat",
        "payroll", "business", "director", "annual accounts", "corporation tax",
        "ct600", "companies house", "kompaniya", "компания", "бухгалтерия",
    ],
}


def detect_service(text: str):
    text_lower = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return service
    return None


# ──────────────────────────── AI SYSTEM PROMPTS ──────────────────────────────

SERVICE_INFO = {
    "student": {
        "name": "UK Student Visa",
        "collect": ["nationality", "which university and course", "intake date",
                    "CAS letter status", "English test result (IELTS/TOEFL)",
                    "funding source", "current location"],
        "documents": ["Passport (photo page)", "CAS letter (when available)",
                      "English test certificate", "Bank statements (28 days)",
                      "Sponsorship letter if family-funded"],
    },
    "paye": {
        "name": "PAYE Tax Refund",
        "collect": ["which tax years to claim", "number of employers",
                    "NI number", "bank details for refund"],
        "documents": ["P60 (one per year)", "P45 (if changed employer)", "Payslips"],
    },
    "self": {
        "name": "Self-Employed Tax / Self Assessment",
        "collect": ["tax year", "UTR number", "total income",
                    "expense records available (yes/no)",
                    "payments on account already made"],
        "documents": ["UTR confirmation", "Income records / invoices",
                      "Expense receipts", "Bank statements"],
    },
    "company": {
        "name": "Company Accounting",
        "collect": ["company name and number", "financial year end",
                    "approximate revenue", "number of directors",
                    "specific needs (accounts / CT600 / VAT / payroll)"],
        "documents": ["Business bank statements", "Bookkeeping file",
                      "Director details", "Previous accounts if any"],
    },
}

TONE_RULES = """
TONE AND STYLE:
- Sound like a real consultant in a live chat, not a scripted assistant.
- Professional, warm, and direct. Natural wording over formal template wording.
- Avoid repetitive openings and cliches.
- NEVER start with filler phrases like "Great!", "Excellent!", "Of course!", "Certainly!", "Understood!".
- Do not repeat the user's sentence back in different words unless needed for clarity.
- Ask exactly ONE clear question per message.
- Keep replies short (1-3 short sentences) unless sharing a document list.
- Use plain, natural wording for the user's language (especially Uzbek and Russian).
- If user is worried, reassure briefly, then continue with next practical step.
- Use emoji rarely (optional, max one and only when it fits naturally).
"""

ANTI_BOT_PATTERNS = """
AVOID BOT-LIKE PHRASES:
- "I understand that you need..."
- "Thank you for your message."
- "Please be informed that..."
- "As per your request..."
- "Kindly provide..."
- "Rest assured..."

Prefer natural alternatives:
- "Understood. Could you share ..."
- "Got it. What is ..."
- "Thanks. Please send ..."
"""

STYLE_EXAMPLES = """
STYLE EXAMPLES (follow this vibe):

EN:
User: "I need help with company accounting."
Bad: "Great — I understand you need help with company accounting. Kindly provide your company details."
Good: "Understood. Could you share your company name and Companies House number?"

UZ:
User: "Kompaniya hisobi kerak."
Bad: "Zo'r — kompaniya hisobi bo'yicha yordam kerakligini tushundim."
Good: "Tushunarli. Kompaniya nomi va Companies House raqamini yuborasizmi?"

RU:
User: "Нужна помощь по бухгалтерии компании."
Bad: "Отлично, я понял, что вам нужна помощь по бухгалтерии компании."
Good: "Понял. Подскажите, пожалуйста, название компании и номер в Companies House."
"""

GENERAL_SYSTEM_PROMPT = f"""You are a consultant at Brightway Consulting — a UK firm specialising in visas, tax, and accounting.

You're speaking with a potential client on Telegram. Understand what they need and guide them to the right service.

Services offered: UK Student Visa, PAYE Tax Refund, Self-Employed Tax / Self Assessment, Company Accounting.

{TONE_RULES}
{ANTI_BOT_PATTERNS}
{STYLE_EXAMPLES}
Always move the conversation forward naturally."""


def build_system_prompt(service: str, lang: str) -> str:
    if service == "general" or service not in SERVICE_INFO:
        return GENERAL_SYSTEM_PROMPT

    info = SERVICE_INFO[service]
    lang_map = {
        "en": "English",
        "uz": "Uzbek (Latin script)",
        "ru": "Russian",
    }
    reply_lang = lang_map.get(lang, "English")

    return f"""You work at Brightway Consulting, a UK firm. You're chatting with a client on Telegram about {info['name']}.

YOUR JOB — gather this info through natural conversation, one thing at a time:
{chr(10).join(f"- {item}" for item in info['collect'])}

DOCUMENTS you'll need from them (ask when the moment feels right, not all at once):
{chr(10).join(f"- {doc}" for doc in info['documents'])}

Once docs are uploaded: tell them the team will review and send payment info + next steps within 24-48h.
If they ask price: say the team confirms the exact fee after reviewing — it's competitive for what's included.

KEY FACTS:
- Visa: UKVI decides; we prepare the strongest possible application.
- Tax refunds: HMRC takes 4-12 weeks; we submit correctly and follow up.
- Company accounts: scope confirmed after reviewing their situation.

{TONE_RULES}
{ANTI_BOT_PATTERNS}
{STYLE_EXAMPLES}
Reply in {reply_lang}. Keep messages to 1-3 short sentences unless listing documents.
Use varied sentence structures so replies do not sound repetitive."""


# ────────────────────────────── AI CALLER ────────────────────────────────────

def ask_ai(conversation: list, service: str, lang: str) -> str:
    if not OPENAI_API_KEY:
        print("[AI] OPENAI_API_KEY missing")
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": build_system_prompt(service, lang)}]
        for msg in conversation[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        print(f"[AI] {service} | {len(conversation)} msgs | lang={lang}")
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
            max_completion_tokens=800,
        )
        reply = (resp.choices[0].message.content or "").strip()
        print(f"[AI] reply {len(reply)} chars")
        return reply or None
    except Exception as e:
        print(f"[AI] {type(e).__name__}: {e}")
        return None


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
