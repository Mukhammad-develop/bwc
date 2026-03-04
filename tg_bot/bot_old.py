import time
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types

import db
from config import (
    BOT_TOKEN,
    DB_PATH,
    TIMEZONE_OFFSET_HOURS,
    ADMIN_CHAT_ID,
    OPENAI_API_KEY,
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

db.init_db(DB_PATH)

LANGS = {
    "en": "English",
    "uz": "O‘zbek",
    "ru": "Русский",
}

T = {
    "en": {
        "welcome": "Welcome to Brightway Consulting 👋\nPlease choose your language:",
        "main_menu": "How can we help you today? Choose a service:",
        "my_case_btn": "📌 My case",
        "change_lang": "Change language",
        "talk_moderator": "Talk to moderator (AI)",
        "back_menu": "Back to menu",
        "start": "Start",
        "back": "Back",
        "student_title": "Student visa & university",
        "student_intro": "Great — we can help with university admission and the visa process.\nI’ll ask a few quick questions to check what you need.",
        "student_nationality": "What is your nationality (passport country)?",
        "student_apply_from": "Where are you applying from now (country/city)?",
        "student_qa": "Are you applying through QA (our partner)?",
        "student_intake": "When do you want to start your studies?",
        "student_level": "Which level are you applying for?",
        "student_english": "Do you already have English test results (IELTS/PTE)?",
        "student_budget": "Do you have a tuition budget range?",
        "student_summary": "Thanks. Here’s what we understood:\n• Service: Student visa & university\n• Applying from: {applying_from}\n• Level: {level}\n• Intake: {intake}\nNext step: we’ll review your details and tell you the exact documents and timeline.",
        "student_docs": "Please upload the following (clear photos or PDFs):\nPassport (main page)\nHighest education certificate + transcript\nEnglish test (if available)\nCV (if available)\nAny UK visa refusal letter (only if applicable)",
        "doc_upload_mode": "Choose which document you want to upload:",
        "send_doc": "Please send the file for: {doc}",
        "doc_received": "Received ✅",
        "upload_later": "I will upload later",
        "upload_now": "I will upload now",
        "payment_method": "Your documents are received ✅\nNow we can proceed with service payment.\nChoose a payment method:",
        "pay_online": "Pay online (recommended)",
        "bank_transfer": "Bank transfer",
        "payment_instructions_online": "Payment link: {link}\nInvoice reference: {ref}\nAfter payment, please send proof (screenshot or PDF).\nWe’ll confirm and start the process.",
        "payment_instructions_bank": "Bank details: {bank}\nReference: {ref}\nAfter payment, please send proof (screenshot or PDF).\nWe’ll confirm and start the process.",
        "upload_payment": "Upload payment proof",
        "upload_payment_prompt": "Please upload payment proof (screenshot or PDF).",
        "paye_intro": "We help you claim PAYE tax refunds from HMRC if you overpaid.\nI’ll ask a few questions to check eligibility.",
        "paye_worked": "Did you work in the UK and pay PAYE tax?",
        "paye_not_eligible": "If you didn’t work in the UK with PAYE, a PAYE refund may not apply.\nYou can still talk to the AI moderator or continue in the menu.",
        "paye_year": "Which tax year is your refund for?",
        "paye_employment": "How were you working?",
        "paye_docs_available": "Do you have any of these documents?",
        "paye_ni": "Do you have your National Insurance (NI) number?",
        "paye_summary": "Thanks. Next we need your documents to calculate and submit your refund claim.",
        "paye_docs": "Please upload (clear photos or PDFs):\nPassport (main page)\nNI number (photo or typed)\nP60 or P45 (if you have)\nLatest payslips (if you have)\nHMRC letters (if any)",
        "paye_payment": "Our service fee will be confirmed after we review your documents (or we can give a standard fee if your company uses fixed pricing).\nChoose payment method:",
        "self_intro": "We help self-employed individuals (sole traders/freelancers) with Self Assessment, record advice, and deadlines.",
        "self_registered": "Are you registered as self-employed with HMRC?",
        "self_register_help": "We can help you register and set up properly.",
        "self_year": "Which tax year do you need help with?",
        "self_income": "Roughly what is your income range for that year?",
        "self_expenses": "Do you have your expenses records?",
        "self_urgent": "Is it urgent (deadline soon)?",
        "self_docs": "Please upload (clear photos or PDFs):\nPassport (main page)\nUTR number (if you have)\nIncome records (invoices / bank statements summary)\nExpense records (receipts / spreadsheet)\nAny HMRC letters (if any)",
        "company_intro": "We support small businesses, startups, and UK limited companies with accounts, corporation tax, payroll, VAT, and ongoing advice.",
        "company_type": "What type of business is it?",
        "company_number": "Do you have a Companies House number?",
        "company_need": "What do you need most right now?",
        "company_activity": "Roughly how active is the business?",
        "company_urgent": "Is there a deadline soon (Companies House / HMRC)?",
        "company_next": "Thanks. Next we will review your information and tell you the exact plan and price.",
        "company_docs": "Please upload (if available):\nCompany details (company number or incorporation certificate)\nBank statements (business)\nExisting bookkeeping files (if any)\nVAT details (if registered)\nPayroll info (if needed)",
        "company_quote": "For company accounting, pricing depends on workload.\nWe can prepare a quick quote after reviewing your info.",
        "chat_ai_intro": "You're chatting with the AI moderator. Send your question or message below — I'll reply here. Use the button to return to the menu.",
        "chat_ai_error": "The AI is temporarily unavailable. Please try again in a moment or return to the menu.",
        "my_case": "Here is your current status:\n• Service: {service}\n• Status: {status}\n• Payment: {payment}\n• Missing: {missing}",
        "completed": "✅ Your case is completed. Thank you for choosing Brightway Consulting.\nIf you need help again (tax, visa, accounting), just message us here.",
        "feedback": "Leave feedback",
        "start_new": "Start new request",
        "invalid_country": "Please type the country name (example: Uzbekistan).",
        "choose_doc_first": "Please choose a document first.",
        "privacy": "Your documents are used only for your service and handled securely.",
        "visa_note": "Important: Visa decisions are made by official authorities. We support your application and process, but we cannot guarantee approval.",
        "tax_note": "Important: HMRC processing times vary. We submit correctly and follow up, but final timing depends on HMRC.",
        "next": "✅ Next: {next}",
        "eta": "⏳ Expected time: {eta}",
        "yes": "Yes",
        "no_not_sure": "No / Not sure",
        "other": "Other",
        "done_uploading": "Done uploading",
        "doc_dont_have": "I don't have this",
        "doc_back_list": "Back to list",
        "upload_docs_btn": "Upload documents",
        "upload_payment_btn": "Upload payment proof",
        "reminder_doc": "Friendly reminder: we still need your documents to start your case.",
        "reminder_payment": "Once you've paid, please upload proof so we can begin.",
        "intake_mar_apr": "March / April",
        "intake_sep": "September",
        "paye_year_older": "Older",
        "paye_emp_one": "One job",
        "paye_emp_multi": "Multiple jobs",
        "paye_emp_agency": "Agency / temporary",
        "paye_ni_yes": "Yes (type it)",
        "paye_ni_no": "No / I don't know",
        "self_urgent_urgent": "Urgent",
        "self_urgent_normal": "Normal",
        "company_type_ltd": "Limited company (Ltd)",
        "company_type_sole": "Sole trader",
        "company_type_unreg": "Not registered yet",
        "company_number_yes": "Yes (type it)",
        "company_number_no": "No / not sure",
        "company_urgent_yes": "Yes, urgent",
        "company_urgent_no": "No",
        "company_activity_small": "Small (few transactions)",
        "company_activity_medium": "Medium",
        "company_activity_busy": "Busy",
        "not_sure": "Not sure",
        "prefer_not_say": "Prefer not to say",
        "footer_questions": "Answer a few questions",
        "footer_eligibility": "Check eligibility",
        "footer_2_3_min": "2–3 minutes",
        "footer_continue": "Continue",
        "footer_update": "We'll update you",
        "help_text": "This bot helps you with:\n• Student visa & university (QA partner)\n• PAYE tax refund (HMRC)\n• Self-employed tax (Self Assessment)\n• Company accounting\n\nUse /start to begin or choose a service.\n/case or /mycase — see your current case status.\n\nQuestions? Use «Talk to moderator (AI)» in the menu.",
        "service_student": "🎓 Student visa & university (QA partner)",
        "service_paye": "💷 PAYE Tax Refund (HMRC)",
        "service_self": "🧾 Self-Employed Tax (Self Assessment)",
        "service_company": "🏢 Company Accounting (Ltd / payroll / VAT)",
    },
    "uz": {
        "welcome": "Brightway Consultingga xush kelibsiz 👋\nIltimos, tilni tanlang:",
        "main_menu": "Bugun qanday yordam kerak? Quyidagi xizmatlardan birini tanlang:",
        "my_case_btn": "📌 Mening ishim",
        "change_lang": "Tilni o‘zgartirish",
        "talk_moderator": "Moderator (AI) bilan suhbat",
        "back_menu": "Menyuga qaytish",
        "start": "Boshlash",
        "back": "Orqaga",
        "student_title": "Talaba vizasi va universitet",
        "student_intro": "Ajoyib — universitet qabul va viza jarayonida yordam beramiz.\nBir nechta qisqa savol beraman.",
        "student_nationality": "Fuqaroligingiz (pasport davlati) qaysi?",
        "student_apply_from": "Hozir qayerdan topshiryapsiz (davlat/shahar)?",
        "student_qa": "QA (hamkorimiz) orqali topshiryapsizmi?",
        "student_intake": "Qachon o‘qishni boshlamoqchisiz?",
        "student_level": "Qaysi darajaga topshiryapsiz?",
        "student_english": "IELTS/PTE natijalaringiz bormi?",
        "student_budget": "O‘qish uchun byudjet oralig‘ingiz bormi?",
        "student_summary": "Rahmat. Qisqa xulosa:\n• Xizmat: Talaba vizasi va universitet\n• Qayerdan: {applying_from}\n• Daraja: {level}\n• Intake: {intake}\nKeyingi qadam: hujjatlaringizni tekshirib, aniq ro‘yxat va muddatni aytamiz.",
        "student_docs": "Iltimos, quyidagilarni yuboring (aniq foto yoki PDF):\nPasport (asosiy sahifa)\nEng yuqori ta’lim diplomi va transkript\nEnglish test (bo‘lsa)\nCV (bo‘lsa)\nUK viza rad xati (bo‘lsa)",
        "doc_upload_mode": "Qaysi hujjatni yubormoqchisiz?",
        "send_doc": "Iltimos, quyidagi hujjatni yuboring: {doc}",
        "doc_received": "Qabul qilindi ✅",
        "upload_later": "Keyin yuboraman",
        "upload_now": "Hozir yuboraman",
        "payment_method": "Hujjatlar qabul qilindi ✅\nEndi to‘lovni boshlashimiz mumkin.\nTo‘lov usulini tanlang:",
        "pay_online": "Onlayn to‘lov (tavsiya etiladi)",
        "bank_transfer": "Bank o‘tkazmasi",
        "payment_instructions_online": "To‘lov havolasi: {link}\nHisob raqami: {ref}\nTo‘lovdan so‘ng skrinshot/PDF yuboring.\nTasdiqlab jarayonni boshlaymiz.",
        "payment_instructions_bank": "Bank ma’lumotlari: {bank}\nIzoh: {ref}\nTo‘lovdan so‘ng skrinshot/PDF yuboring.\nTasdiqlab jarayonni boshlaymiz.",
        "upload_payment": "To‘lov cheki",
        "upload_payment_prompt": "Iltimos, to‘lov chekini yuboring (screenshot yoki PDF).",
        "paye_intro": "PAYE soliq qaytimi bo‘yicha yordam beramiz.\nBir nechta savol beraman.",
        "paye_worked": "UKda ishlaganmisiz va PAYE soliq to‘laganmisiz?",
        "paye_not_eligible": "Agar UKda PAYE bilan ishlamagan bo‘lsangiz, qaytim mos bo‘lmasligi mumkin.\nAI moderator bilan suhbat qilishingiz yoki menyudan davom etishingiz mumkin.",
        "paye_year": "Qaysi soliq yili uchun?",
        "paye_employment": "Qanday ishlagansiz?",
        "paye_docs_available": "Quyidagi hujjatlaringiz bormi?",
        "paye_ni": "NI raqamingiz bormi?",
        "paye_summary": "Rahmat. Endi hisoblash va topshirish uchun hujjatlar kerak.",
        "paye_docs": "Iltimos yuboring (foto yoki PDF):\nPasport (asosiy sahifa)\nNI raqami (foto yoki yozma)\nP60/P45 (bo‘lsa)\nSo‘nggi paysliplar (bo‘lsa)\nHMRC xatlari (bo‘lsa)",
        "paye_payment": "To‘lov miqdori hujjatlarni ko‘rib chiqilgach tasdiqlanadi.\nTo‘lov usulini tanlang:",
        "self_intro": "Self Assessment bo‘yicha yordam beramiz.",
        "self_registered": "HMRCda self-employed sifatida ro‘yxatdan o‘tganmisiz?",
        "self_register_help": "Ro‘yxatdan o‘tishda yordam bera olamiz.",
        "self_year": "Qaysi soliq yili kerak?",
        "self_income": "Daromad oralig‘i?",
        "self_expenses": "Xarajatlar qaydlari bormi?",
        "self_urgent": "Shoshilinchmi (muddat yaqin)?",
        "self_docs": "Iltimos yuboring:\nPasport (asosiy sahifa)\nUTR (bo‘lsa)\nDaromad hujjatlari\nXarajat hujjatlari\nHMRC xatlari (bo‘lsa)",
        "company_intro": "Kompaniya hisobini yuritishda yordam beramiz.",
        "company_type": "Biznes turi qanday?",
        "company_number": "Companies House raqami bormi?",
        "company_need": "Hozir eng kerakli xizmat?",
        "company_activity": "Faollik darajasi qanday?",
        "company_urgent": "Muddat yaqinmi?",
        "company_next": "Rahmat. Ma’lumotni ko‘rib, reja va narxni aytamiz.",
        "company_docs": "Iltimos yuboring (bo‘lsa):\nKompaniya ma’lumotlari\nBank statementlar\nBuxgalteriya fayllari\nVAT ma’lumotlari\nPayroll ma’lumotlari",
        "company_quote": "Narx ish hajmiga bog‘liq. Ma’lumotdan so‘ng tezkor taklif beramiz.",
        "chat_ai_intro": "Siz AI moderator bilan suhbatdasiz. Savolingizni yuboring — javobni shu yerga yozaman. Menyuga qaytish uchun tugmani bosing.",
        "chat_ai_error": "AI hozircha ishlamayapti. Iltimos, keyinroq urinib ko‘ring yoki menyuga qayting.",
        "my_case": "Hozirgi holat:\n• Xizmat: {service}\n• Status: {status}\n• To‘lov: {payment}\n• Yetishmayapti: {missing}",
        "completed": "✅ Ish yakunlandi. Brightway Consultingni tanlaganingiz uchun rahmat.\nYana kerak bo‘lsa, shu yerga yozing.",
        "feedback": "Baholash",
        "start_new": "Yangi so‘rov",
        "invalid_country": "Iltimos, davlat nomini yozing (masalan: Uzbekistan).",
        "choose_doc_first": "Avval hujjatni tanlang.",
        "privacy": "Hujjatlaringiz faqat xizmat uchun ishlatiladi va xavfsiz saqlanadi.",
        "visa_note": "Muhim: Viza qarorini rasmiy idoralar qabul qiladi. Biz yordam beramiz, lekin kafolat bera olmaymiz.",
        "tax_note": "Muhim: HMRC muddatlari o‘zgarishi mumkin. Biz to‘g‘ri topshiramiz, lekin vaqt HMRCga bog‘liq.",
        "next": "✅ Keyingi: {next}",
        "eta": "⏳ Kutilayotgan vaqt: {eta}",
        "yes": "Ha",
        "no_not_sure": "Yo'q / Aniq emasman",
        "other": "Boshqa",
        "done_uploading": "Yuborishni tugatdim",
        "doc_dont_have": "Buni yo'q",
        "doc_back_list": "Ro'yxatga qaytish",
        "upload_docs_btn": "Hujjatlar yuborish",
        "upload_payment_btn": "To'lov tasdiqini yuborish",
        "reminder_doc": "Eslatma: ishingizni boshlash uchun hujjatlar hali kerak.",
        "reminder_payment": "To'lovni amalga oshirganingizdan so'ng tasdiqni yuboring — shunda boshlaymiz.",
        "intake_mar_apr": "Mart / Aprel",
        "intake_sep": "Sentyabr",
        "paye_year_older": "Undan oldingi",
        "paye_emp_one": "Bitta ish",
        "paye_emp_multi": "Bir nechta ish",
        "paye_emp_agency": "Agentlik / vaqtincha",
        "paye_ni_yes": "Ha (yozing)",
        "paye_ni_no": "Yo'q / Bilmayman",
        "self_urgent_urgent": "Shoshilinch",
        "self_urgent_normal": "Oddiy",
        "company_type_ltd": "Limited kompaniya (Ltd)",
        "company_type_sole": "Yakka tadbirkor",
        "company_type_unreg": "Hali ro'yxatdan o'tmagan",
        "company_number_yes": "Ha (yozing)",
        "company_number_no": "Yo'q / aniq emas",
        "company_urgent_yes": "Ha, shoshilinch",
        "company_urgent_no": "Yo'q",
        "company_activity_small": "Kichik (oz operatsiya)",
        "company_activity_medium": "O'rta",
        "company_activity_busy": "Ishlar ko'p",
        "not_sure": "Aniq emasman",
        "prefer_not_say": "Aytishni xohlamayman",
        "footer_questions": "Bir nechta savolga javob bering",
        "footer_eligibility": "Imkoniyatni tekshirish",
        "footer_2_3_min": "2–3 daqiqa",
        "footer_continue": "Davom etish",
        "footer_update": "Sizga xabar beramiz",
        "help_text": "Bot quyidagilarda yordam beradi:\n• Talaba vizasi va universitet (QA hamkor)\n• PAYE soliq qaytimi (HMRC)\n• Mustaqil ishlovchi solig'i (Self Assessment)\n• Kompaniya hisobi\n\nBoshlash: /start\nIshingiz holati: /case yoki /mycase\n\nSavol bormi? Menydan «Moderator (AI) bilan suhbat»ni tanlang.",
        "service_student": "🎓 Talaba vizasi va universitet (QA hamkor)",
        "service_paye": "💷 PAYE soliq qaytimi (HMRC)",
        "service_self": "🧾 Mustaqil ishlovchi solig'i (Self Assessment)",
        "service_company": "🏢 Kompaniya hisobi (Ltd / ish haqi / QQS)",
    },
    "ru": {
        "welcome": "Добро пожаловать в Brightway Consulting 👋\nВыберите язык:",
        "main_menu": "Чем мы можем помочь сегодня? Выберите услугу:",
        "my_case_btn": "📌 Моё дело",
        "change_lang": "Изменить язык",
        "talk_moderator": "Написать модератору (AI)",
        "back_menu": "Назад в меню",
        "start": "Начать",
        "back": "Назад",
        "student_title": "Студенческая виза и университет",
        "student_intro": "Отлично — поможем с поступлением и визой.\nЗадам несколько коротких вопросов.",
        "student_nationality": "Ваше гражданство (страна паспорта)?",
        "student_apply_from": "Откуда вы подаете сейчас (страна/город)?",
        "student_qa": "Подаете через QA (наш партнер)?",
        "student_intake": "Когда хотите начать обучение?",
        "student_level": "На какой уровень поступаете?",
        "student_english": "Есть результаты IELTS/PTE?",
        "student_budget": "Есть бюджет на обучение?",
        "student_summary": "Спасибо. Кратко:\n• Услуга: Студенческая виза и университет\n• Откуда: {applying_from}\n• Уровень: {level}\n• Intake: {intake}\nДалее мы проверим данные и дадим точный список документов и сроки.",
        "student_docs": "Пожалуйста, загрузите (четкие фото или PDF):\nПаспорт (главная страница)\nДиплом + транскрипт\nEnglish test (если есть)\nCV (если есть)\nПисьмо об отказе UK визы (если есть)",
        "doc_upload_mode": "Какой документ хотите загрузить?",
        "send_doc": "Пожалуйста, отправьте файл: {doc}",
        "doc_received": "Получено ✅",
        "upload_later": "Загружу позже",
        "upload_now": "Загружу сейчас",
        "payment_method": "Документы получены ✅\nТеперь можно перейти к оплате услуги.\nВыберите способ оплаты:",
        "pay_online": "Оплатить онлайн (рекомендуем)",
        "bank_transfer": "Банковский перевод",
        "payment_instructions_online": "Ссылка на оплату: {link}\nНомер счета: {ref}\nПосле оплаты пришлите подтверждение.\nМы подтвердим и начнем процесс.",
        "payment_instructions_bank": "Реквизиты банка: {bank}\nНазначение: {ref}\nПосле оплаты пришлите подтверждение.\nМы подтвердим и начнем процесс.",
        "upload_payment": "Загрузить подтверждение оплаты",
        "upload_payment_prompt": "Пожалуйста, загрузите подтверждение оплаты (скриншот или PDF).",
        "paye_intro": "Помогаем вернуть переплату PAYE от HMRC.\nЗадам несколько вопросов.",
        "paye_worked": "Вы работали в UK и платили PAYE?",
        "paye_not_eligible": "Если вы не работали в UK с PAYE, возврат может не подойти.\nМожно написать модератору (AI) или продолжить в меню.",
        "paye_year": "За какой налоговый год возврат?",
        "paye_employment": "Как вы работали?",
        "paye_docs_available": "Есть ли у вас эти документы?",
        "paye_ni": "Есть NI номер?",
        "paye_summary": "Спасибо. Теперь нужны документы для расчета и подачи.",
        "paye_docs": "Пожалуйста, загрузите (фото или PDF):\nПаспорт (главная страница)\nNI номер (фото или текст)\nP60/P45 (если есть)\nПоследние payslips (если есть)\nПисьма HMRC (если есть)",
        "paye_payment": "Стоимость подтвердим после проверки документов.\nВыберите способ оплаты:",
        "self_intro": "Помогаем с Self Assessment для самозанятых.",
        "self_registered": "Вы зарегистрированы как self-employed в HMRC?",
        "self_register_help": "Можем помочь с регистрацией.",
        "self_year": "За какой налоговый год нужна помощь?",
        "self_income": "Примерный доход за год?",
        "self_expenses": "Есть учет расходов?",
        "self_urgent": "Срочно (дедлайн скоро)?",
        "self_docs": "Пожалуйста, загрузите:\nПаспорт (главная страница)\nUTR (если есть)\nДоходы\nРасходы\nПисьма HMRC (если есть)",
        "company_intro": "Поддержка компаний: отчеты, налог, payroll, VAT.",
        "company_type": "Тип бизнеса?",
        "company_number": "Есть номер Companies House?",
        "company_need": "Что нужно в первую очередь?",
        "company_activity": "Насколько активен бизнес?",
        "company_urgent": "Есть срочный дедлайн?",
        "company_next": "Спасибо. Мы проверим информацию и сообщим план и цену.",
        "company_docs": "Пожалуйста, загрузите (если есть):\nДанные компании\nВыписки банка\nФайлы бухучета\nДанные VAT\nДанные payroll",
        "company_quote": "Цена зависит от объема. После проверки дадим предложение.",
        "chat_ai_intro": "Вы в чате с AI-модератором. Напишите ваш вопрос — я отвечу здесь. Кнопка ниже вернёт в меню.",
        "chat_ai_error": "AI временно недоступен. Попробуйте позже или вернитесь в меню.",
        "my_case": "Текущий статус:\n• Услуга: {service}\n• Статус: {status}\n• Оплата: {payment}\n• Не хватает: {missing}",
        "completed": "✅ Дело завершено. Спасибо, что выбрали Brightway Consulting.\nЕсли нужно снова — напишите здесь.",
        "feedback": "Оставить отзыв",
        "start_new": "Новый запрос",
        "invalid_country": "Пожалуйста, напишите название страны (например: Uzbekistan).",
        "choose_doc_first": "Сначала выберите документ.",
        "privacy": "Ваши документы используются только для вашего сервиса и хранятся безопасно.",
        "visa_note": "Важно: Решение по визе принимает государственный орган. Мы поддерживаем процесс, но не гарантируем результат.",
        "tax_note": "Важно: Сроки HMRC могут меняться. Мы подаем корректно, но время зависит от HMRC.",
        "next": "✅ Далее: {next}",
        "eta": "⏳ Ожидаемое время: {eta}",
        "yes": "Да",
        "no_not_sure": "Нет / Не уверен",
        "other": "Другое",
        "done_uploading": "Загрузка завершена",
        "doc_dont_have": "Этого документа нет",
        "doc_back_list": "К списку",
        "upload_docs_btn": "Загрузить документы",
        "upload_payment_btn": "Загрузить подтверждение оплаты",
        "reminder_doc": "Напоминание: нам по-прежнему нужны ваши документы, чтобы начать дело.",
        "reminder_payment": "После оплаты пришлите подтверждение — тогда мы начнём.",
        "intake_mar_apr": "Март / Апрель",
        "intake_sep": "Сентябрь",
        "paye_year_older": "Раньше",
        "paye_emp_one": "Одна работа",
        "paye_emp_multi": "Несколько работ",
        "paye_emp_agency": "Агентство / временная",
        "paye_ni_yes": "Да (введите)",
        "paye_ni_no": "Нет / Не знаю",
        "self_urgent_urgent": "Срочно",
        "self_urgent_normal": "Обычно",
        "company_type_ltd": "Limited компания (Ltd)",
        "company_type_sole": "ИП / самозанятый",
        "company_type_unreg": "Ещё не зарегистрированы",
        "company_number_yes": "Да (введите)",
        "company_number_no": "Нет / не уверен",
        "company_urgent_yes": "Да, срочно",
        "company_urgent_no": "Нет",
        "company_activity_small": "Мало операций",
        "company_activity_medium": "Средне",
        "company_activity_busy": "Много операций",
        "not_sure": "Не уверен",
        "prefer_not_say": "Предпочитаю не говорить",
        "footer_questions": "Ответьте на несколько вопросов",
        "footer_eligibility": "Проверить возможность возврата",
        "footer_2_3_min": "2–3 минуты",
        "footer_continue": "Продолжить",
        "footer_update": "Мы сообщим вам",
        "help_text": "Бот помогает с:\n• Студенческая виза и университет (партнёр QA)\n• Возврат налога PAYE (HMRC)\n• Налог для самозанятых (Self Assessment)\n• Учёт компании\n\nНачать: /start\nСтатус дела: /case или /mycase\n\nВопросы? В меню выберите «Написать модератору (AI)».",
        "service_student": "🎓 Студенческая виза и университет (партнёр QA)",
        "service_paye": "💷 Возврат налога PAYE (HMRC)",
        "service_self": "🧾 Налог для самозанятых (Self Assessment)",
        "service_company": "🏢 Учёт компании (Ltd / зарплата / НДС)",
    },
}

SERVICES = {
    "student": "🎓 Student visa & university (QA partner)",
    "paye": "💷 PAYE Tax Refund (HMRC)",
    "self": "🧾 Self-Employed Tax (Self Assessment)",
    "company": "🏢 Company Accounting (Ltd / payroll / VAT)",
}

STUDENT_DOCS = [
    "Passport (main page)",
    "Highest education certificate + transcript",
    "English test (if available)",
    "CV (if available)",
    "Any UK visa refusal letter (if applicable)",
]

PAYE_DOCS = [
    "Passport (main page)",
    "NI number",
    "P60 or P45",
    "Latest payslips",
    "HMRC letters",
]

SELF_DOCS = [
    "Passport (main page)",
    "UTR number",
    "Income records",
    "Expense records",
    "HMRC letters",
]

COMPANY_DOCS = [
    "Company details",
    "Business bank statements",
    "Bookkeeping files",
    "VAT details",
    "Payroll info",
]


def t(lang: str, key: str, **kwargs):
    text = T.get(lang, T["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def footer(
    lang: str, next_key: str = "footer_continue", eta_key: str = "footer_update"
):
    return f"\n\n{t(lang, 'next', next=t(lang, next_key))}\n{t(lang, 'eta', eta=t(lang, eta_key))}"


AI_MODERATOR_SYSTEM_PROMPT = """You are the AI moderator for Brightway Consulting, a UK-based firm that helps clients with:

1. **Student visa & university** – University admission and UK student visa (including via QA partner). Documents: passport, education certificates, English test (IELTS/PTE), CV, visa refusal letter if any.
2. **PAYE tax refund** – Claiming overpaid PAYE from HMRC. Documents: passport, NI number, P60/P45, payslips, HMRC letters.
3. **Self-employed tax (Self Assessment)** – For sole traders and freelancers. UTR, income/expense records, HMRC letters.
4. **Company accounting** – Ltd companies: accounts, corporation tax, payroll, VAT, bookkeeping.

Rules:
- Reply in the SAME language the user writes in: if they write in English use English, if in Russian use Russian, if in Uzbek use Uzbek (Latin script). If unclear, default to English.
- Be helpful, professional, and concise. Keep replies suitable for a Telegram message (not too long).
- Do NOT guarantee visa approval, refund amounts, or tax outcomes. Say that final decisions are with authorities (UKVI, HMRC) and we support the process.
- For document lists, deadlines, or case-specific steps, suggest they continue in the bot flow or provide general guidance.
- If the question is about pricing or a quote, say that the team will confirm after reviewing their details/documents.
- Do not give legal or regulated advice; direct complex or personal cases to the bot’s main menu or say the team will follow up.
- Stay on topic: Brightway services (visa, PAYE, self-employed, company accounting). Politely deflect off-topic or abusive content."""


def ask_ai(user_message: str, lang: str):
    if not OPENAI_API_KEY:
        print("[AI] OPENAI_API_KEY is missing or empty. Set it in .env")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        print("[AI] Calling OpenAI (gpt-4o-mini)...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": AI_MODERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=600,
        )
        content = (response.choices[0].message.content or "").strip() or None
        if content:
            print("[AI] Reply received, length:", len(content))
        else:
            print("[AI] Empty reply from API")
        return content
    except Exception as e:
        print("[AI] Error:", type(e).__name__, str(e))
        return None


def lang_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇺🇿 O‘zbek", callback_data="lang_uz"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
    )
    return kb


def main_menu_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            t(lang, "service_student"), callback_data="service_student"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            t(lang, "service_paye"), callback_data="service_paye"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            t(lang, "service_self"), callback_data="service_self"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            t(lang, "service_company"), callback_data="service_company"
        )
    )
    kb.add(types.InlineKeyboardButton(t(lang, "my_case_btn"), callback_data="my_case"))
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🌐 " + t(lang, "change_lang"), callback_data="change_lang"
        )
    )
    return kb


def back_menu_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def text_input_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    return kb


def start_back_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("▶️ " + t(lang, "start"), callback_data="start_flow")
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def yes_no_kb(lang: str, yes_cb: str, no_cb: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ " + t(lang, "yes"), callback_data=yes_cb))
    kb.add(
        types.InlineKeyboardButton("❌ " + t(lang, "no_not_sure"), callback_data=no_cb)
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def document_select_kb(lang: str, docs):
    kb = types.InlineKeyboardMarkup()
    for d in docs:
        kb.add(types.InlineKeyboardButton(d, callback_data=f"doc_{d}"))
    kb.add(
        types.InlineKeyboardButton(
            "✔️ " + t(lang, "done_uploading"), callback_data="doc_done"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def doc_wait_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "➖ " + t(lang, "doc_dont_have"), callback_data="doc_missing"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "↩️ " + t(lang, "doc_back_list"), callback_data="doc_back_list"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def payment_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "💳 " + t(lang, "pay_online"), callback_data="pay_online"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🏦 " + t(lang, "bank_transfer"), callback_data="pay_bank"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    return kb


def upload_payment_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📤 " + t(lang, "upload_payment"), callback_data="upload_payment"
        )
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def ai_chat_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    return kb


def upload_choice_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "✅ " + t(lang, "upload_now"), callback_data="upload_now"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "⏳ " + t(lang, "upload_later"), callback_data="upload_later"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(types.InlineKeyboardButton("🔙 " + t(lang, "back"), callback_data="menu"))
    return kb


def doc_list_for_service(service: str):
    if service == "student":
        return STUDENT_DOCS
    if service == "paye":
        return PAYE_DOCS
    if service == "self":
        return SELF_DOCS
    if service == "company":
        return COMPANY_DOCS
    return []


def doc_checklist_text(lang: str, service: str):
    if service == "student":
        return t(lang, "student_docs") + "\n\n" + t(lang, "visa_note")
    if service == "paye":
        return t(lang, "paye_docs") + "\n\n" + t(lang, "tax_note")
    if service == "self":
        return t(lang, "self_docs") + "\n\n" + t(lang, "tax_note")
    if service == "company":
        return t(lang, "company_docs")
    return ""


def set_stage(conn, case_id, stage: str, **kwargs):
    db.update_case(conn, case_id, stage=stage, **kwargs)


def get_case_and_lang(message):
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        case = db.get_active_case(conn, user_id)
        lang = db.get_language(conn, message.from_user.id)
    return case, lang


def ensure_case(conn, user_id: int, service: str):
    case_id = db.create_case(conn, user_id, service)
    return db.get_active_case(conn, user_id)


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
    bot.send_message(
        message.chat.id, t(lang, "help_text"), reply_markup=main_menu_kb(lang)
    )


@bot.message_handler(commands=["mycase", "case"])
def handle_my_case(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
        case = db.get_active_case(conn, user_id)
        if not case:
            bot.send_message(
                message.chat.id, t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
            )
            return
        missing = ", ".join(db.get_missing_docs(conn, case["id"])) or "-"
        service_name = (
            t(lang, "service_" + case["service"])
            if case["service"] in ("student", "paye", "self", "company")
            else case["service"]
        )
        text = t(
            lang,
            "my_case",
            service=service_name,
            status=case["status"],
            payment=case["payment_status"],
            missing=missing,
        )
        bot.send_message(message.chat.id, text, reply_markup=back_menu_kb(lang))


@bot.message_handler(commands=["start"])
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
        chat_mode = db.get_chat_mode(conn, message.from_user.id)
        if (message.text or "").strip() == "/start":
            db.set_chat_mode(conn, message.from_user.id, "menu")
            case = db.get_active_case(conn, user_id)
            if not case:
                bot.send_message(
                    message.chat.id, t(lang, "welcome"), reply_markup=lang_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    t(lang, "main_menu"),
                    reply_markup=main_menu_kb(lang),
                )
            return

        if chat_mode == "ai":
            user_message = (message.text or "").strip()
            if not user_message:
                bot.send_message(
                    message.chat.id,
                    t(lang, "chat_ai_intro"),
                    reply_markup=ai_chat_kb(lang),
                )
                return
            reply = ask_ai(user_message, lang)
            if reply:
                bot.send_message(message.chat.id, reply, reply_markup=ai_chat_kb(lang))
            else:
                bot.send_message(
                    message.chat.id,
                    t(lang, "chat_ai_error"),
                    reply_markup=ai_chat_kb(lang),
                )
            return

        case = db.get_active_case(conn, user_id)
        if not case:
            bot.send_message(
                message.chat.id, t(lang, "welcome"), reply_markup=lang_keyboard()
            )
            return

        stage = case["stage"]
        text = message.text.strip() if message.text else ""

        if stage == "student_nationality":
            if len(text) < 2 or any(char.isdigit() for char in text):
                bot.send_message(message.chat.id, t(lang, "invalid_country"))
                return
            db.update_case(conn, case["id"], nationality=text)
            set_stage(conn, case["id"], "student_apply_from")
            bot.send_message(
                message.chat.id,
                t(lang, "student_apply_from"),
                reply_markup=text_input_kb(lang),
            )
            return

        if stage == "student_apply_from":
            db.update_case(conn, case["id"], applying_from=text)
            set_stage(conn, case["id"], "student_qa")
            bot.send_message(
                message.chat.id,
                t(lang, "student_qa"),
                reply_markup=yes_no_kb(lang, "qa_yes", "qa_no"),
            )
            return

        if stage == "student_intake_other":
            db.update_case(conn, case["id"], intake=text)
            set_stage(conn, case["id"], "student_level")
            bot.send_message(
                message.chat.id,
                t(lang, "student_level"),
                reply_markup=student_level_kb(lang),
            )
            return

        if stage == "student_level_other":
            db.update_case(conn, case["id"], level=text)
            set_stage(conn, case["id"], "student_english")
            bot.send_message(
                message.chat.id,
                t(lang, "student_english"),
                reply_markup=yes_no_kb(lang, "eng_yes", "eng_no"),
            )
            return

        if stage == "student_budget_other":
            db.update_case(conn, case["id"], budget=text)
            send_student_summary(message.chat.id, conn, case["id"], lang)
            return

        if stage == "paye_year_other":
            db.update_case(conn, case["id"], tax_year=text)
            set_stage(conn, case["id"], "paye_employment")
            bot.send_message(
                message.chat.id,
                t(lang, "paye_employment"),
                reply_markup=paye_employment_kb(lang),
            )
            return

        if stage == "paye_ni_enter":
            db.update_case(conn, case["id"], ni_number=text)
            send_paye_summary(message.chat.id, conn, case["id"], lang)
            return

        if stage == "self_year_other":
            db.update_case(conn, case["id"], tax_year=text)
            set_stage(conn, case["id"], "self_income")
            bot.send_message(
                message.chat.id,
                t(lang, "self_income"),
                reply_markup=self_income_kb(lang),
            )
            return

        if stage == "company_number_enter":
            db.update_case(conn, case["id"], company_number=text)
            set_stage(conn, case["id"], "company_need")
            bot.send_message(
                message.chat.id,
                t(lang, "company_need"),
                reply_markup=company_need_kb(lang),
            )
            return

        # Default: show menu
        bot.send_message(
            message.chat.id, t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
        )


@bot.message_handler(content_types=["document", "photo"])
def handle_document(message):
    bot.send_chat_action(message.chat.id, "typing")
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, message.from_user.id)
        lang = db.get_language(conn, message.from_user.id)
        case = db.get_active_case(conn, user_id)
        if not case:
            bot.send_message(
                message.chat.id, t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
            )
            return

        if case["awaiting_payment_proof"] == 1:
            file_id, file_unique_id = extract_file_ids(message)
            db.add_payment(
                conn,
                case["id"],
                method="unknown",
                status="proof_received",
                proof_file_id=file_id,
            )
            db.update_case(
                conn,
                case["id"],
                payment_status="proof_received",
                awaiting_payment_proof=0,
            )
            bot.send_message(
                message.chat.id,
                t(lang, "doc_received"),
                reply_markup=back_menu_kb(lang),
            )
            return

        if case["awaiting_doc_type"]:
            file_id, file_unique_id = extract_file_ids(message)
            db.add_document(
                conn, case["id"], case["awaiting_doc_type"], file_id, file_unique_id
            )
            db.update_case(conn, case["id"], awaiting_doc_type=None)
            bot.send_message(message.chat.id, t(lang, "doc_received"))
            show_doc_upload_menu(message.chat.id, conn, case, lang)
            return

        bot.send_message(
            message.chat.id, t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
        )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    with db.connect(DB_PATH) as conn:
        user_id = db.get_or_create_user(conn, call.from_user.id)
        lang = db.get_language(conn, call.from_user.id)
        data = call.data

        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            db.set_language(conn, call.from_user.id, lang_code)
            bot.edit_message_text(
                t(lang_code, "main_menu"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu_kb(lang_code),
            )
            return

        if data == "change_lang":
            bot.edit_message_text(
                t(lang, "welcome"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=lang_keyboard(),
            )
            return

        if data == "menu":
            db.set_chat_mode(conn, call.from_user.id, "menu")
            bot.edit_message_text(
                t(lang, "main_menu"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu_kb(lang),
            )
            return

        if data == "chat_ai":
            db.set_chat_mode(conn, call.from_user.id, "ai")
            bot.edit_message_text(
                t(lang, "chat_ai_intro"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=ai_chat_kb(lang),
            )
            return

        if data.startswith("service_"):
            service = data.split("_")[1]
            case = ensure_case(conn, user_id, service)
            if service == "student":
                set_stage(conn, case["id"], "student_intro")
                bot.edit_message_text(
                    t(lang, "student_intro")
                    + footer(lang, "footer_questions", "footer_2_3_min"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=start_back_kb(lang),
                )
                return
            if service == "paye":
                set_stage(conn, case["id"], "paye_intro")
                bot.edit_message_text(
                    t(lang, "paye_intro")
                    + footer(lang, "footer_eligibility", "footer_2_3_min"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=start_back_kb(lang),
                )
                return
            if service == "self":
                set_stage(conn, case["id"], "self_intro")
                bot.edit_message_text(
                    t(lang, "self_intro")
                    + footer(lang, "footer_questions", "footer_2_3_min"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=start_back_kb(lang),
                )
                return
            if service == "company":
                set_stage(conn, case["id"], "company_intro")
                bot.edit_message_text(
                    t(lang, "company_intro")
                    + footer(lang, "footer_questions", "footer_2_3_min"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=start_back_kb(lang),
                )
                return

        if data == "start_flow":
            case = db.get_active_case(conn, user_id)
            if not case:
                bot.edit_message_text(
                    t(lang, "main_menu"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=main_menu_kb(lang),
                )
                return
            if case["service"] == "student":
                set_stage(conn, case["id"], "student_nationality")
                bot.edit_message_text(
                    t(lang, "student_nationality"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=text_input_kb(lang),
                )
                return
            if case["service"] == "paye":
                set_stage(conn, case["id"], "paye_worked")
                bot.edit_message_text(
                    t(lang, "paye_worked"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=yes_no_kb(lang, "paye_yes", "paye_no"),
                )
                return
            if case["service"] == "self":
                set_stage(conn, case["id"], "self_registered")
                bot.edit_message_text(
                    t(lang, "self_registered"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self_registered_kb(lang),
                )
                return
            if case["service"] == "company":
                set_stage(conn, case["id"], "company_type")
                bot.edit_message_text(
                    t(lang, "company_type"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=company_type_kb(lang),
                )
                return

        # Student flow callbacks
        if data == "qa_yes":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], qa_partner=1)
            set_stage(conn, case["id"], "student_intake")
            bot.edit_message_text(
                t(lang, "student_intake"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=student_intake_kb(lang),
            )
            return

        if data == "qa_no":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], qa_partner=0)
            set_stage(conn, case["id"], "student_intake")
            bot.edit_message_text(
                t(lang, "student_intake"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=student_intake_kb(lang),
            )
            return

        if data == "intake_other":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "student_intake_other")
            bot.edit_message_text(
                t(lang, "student_intake"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data.startswith("intake_"):
            case = db.get_active_case(conn, user_id)
            intake = data.split("_")[1]
            db.update_case(conn, case["id"], intake=intake)
            set_stage(conn, case["id"], "student_level")
            bot.edit_message_text(
                t(lang, "student_level"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=student_level_kb(lang),
            )
            return

        if data == "level_other":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "student_level_other")
            bot.edit_message_text(
                t(lang, "student_level"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data.startswith("level_"):
            case = db.get_active_case(conn, user_id)
            level = data.split("_")[1]
            db.update_case(conn, case["id"], level=level)
            set_stage(conn, case["id"], "student_english")
            bot.edit_message_text(
                t(lang, "student_english"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=yes_no_kb(lang, "eng_yes", "eng_no"),
            )
            return

        if data == "eng_yes":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], english_test="yes")
            set_stage(conn, case["id"], "student_budget")
            bot.edit_message_text(
                t(lang, "student_budget"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=student_budget_kb(lang),
            )
            return

        if data == "eng_no":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], english_test="no")
            set_stage(conn, case["id"], "student_budget")
            bot.edit_message_text(
                t(lang, "student_budget"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=student_budget_kb(lang),
            )
            return

        if data == "budget_other":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "student_budget_other")
            bot.edit_message_text(
                t(lang, "student_budget"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data.startswith("budget_"):
            case = db.get_active_case(conn, user_id)
            budget = data.split("_")[1]
            db.update_case(conn, case["id"], budget=budget)
            send_student_summary(
                call.message.chat.id, conn, case["id"], lang, edit=call
            )
            return

        # PAYE flow callbacks
        if data == "paye_yes":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "paye_year")
            bot.edit_message_text(
                t(lang, "paye_year"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=paye_year_kb(lang),
            )
            return

        if data == "paye_no":
            bot.edit_message_text(
                t(lang, "paye_not_eligible"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=back_menu_kb(lang),
            )
            return

        if data == "paye_year_other":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "paye_year_other")
            bot.edit_message_text(
                t(lang, "paye_year"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data.startswith("paye_year_"):
            case = db.get_active_case(conn, user_id)
            tax_year = data.split("_", 2)[2]
            db.update_case(conn, case["id"], tax_year=tax_year)
            set_stage(conn, case["id"], "paye_employment")
            bot.edit_message_text(
                t(lang, "paye_employment"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=paye_employment_kb(lang),
            )
            return

        if data.startswith("paye_emp_"):
            case = db.get_active_case(conn, user_id)
            emp = data.split("_", 2)[2]
            db.update_case(conn, case["id"], employment_type=emp)
            set_stage(conn, case["id"], "paye_docs_available")
            bot.edit_message_text(
                t(lang, "paye_docs_available"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=paye_docs_available_kb(lang),
            )
            return

        if data.startswith("paye_dochave_"):
            case = db.get_active_case(conn, user_id)
            docs = data.split("_", 2)[2]
            db.update_case(conn, case["id"], docs_available=docs)
            set_stage(conn, case["id"], "paye_ni")
            bot.edit_message_text(
                t(lang, "paye_ni"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=paye_ni_kb(lang),
            )
            return

        if data == "paye_ni_yes":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "paye_ni_enter")
            bot.edit_message_text(
                t(lang, "paye_ni"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data == "paye_ni_no":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], ni_number=None)
            send_paye_summary(call.message.chat.id, conn, case["id"], lang, edit=call)
            return

        # Self-employed flow callbacks
        if data.startswith("self_reg_"):
            case = db.get_active_case(conn, user_id)
            value = data.split("_", 2)[2]
            db.update_case(conn, case["id"], self_employed_registered=value)
            set_stage(conn, case["id"], "self_year")
            bot.edit_message_text(
                t(lang, "self_year"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self_year_kb(lang),
            )
            return

        if data == "self_year_other":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "self_year_other")
            bot.edit_message_text(
                t(lang, "self_year"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data.startswith("self_year_"):
            case = db.get_active_case(conn, user_id)
            tax_year = data.split("_", 2)[2]
            db.update_case(conn, case["id"], tax_year=tax_year)
            set_stage(conn, case["id"], "self_income")
            bot.edit_message_text(
                t(lang, "self_income"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self_income_kb(lang),
            )
            return

        if data.startswith("self_income_"):
            case = db.get_active_case(conn, user_id)
            income = data.split("_", 2)[2]
            db.update_case(conn, case["id"], income_range=income)
            set_stage(conn, case["id"], "self_expenses")
            bot.edit_message_text(
                t(lang, "self_expenses"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self_expenses_kb(lang),
            )
            return

        if data.startswith("self_exp_"):
            case = db.get_active_case(conn, user_id)
            exp = data.split("_", 2)[2]
            db.update_case(conn, case["id"], expenses_records=exp)
            set_stage(conn, case["id"], "self_urgent")
            bot.edit_message_text(
                t(lang, "self_urgent"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self_urgent_kb(lang),
            )
            return

        if data.startswith("self_urgent_"):
            case = db.get_active_case(conn, user_id)
            urgent = data.split("_", 2)[2]
            db.update_case(
                conn,
                case["id"],
                urgent=urgent,
                priority="high" if urgent == "urgent" else None,
            )
            send_self_docs(call.message.chat.id, conn, case["id"], lang, edit=call)
            return

        # Company flow callbacks
        if data.startswith("company_type_"):
            case = db.get_active_case(conn, user_id)
            company_type = data.split("_", 2)[2]
            db.update_case(conn, case["id"], company_type=company_type)
            set_stage(conn, case["id"], "company_number")
            bot.edit_message_text(
                t(lang, "company_number"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=company_number_kb(lang),
            )
            return

        if data == "company_number_yes":
            case = db.get_active_case(conn, user_id)
            set_stage(conn, case["id"], "company_number_enter")
            bot.edit_message_text(
                t(lang, "company_number"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=text_input_kb(lang),
            )
            return

        if data == "company_number_no":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], company_number=None)
            set_stage(conn, case["id"], "company_need")
            bot.edit_message_text(
                t(lang, "company_need"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=company_need_kb(lang),
            )
            return

        if data.startswith("company_need_"):
            case = db.get_active_case(conn, user_id)
            need = data.split("_", 2)[2]
            db.update_case(conn, case["id"], company_need=need)
            set_stage(conn, case["id"], "company_activity")
            bot.edit_message_text(
                t(lang, "company_activity"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=company_activity_kb(lang),
            )
            return

        if data.startswith("company_activity_"):
            case = db.get_active_case(conn, user_id)
            activity = data.split("_", 2)[2]
            db.update_case(conn, case["id"], company_activity=activity)
            set_stage(conn, case["id"], "company_urgent")
            bot.edit_message_text(
                t(lang, "company_urgent"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=company_urgent_kb(lang),
            )
            return

        if data.startswith("company_urgent_"):
            case = db.get_active_case(conn, user_id)
            urgent = data.split("_", 2)[2]
            db.update_case(conn, case["id"], company_urgent=urgent)
            send_company_docs(call.message.chat.id, conn, case["id"], lang, edit=call)
            return

        # Common actions
        if data == "upload_now":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], status="waiting_documents")
            checklist = doc_checklist_text(lang, case["service"])
            bot.edit_message_text(
                checklist, call.message.chat.id, call.message.message_id
            )
            show_doc_upload_menu(call.message.chat.id, conn, case, lang)
            return

        if data == "upload_later":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], status="waiting_documents")
            schedule_doc_reminders(conn, case["id"])
            bot.edit_message_text(
                t(lang, "privacy"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=back_menu_kb(lang),
            )
            return

        if data.startswith("doc_"):
            case = db.get_active_case(conn, user_id)
            if data == "doc_missing":
                missing = db.get_missing_docs(conn, case["id"])
                awaiting = case["awaiting_doc_type"]
                if not awaiting:
                    bot.edit_message_text(
                        t(lang, "choose_doc_first"),
                        call.message.chat.id,
                        call.message.message_id,
                    )
                    show_doc_upload_menu(call.message.chat.id, conn, case, lang)
                    return
                if awaiting and awaiting not in missing:
                    missing.append(awaiting)
                db.set_missing_docs(conn, case["id"], missing)
                db.update_case(conn, case["id"], awaiting_doc_type=None)
                show_doc_upload_menu(call.message.chat.id, conn, case, lang, edit=call)
                return
            if data == "doc_back_list":
                db.update_case(conn, case["id"], awaiting_doc_type=None)
                show_doc_upload_menu(call.message.chat.id, conn, case, lang, edit=call)
                return
            if data == "doc_done":
                bot.edit_message_text(
                    t(lang, "payment_method"),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=payment_kb(lang),
                )
                return
            doc_name = data[4:]
            db.update_case(conn, case["id"], awaiting_doc_type=doc_name)
            bot.edit_message_text(
                t(lang, "send_doc", doc=doc_name),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=doc_wait_kb(lang),
            )
            return

        if data == "pay_online":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], payment_status="pending")
            db.add_payment(conn, case["id"], method="online", status="pending")
            ref = f"BW-{case['id']}-{call.from_user.first_name}"
            bot.edit_message_text(
                t(
                    lang,
                    "payment_instructions_online",
                    link="https://pay.example.com",
                    ref=ref,
                ),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=upload_payment_kb(lang),
            )
            schedule_payment_reminders(conn, case["id"])
            return

        if data == "pay_bank":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], payment_status="pending")
            db.add_payment(conn, case["id"], method="bank", status="pending")
            ref = f"BW-{case['id']}-{call.from_user.first_name}"
            bot.edit_message_text(
                t(
                    lang,
                    "payment_instructions_bank",
                    bank="HSBC / Sort code 00-00-00 / Acc 00000000",
                    ref=ref,
                ),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=upload_payment_kb(lang),
            )
            schedule_payment_reminders(conn, case["id"])
            return

        if data == "upload_payment":
            case = db.get_active_case(conn, user_id)
            db.update_case(conn, case["id"], awaiting_payment_proof=1)
            bot.edit_message_text(
                t(lang, "upload_payment_prompt"),
                call.message.chat.id,
                call.message.message_id,
            )
            return

        if data == "my_case":
            case = db.get_active_case(conn, user_id)
            missing = ", ".join(db.get_missing_docs(conn, case["id"])) or "-"
            service_name = (
                t(lang, "service_" + case["service"])
                if case["service"] in ("student", "paye", "self", "company")
                else case["service"]
            )
            text = t(
                lang,
                "my_case",
                service=service_name,
                status=case["status"],
                payment=case["payment_status"],
                missing=missing,
            )
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=back_menu_kb(lang),
            )
            return


def student_intake_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🌸 " + t(lang, "intake_mar_apr"), callback_data="intake_march_april"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🍂 " + t(lang, "intake_sep"), callback_data="intake_september"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📝 " + t(lang, "other"), callback_data="intake_other"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def student_level_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📚 Foundation", callback_data="level_foundation")
    )
    kb.add(types.InlineKeyboardButton("🎓 Bachelor’s", callback_data="level_bachelors"))
    kb.add(types.InlineKeyboardButton("🎓 Master's", callback_data="level_masters"))
    kb.add(
        types.InlineKeyboardButton(
            "🗣️ English course / Pre-sessional", callback_data="level_english"
        )
    )
    kb.add(types.InlineKeyboardButton("📝 Other", callback_data="level_other"))
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def student_budget_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💰 Under £10k", callback_data="budget_under10"))
    kb.add(types.InlineKeyboardButton("💰 £10k–£15k", callback_data="budget_10_15"))
    kb.add(types.InlineKeyboardButton("💰 £15k–£20k", callback_data="budget_15_20"))
    kb.add(types.InlineKeyboardButton("💰 £20k+", callback_data="budget_20_plus"))
    kb.add(
        types.InlineKeyboardButton("🤐 Prefer not to say", callback_data="budget_no")
    )
    kb.add(types.InlineKeyboardButton("📝 Other", callback_data="budget_other"))
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def paye_year_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("2025/26", callback_data="paye_year_2025_26"))
    kb.add(types.InlineKeyboardButton("2024/25", callback_data="paye_year_2024_25"))
    kb.add(types.InlineKeyboardButton("2023/24", callback_data="paye_year_2023_24"))
    kb.add(
        types.InlineKeyboardButton(
            "📅 " + t(lang, "paye_year_older"), callback_data="paye_year_other"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def paye_employment_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "👤 " + t(lang, "paye_emp_one"), callback_data="paye_emp_one"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "👥 " + t(lang, "paye_emp_multi"), callback_data="paye_emp_multi"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🏢 " + t(lang, "paye_emp_agency"), callback_data="paye_emp_agency"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="paye_emp_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def paye_docs_available_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📄 P60", callback_data="paye_dochave_p60"))
    kb.add(types.InlineKeyboardButton("📄 P45", callback_data="paye_dochave_p45"))
    kb.add(
        types.InlineKeyboardButton("📋 Payslips", callback_data="paye_dochave_payslips")
    )
    kb.add(
        types.InlineKeyboardButton("✉️ HMRC letters", callback_data="paye_dochave_hmrc")
    )
    kb.add(types.InlineKeyboardButton("➖ None", callback_data="paye_dochave_none"))
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def paye_ni_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "✅ " + t(lang, "paye_ni_yes"), callback_data="paye_ni_yes"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❌ " + t(lang, "paye_ni_no"), callback_data="paye_ni_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def self_registered_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ " + t(lang, "yes"), callback_data="self_reg_yes")
    )
    kb.add(
        types.InlineKeyboardButton(
            "❌ " + t(lang, "no_not_sure").split(" / ")[0], callback_data="self_reg_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="self_reg_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def self_year_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📅 2024/25", callback_data="self_year_2024_25"))
    kb.add(types.InlineKeyboardButton("📅 2023/24", callback_data="self_year_2023_24"))
    kb.add(
        types.InlineKeyboardButton(
            "📝 " + t(lang, "other"), callback_data="self_year_other"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def self_income_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("💰 Under £10k", callback_data="self_income_under10")
    )
    kb.add(
        types.InlineKeyboardButton("💰 £10k–£30k", callback_data="self_income_10_30")
    )
    kb.add(
        types.InlineKeyboardButton("💰 £30k–£60k", callback_data="self_income_30_60")
    )
    kb.add(types.InlineKeyboardButton("💰 £60k+", callback_data="self_income_60_plus"))
    kb.add(
        types.InlineKeyboardButton(
            "🤐 Prefer not to say", callback_data="self_income_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def self_expenses_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ " + t(lang, "yes"), callback_data="self_exp_yes")
    )
    kb.add(
        types.InlineKeyboardButton(
            "❌ " + t(lang, "no_not_sure").split(" / ")[0], callback_data="self_exp_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="self_exp_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def self_urgent_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🚨 " + t(lang, "self_urgent_urgent"), callback_data="self_urgent_urgent"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "✅ " + t(lang, "self_urgent_normal"), callback_data="self_urgent_normal"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="self_urgent_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def company_type_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🏢 " + t(lang, "company_type_ltd"), callback_data="company_type_ltd"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "👤 " + t(lang, "company_type_sole"), callback_data="company_type_sole"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📝 " + t(lang, "company_type_unreg"),
            callback_data="company_type_unregistered",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def company_number_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "✅ " + t(lang, "company_number_yes"), callback_data="company_number_yes"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❌ " + t(lang, "company_number_no"), callback_data="company_number_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def company_need_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📊 Annual accounts + Corporation tax",
            callback_data="company_need_accounts",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📒 Bookkeeping support", callback_data="company_need_bookkeeping"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "👥 Payroll / PAYE", callback_data="company_need_payroll"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📦 VAT registration/returns", callback_data="company_need_vat"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "👤 Director Self Assessment", callback_data="company_need_director"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📅 Ongoing monthly accounting", callback_data="company_need_monthly"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def company_activity_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🔵 " + t(lang, "company_activity_small"),
            callback_data="company_activity_small",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🟡 " + t(lang, "company_activity_medium"),
            callback_data="company_activity_medium",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "🔴 " + t(lang, "company_activity_busy"),
            callback_data="company_activity_busy",
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="company_activity_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def company_urgent_kb(lang: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "🚨 " + t(lang, "company_urgent_yes"), callback_data="company_urgent_yes"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "✅ " + t(lang, "company_urgent_no"), callback_data="company_urgent_no"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "❓ " + t(lang, "not_sure"), callback_data="company_urgent_not_sure"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    return kb


def extract_file_ids(message):
    if message.document:
        return message.document.file_id, message.document.file_unique_id
    if message.photo:
        photo = message.photo[-1]
        return photo.file_id, photo.file_unique_id
    return None, None


def send_student_summary(chat_id, conn, case_id, lang, edit=None):
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    text = (
        t(
            lang,
            "student_summary",
            applying_from=case["applying_from"] or "-",
            level=case["level"] or "-",
            intake=case["intake"] or "-",
        )
        + "\n\n"
        + t(lang, "visa_note")
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📄 " + t(lang, "upload_docs_btn"), callback_data="upload_now"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    if edit:
        bot.edit_message_text(
            text, edit.message.chat.id, edit.message.message_id, reply_markup=kb
        )
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def send_paye_summary(chat_id, conn, case_id, lang, edit=None):
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    text = t(lang, "paye_summary") + "\n\n" + t(lang, "tax_note")
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📄 " + t(lang, "upload_docs_btn"), callback_data="upload_now"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
        )
    )
    kb.add(
        types.InlineKeyboardButton("🔙 " + t(lang, "back_menu"), callback_data="menu")
    )
    if edit:
        bot.edit_message_text(
            text, edit.message.chat.id, edit.message.message_id, reply_markup=kb
        )
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def send_self_docs(chat_id, conn, case_id, lang, edit=None):
    text = t(lang, "self_docs") + "\n\n" + t(lang, "tax_note")
    if edit:
        bot.edit_message_text(
            text,
            edit.message.chat.id,
            edit.message.message_id,
            reply_markup=upload_choice_kb(lang),
        )
    else:
        bot.send_message(chat_id, text, reply_markup=upload_choice_kb(lang))


def send_company_docs(chat_id, conn, case_id, lang, edit=None):
    text = t(lang, "company_docs")
    if edit:
        bot.edit_message_text(
            text,
            edit.message.chat.id,
            edit.message.message_id,
            reply_markup=upload_choice_kb(lang),
        )
    else:
        bot.send_message(chat_id, text, reply_markup=upload_choice_kb(lang))


def show_doc_upload_menu(chat_id, conn, case, lang, edit=None):
    docs = doc_list_for_service(case["service"])
    text = t(lang, "doc_upload_mode")
    kb = document_select_kb(lang, docs)
    if edit:
        bot.edit_message_text(
            text, edit.message.chat.id, edit.message.message_id, reply_markup=kb
        )
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


def schedule_doc_reminders(conn, case_id):
    now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET_HOURS)
    for hours in [6, 24, 72]:
        due = (now + timedelta(hours=hours)).isoformat()
        db.add_reminder(conn, case_id, "doc", due)


def schedule_payment_reminders(conn, case_id):
    now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET_HOURS)
    for hours in [6, 24]:
        due = (now + timedelta(hours=hours)).isoformat()
        db.add_reminder(conn, case_id, "payment", due)


def reminder_worker():
    while True:
        with db.connect(DB_PATH) as conn:
            now = datetime.utcnow().isoformat()
            for reminder in db.due_reminders(conn, now):
                case = conn.execute(
                    "SELECT cases.*, users.tg_id FROM cases JOIN users ON users.id = cases.user_id WHERE cases.id = ?",
                    (reminder["case_id"],),
                ).fetchone()
                if not case:
                    db.mark_reminder_sent(conn, reminder["id"])
                    continue
                lang = db.get_language(conn, case["tg_id"])
                if reminder["type"] == "doc":
                    text = t(lang, "reminder_doc")
                else:
                    text = t(lang, "reminder_payment")
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton(
                        "📄 " + t(lang, "upload_docs_btn"), callback_data="upload_now"
                    )
                )
                kb.add(
                    types.InlineKeyboardButton(
                        "📤 " + t(lang, "upload_payment_btn"),
                        callback_data="upload_payment",
                    )
                )
                kb.add(
                    types.InlineKeyboardButton(
                        "📞 " + t(lang, "talk_moderator"), callback_data="chat_ai"
                    )
                )
                bot.send_message(case["tg_id"], text, reply_markup=kb)
                db.mark_reminder_sent(conn, reminder["id"])
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=reminder_worker, daemon=True).start()
    bot.infinity_polling()
