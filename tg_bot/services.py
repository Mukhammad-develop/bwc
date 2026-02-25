"""
Shared AI / service logic.
Imported by both bot.py (telebot) and userbot.py (Telethon).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ─────────────────────────── TRANSLATIONS ────────────────────────────────────

T = {
    "en": {
        "welcome":    "Welcome to Brightway Consulting 👋\nPlease choose your language:",
        "intro": (
            "Hi! I'm your AI assistant at Brightway Consulting.\n\n"
            "We help with:\n"
            "• 🎓 UK Student Visa\n"
            "• 💷 PAYE Tax Refund (HMRC)\n"
            "• 🧾 Self-Employed Tax / Self Assessment\n"
            "• 🏢 Company Accounting\n\n"
            "What do you need help with today? Just tell me in your own words."
        ),
        "ai_error":  "Sorry, something went wrong on my end. Please try again in a moment.",
        "case_none": "You don't have an active case yet. Just tell me what you need and we'll get started.",
        "case_info": (
            "Your current case:\n"
            "• Service: {service}\n"
            "• Status: {status}\n"
            "• Payment: {payment}\n"
            "• Documents uploaded: {doc_count}"
        ),
        "help_text": (
            "I can help with UK student visas, PAYE tax refunds, "
            "self-employed tax returns, or company accounting.\n\n"
            "Type your question or describe your situation."
        ),
        "doc_received": "Got your file ✅",
    },
    "uz": {
        "welcome":    "Brightway Consultingga xush kelibsiz 👋\nIltimos, tilni tanlang:",
        "intro": (
            "Salom! Men Brightway Consulting AI yordamchisiman.\n\n"
            "Quyidagi xizmatlarda yordam beramiz:\n"
            "• 🎓 UK talaba vizasi\n"
            "• 💷 PAYE soliq qaytimi (HMRC)\n"
            "• 🧾 Mustaqil ishlovchi solig'i / Self Assessment\n"
            "• 🏢 Kompaniya hisobi\n\n"
            "Bugun qanday masalada yordam kerak? Oddiy so'z bilan yozing."
        ),
        "ai_error":  "Kechirasiz, xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
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
        "welcome":    "Добро пожаловать в Brightway Consulting 👋\nВыберите язык:",
        "intro": (
            "Привет! Я AI-помощник Brightway Consulting.\n\n"
            "Мы помогаем с:\n"
            "• 🎓 UK студенческая виза\n"
            "• 💷 Возврат налога PAYE (HMRC)\n"
            "• 🧾 Налог для самозанятых / Self Assessment\n"
            "• 🏢 Учёт компании\n\n"
            "Что вас интересует? Напишите в свободной форме."
        ),
        "ai_error":  "Извините, что-то пошло не так. Попробуйте ещё раз.",
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
        # Uzbek
        "ish haqi", "soliq qaytimi", "soliq", "ishchi", "deklaratsiya",
        "vergi", "qaytim", "ishlayapman", "ishlagan",
        # Russian
        "возврат налога", "ндфл", "работаю", "работал", "налог", "возврат",
        "зарплата", "декларация",
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


# ─────────────────────────── SERVICE INFO & PROMPTS ──────────────────────────

SERVICE_INFO = {
    "student": {
        "name": "UK Student Visa",
        "collect": [
            "nationality", "which university and course", "intake date",
            "CAS letter status", "English test result (IELTS/TOEFL)",
            "funding source", "current location",
        ],
        "documents": [
            "Passport (photo page)", "CAS letter (when available)",
            "English test certificate", "Bank statements (28 days)",
            "Sponsorship letter if family-funded",
        ],
    },
    "paye": {
        "name": "HMRC Tax Return (PAYE)",
        "flow": """\
You are helping the client complete their HMRC PAYE tax return.
Collect the following items ONE AT A TIME, strictly in this order.
Do NOT ask for the next item until the previous one is provided or confirmed.

STEP 1 — P45 file
  Ask them to send their P45 as a PDF file.
  Once they send the file, immediately ask:
    "Is this file password protected?"
  If YES → ask them to share the password so we can open and process it.
  If NO  → move on to Step 2.

STEP 2 — Passport
  Ask for a photo or scan of the photo/ID page of their passport.

STEP 3 — Address outside England
  Ask for their residential address in their home country
  (Uzbekistan / Kazakhstan / Kyrgyzstan / Tajikistan).

STEP 4 — National Insurance number
  Ask for their NI number. If they are unsure where to find it,
  tell them it's on their payslip or P60, and looks like: AB 12 34 56 C.

STEP 5 — Email and phone number
  Ask for their email address and their phone number
  (UK number or home country number — either is fine).

STEP 6 — UK bank details
  Ask for their UK bank Sort Code (6 digits, format 12-34-56)
  and Account Number (8 digits). Explain this is where HMRC sends the refund.

STEP 7 — How many times worked in England
  Ask how many times they have come to work in England
  (first time ever, or total number of visits/employment periods).

COMPLETION
  Once all 7 steps are done, give a brief summary of everything collected,
  then tell them:
  "The Brightway team will now review everything and get back to you with
   the exact fee and next steps within 24-48 hours."
  Do not ask for anything else after this.

IMPORTANT NOTES:
- If the user sends a document before being asked, acknowledge it and
  continue from where you are in the flow (do not repeat steps already done).
- Never ask for more than one thing at a time.
- If the user asks about fees, say the fee is confirmed after reviewing
  the documents — competitive pricing for a full HMRC submission.
- HMRC refunds typically take 4-12 weeks once submitted.
""",
    },
    "self": {
        "name": "Self-Employed Tax / Self Assessment",
        "collect": [
            "tax year", "UTR number", "total income",
            "expense records available (yes/no)",
            "payments on account already made",
        ],
        "documents": [
            "UTR confirmation", "Income records / invoices",
            "Expense receipts", "Bank statements",
        ],
    },
    "company": {
        "name": "Company Accounting",
        "collect": [
            "company name and number", "financial year end",
            "approximate revenue", "number of directors",
            "specific needs (accounts / CT600 / VAT / payroll)",
        ],
        "documents": [
            "Business bank statements", "Bookkeeping file",
            "Director details", "Previous accounts if any",
        ],
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
- "Could you share ..."
- "Got it. What is ..."
- "Please send ..."
"""

STYLE_EXAMPLES = """
STYLE EXAMPLES (follow this vibe):

EN:
User: "I need help with company accounting."
Bad:  "Great — I understand you need help with company accounting. Kindly provide your company details."
Good: "Could you share your company name and Companies House number?"

UZ:
User: "Kompaniya hisobi kerak."
Bad:  "Zo'r — kompaniya hisobi bo'yicha yordam kerakligini tushundim."
Good: "Kompaniya nomi va Companies House raqamini yuborasizmi?"

RU:
User: "Нужна помощь по бухгалтерии компании."
Bad:  "Отлично, я понял, что вам нужна помощь."
Good: "Подскажите, пожалуйста, название компании и номер в Companies House."
"""

GENERAL_SYSTEM_PROMPT = f"""You are a consultant at Brightway Consulting — a UK firm specialising in visas, tax, and accounting.

You're speaking with a potential client on Telegram. Understand what they need and guide them to the right service.

Services offered: UK Student Visa, PAYE Tax Refund (HMRC), Self-Employed Tax / Self Assessment, Company Accounting.

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
        "uz": "Uzbek (Latin script, not Cyrillic)",
        "ru": "Russian",
    }
    reply_lang = lang_map.get(lang, "English")

    if "flow" in info:
        return f"""You work at Brightway Consulting, a UK firm helping Central Asian workers in England.
You're in a Telegram chat helping the client with: {info['name']}.

{info['flow']}

{TONE_RULES}
{ANTI_BOT_PATTERNS}
{STYLE_EXAMPLES}
LANGUAGE: Reply ONLY in {reply_lang}. Never switch languages even if the user writes in a different one.
Keep each message short and focused — one question, one instruction, or one confirmation at a time."""

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


# ─────────────────────────── AI CALLER ───────────────────────────────────────

def ask_ai(conversation: list, service: str, lang: str) -> str:
    if not OPENAI_API_KEY:
        print("[AI] OPENAI_API_KEY missing")
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": build_system_prompt(service, lang)}]
        for msg in conversation[-20:]:
            # Map any non-standard roles to valid OpenAI roles
            role = msg["role"]
            if role not in ("user", "assistant", "system"):
                role = "assistant"
            messages.append({"role": role, "content": msg["content"]})
        print(f"[AI] {service} | {len(conversation)} msgs | lang={lang}")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
        )
        reply = (resp.choices[0].message.content or "").strip()
        print(f"[AI] reply {len(reply)} chars")
        return reply or None
    except Exception as e:
        print(f"[AI] {type(e).__name__}: {e}")
        return None
