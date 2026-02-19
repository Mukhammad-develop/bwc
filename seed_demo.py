"""
Demo seed script — populates bot.db with sample users, chats, documents, and admins.
Run from project root:  python seed_demo.py
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).parent / "tg_bot" / "bot.db"

def ts(days_ago=0, hours_ago=0, minutes_ago=0):
    dt = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
    return dt.isoformat()

def connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# ─── SAMPLE CONVERSATIONS ─────────────────────────────────────────

CONV_STUDENT = [
    {"role": "assistant", "content": "Assalomu alaykum, Amir! 👋 UK student visa bo'yicha hammasini birga tayyorlab chiqamiz. Hozir qaysi davlatdan topshirmoqchisiz?", "timestamp": ts(5, 3, 0)},
    {"role": "user",      "content": "Salom, men hozir Toshkentdaman.", "timestamp": ts(5, 2, 58)},
    {"role": "assistant", "content": "Zo'r. Qaysi universitet va qaysi yo'nalishga qabul oldingiz?", "timestamp": ts(5, 2, 55)},
    {"role": "user",      "content": "University of Manchester, MSc Computer Science, 2026-yil sentabr intake.", "timestamp": ts(5, 2, 50)},
    {"role": "assistant", "content": "Ajoyib tanlov! 🎯 CAS xatingiz chiqib bo'ldimi yoki hali kutyapsizmi?", "timestamp": ts(5, 2, 47)},
    {"role": "user",      "content": "Hali chiqmagan, iyun oyida bo'ladi deyishdi.", "timestamp": ts(5, 2, 40)},
    {"role": "assistant", "content": "Ha, bu odatiy holat. CAS chiqishini kutayotgan paytda qolgan hujjatlarni tayyorlab olamiz.\n\nQisqa tekshiruv:\n- Passport amal qiladimi?\n- IELTS/ingliz tili natijasi bormi?\n- O'qish va yashash uchun mablag' tayyormi?", "timestamp": ts(5, 2, 35)},
    {"role": "user",      "content": "Passport 2031-gacha amal qiladi, IELTS 7.0 bor, ota-onam homiylik qiladi va hisobda taxminan £35,000 bor.", "timestamp": ts(5, 2, 28)},
    {"role": "assistant", "content": "Juda yaxshi, profil kuchli ✅\n\nAvval passportni yuboring, keyin IELTS va moliyaviy hujjatlarni qo'shamiz.", "timestamp": ts(5, 2, 20)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000001_00:passport_amir_karimov.pdf:document]", "timestamp": ts(5, 2, 10)},
    {"role": "assistant", "content": "Passport qabul qilindi 👍\n\nCAS chiqqach quyidagilar bilan topshiramiz:\n- Passport\n- CAS xati\n- IELTS sertifikati\n- 28 kunlik bank statement\n- Homiylik xati + qarindoshlik isboti", "timestamp": ts(5, 2, 5)},
    {"role": "user",      "content": "Sentabr intake uchun qachon topshirgan yaxshi?", "timestamp": ts(5, 1, 50)},
    {"role": "assistant", "content": "Eng yaxshi muddat may-iyun oralig'i. Eng erta martdan bo'ladi, lekin odatda CAS sabab may-iyun qulay.\n\nShunda UKVI qo'shimcha so'rasa ham vaqt yetadi.", "timestamp": ts(5, 1, 45)},
    {"role": "user",      "content": "Tushunarli. Xizmat narxi qancha?", "timestamp": ts(5, 1, 40)},
    {"role": "assistant", "content": "Student visa paketi **£299**: hujjat tekshiruvi, forma bo'yicha yordam va natijagacha kuzatuv.\n\nXohlasangiz hozir case'ni lock qilib, to'lovdan keyin konsultantga o'tkazaman.", "timestamp": ts(5, 1, 35)},
    {"role": "user",      "content": "Mayli, ota-onam bilan gaplashib to'lovni tasdiqlayman.", "timestamp": ts(5, 1, 30)},
    {"role": "assistant", "content": "Zo'r, bemalol. Case saqlab qo'yildi, tayyor bo'lganingizda davom etamiz 🙌", "timestamp": ts(5, 1, 25)},
]

CONV_PAYE = [
    {"role": "assistant", "content": "Hi Sarah 👋 let's sort your PAYE refund. Which years do you want to claim for?", "timestamp": ts(3, 5, 0)},
    {"role": "user",      "content": "Last 3 years if possible.", "timestamp": ts(3, 4, 55)},
    {"role": "assistant", "content": "Yep, that's doable. HMRC allows up to 4 years back. Did you have one job or multiple jobs in any of those years?", "timestamp": ts(3, 4, 50)},
    {"role": "user",      "content": "Mostly one job, but during COVID I had two jobs for around 6 months.", "timestamp": ts(3, 4, 44)},
    {"role": "assistant", "content": "That often leads to overpaid tax, so good chance of refund. Can you share your NI number and upload your P60s?", "timestamp": ts(3, 4, 38)},
    {"role": "user",      "content": "NI: AB 12 34 56 C", "timestamp": ts(3, 4, 30)},
    {"role": "assistant", "content": "Thanks, got it ✅", "timestamp": ts(3, 4, 25)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000002_00:P60_2022-23_Sarah.pdf:document]", "timestamp": ts(3, 4, 15)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000002_01:P60_2023-24_Sarah.pdf:document]", "timestamp": ts(3, 4, 14)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000002_02:P60_2024-25_Sarah.pdf:document]", "timestamp": ts(3, 4, 13)},
    {"role": "assistant", "content": "Perfect, all three P60s received.\n\nQuick estimate from these:\n- 2022-23: possible refund around £380\n- 2023-24: likely bigger due to two jobs\n- 2024-25: still reviewing", "timestamp": ts(3, 4, 5)},
    {"role": "user",      "content": "Nice. Roughly how much in total?", "timestamp": ts(3, 3, 55)},
    {"role": "assistant", "content": "Likely **£1,200 to £1,500** overall. Final number depends on HMRC calculation and any P45 info from your second job.", "timestamp": ts(3, 3, 50)},
    {"role": "user",      "content": "Great, proceed please. Sort code 20-45-67, account 12345678.", "timestamp": ts(3, 3, 40)},
    {"role": "assistant", "content": "Done ✅ I've registered your claim.\n\n- **Name:** Sarah Johnson\n- **NI:** AB 123456C\n- **Years:** 2022-23, 2023-24, 2024-25\n- **Estimate:** £1,200–£1,500\n- **Fee:** 15% of refund\n\nA consultant will submit within 2 business days.", "timestamp": ts(3, 3, 30)},
    {"role": "user",      "content": "Amazing, thank you!", "timestamp": ts(3, 3, 25)},
]

CONV_SELF = [
    {"role": "assistant", "content": "Hi Dmitry, happy to help with your Self Assessment. Which tax year are we filing?", "timestamp": ts(7, 1, 0)},
    {"role": "user",      "content": "2023-24. I'm a freelancer.", "timestamp": ts(7, 0, 55)},
    {"role": "assistant", "content": "Great. Are you already registered with HMRC and do you have your UTR?", "timestamp": ts(7, 0, 50)},
    {"role": "user",      "content": "Yes. UTR is 1234567890.", "timestamp": ts(7, 0, 45)},
    {"role": "assistant", "content": "Perfect. What's your total income for that year?", "timestamp": ts(7, 0, 40)},
    {"role": "user",      "content": "£67,500 from IT contracting.", "timestamp": ts(7, 0, 35)},
    {"role": "assistant", "content": "Thanks. Rough estimate before expenses is around **£17.8k** tax+NI. With proper expense claims, you could save several thousand.\n\nPlease upload invoices first.", "timestamp": ts(7, 0, 28)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000003_00:freelance_invoices_2023-24.pdf:document]", "timestamp": ts(7, 0, 20)},
    {"role": "assistant", "content": "Received ✅ Also, did you make payments on account already?", "timestamp": ts(7, 0, 10)},
    {"role": "user",      "content": "Yes, two payments of £6,500.", "timestamp": ts(6, 23, 50)},
    {"role": "assistant", "content": "Nice, that helps a lot. After those payments, your balancing payment could be roughly **£2.2k** depending on final expenses.\n\nNow send your receipts so we can optimize deductions.", "timestamp": ts(6, 23, 40)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000003_01:expense_receipts.pdf:document]", "timestamp": ts(6, 23, 30)},
    {"role": "assistant", "content": "Got the receipts ✅ Quick review already shows good deductible costs (equipment + software + comms).\n\nFor your case this is a **standard return (£149)**. Want me to open payment?", "timestamp": ts(6, 23, 20)},
    {"role": "user",      "content": "Yes please. How can I pay?", "timestamp": ts(6, 23, 15)},
    {"role": "assistant", "content": "You can do bank transfer or card link.\n\n- **Bank:** 12-34-56 / 87654321\n- **Reference:** your Telegram ID\n\nOnce paid, your assigned accountant finalizes and submits before deadline.", "timestamp": ts(6, 23, 10)},
]

CONV_COMPANY = [
    {"role": "assistant", "content": "Hi Elena, happy to help with company accounts. Can I confirm company name + number?", "timestamp": ts(1, 4, 0)},
    {"role": "user",      "content": "Zara Ltd, company number 14567890.", "timestamp": ts(1, 3, 55)},
    {"role": "assistant", "content": "Thanks. First filing, right? What's your year end and approximate revenue?", "timestamp": ts(1, 3, 48)},
    {"role": "user",      "content": "Yes first filing. Year end 31 March, revenue around £120,000.", "timestamp": ts(1, 3, 40)},
    {"role": "assistant", "content": "Understood. At that level, we should also check VAT registration timing.\n\nCan you upload your bank statements + bookkeeping file first?", "timestamp": ts(1, 3, 30)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000004_00:ZaraLtd_bank_statements_2023-24.pdf:document]", "timestamp": ts(1, 3, 22)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000004_01:ZaraLtd_accounts_spreadsheet.xlsx:document]", "timestamp": ts(1, 3, 20)},
    {"role": "assistant", "content": "Got both files ✅ thank you.\n\nA couple quick checks:\n1) Any dividends paid?\n2) Any major equipment purchases?\n3) Director-paid business expenses?", "timestamp": ts(1, 3, 10)},
    {"role": "user",      "content": "Yes. Dividends £30k each for 2 directors. Bought MacBook Pro £2,499. Director expenses around £3,200.", "timestamp": ts(1, 3, 0)},
    {"role": "assistant", "content": "Great detail. That helps a lot.\n\n- Dividends are fine if post-tax profits support them\n- MacBook can usually be claimed via capital allowance\n- We'll separate deductible travel vs non-deductible client entertainment", "timestamp": ts(1, 2, 45)},
    {"role": "user",      "content": "We're not VAT registered yet.", "timestamp": ts(1, 2, 35)},
    {"role": "assistant", "content": "Given £120k revenue, you should register for VAT now to avoid issues. We'll include that in your onboarding.\n\nPackage for your case is **£799** (accounts + CT600 + director support + VAT guidance).", "timestamp": ts(1, 2, 20)},
    {"role": "user",      "content": "Okay, let's go ahead.", "timestamp": ts(1, 2, 10)},
    {"role": "assistant", "content": "Perfect, I've opened your case ✅\n\n- **Company:** Zara Ltd (14567890)\n- **Director:** Elena Volkov\n- **Year end:** 31 March 2024\n- **Revenue:** ~£120,000\n- **Service bundle:** Accounts + CT600 + VAT setup\n- **Fee:** £799\n\nPlease pay to 12-34-56 / 87654321 with reference **ZARA-LTD**. Your consultant will follow up within 48 hours.", "timestamp": ts(1, 2, 0)},
]

CONV_STUDENT_RU = [
    {"role": "assistant", "content": "Камилла, здравствуйте! Давайте спокойно подготовим вашу студенческую визу в UK. Вы сейчас в Узбекистане?", "timestamp": ts(10, 2, 0)},
    {"role": "user",      "content": "Да, в Ташкенте.", "timestamp": ts(10, 1, 55)},
    {"role": "assistant", "content": "Отлично. В какой вуз поступили и на какую программу?", "timestamp": ts(10, 1, 50)},
    {"role": "user",      "content": "UCL, международные отношения, магистратура. Старт в сентябре 2026.", "timestamp": ts(10, 1, 45)},
    {"role": "assistant", "content": "Супер выбор 👏 CAS уже есть или ещё ждёте?", "timestamp": ts(10, 1, 40)},
    {"role": "user",      "content": "Пока жду, обещали в июне.", "timestamp": ts(10, 1, 35)},
    {"role": "assistant", "content": "Нормально, по срокам всё ок. Пока соберём базовые документы.\n\nНужно:\n- загранпаспорт\n- IELTS\n- подтверждение средств\n- академические документы", "timestamp": ts(10, 1, 28)},
    {"role": "user",      "content": "IELTS 7.5, диплом с отличием.", "timestamp": ts(10, 1, 20)},
    {"role": "assistant", "content": "Отлично, профиль очень сильный. Тогда отправьте, пожалуйста, паспорт и IELTS, чтобы мы сразу проверили качество сканов.", "timestamp": ts(10, 1, 15)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000005_00:pasport_kamilya.jpg:photo]", "timestamp": ts(10, 1, 10)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000005_01:IELTS_certificate_7.5.pdf:document]", "timestamp": ts(10, 1, 9)},
    {"role": "assistant", "content": "Получили ✅ Оба файла читаются хорошо.\n\nДальше ждём CAS, и можно выходить на подачу. По нашей стороне пакет сопровождения **£299**.", "timestamp": ts(10, 1, 0)},
    {"role": "user",      "content": "Отлично, спасибо! Продолжаем с вами.", "timestamp": ts(10, 0, 50)},
]

CONV_PAYE_UKRAINIAN = [
    {"role": "assistant", "content": "Hi Olena, thanks for reaching out. I can help check if you overpaid PAYE tax. Which tax years should we review?", "timestamp": ts(2, 4, 0)},
    {"role": "user",      "content": "2022-23 and 2023-24 please. I changed jobs in 2023.", "timestamp": ts(2, 3, 55)},
    {"role": "assistant", "content": "Great, job change is often where refunds happen. Please share your NI number and upload both P60s (and P45 if you have it).", "timestamp": ts(2, 3, 50)},
    {"role": "user",      "content": "NI is JK 45 67 89 D. Uploading now.", "timestamp": ts(2, 3, 45)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000006_00:Olena_P60_2022-23.pdf:document]", "timestamp": ts(2, 3, 40)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000006_01:Olena_P60_2023-24.pdf:document]", "timestamp": ts(2, 3, 39)},
    {"role": "assistant", "content": "Received, thank you ✅\n\nInitial estimate looks like around **£640-£900** refund, mainly from tax code mismatch during your employer switch.\n\nIf you send P45, I can tighten this estimate before submission.", "timestamp": ts(2, 3, 30)},
    {"role": "user",      "content": "I can't find P45 right now, can we proceed anyway?", "timestamp": ts(2, 3, 20)},
    {"role": "assistant", "content": "Yes, we can proceed now and attach P45 later if needed. I'll mark your case as active and send it to consultant review.", "timestamp": ts(2, 3, 15)},
]

CONV_SELF_DELIVEROO = [
    {"role": "assistant", "content": "Hi Jamshid 👋 I can help with your self-employed tax return. Which year are you filing?", "timestamp": ts(4, 6, 0)},
    {"role": "user",      "content": "2023-24. I worked for Deliveroo and sometimes Uber Eats.", "timestamp": ts(4, 5, 55)},
    {"role": "assistant", "content": "Understood. Do you have a UTR already?", "timestamp": ts(4, 5, 52)},
    {"role": "user",      "content": "Yes, UTR 9876543210.", "timestamp": ts(4, 5, 50)},
    {"role": "assistant", "content": "Perfect. Please upload your income summary and any expense receipts (bike repairs, phone, thermal bag, fuel/travel).", "timestamp": ts(4, 5, 45)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000007_00:Deliveroo_annual_summary.pdf:document]", "timestamp": ts(4, 5, 38)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000007_01:Courier_expenses_photos.zip:document]", "timestamp": ts(4, 5, 37)},
    {"role": "assistant", "content": "Got both files ✅\n\nQuick rough view:\n- Income around £31,200\n- Trackable expenses appear around £4,000-£5,200\n\nThat should reduce your taxable profit nicely. Our standard filing fee is **£149**.", "timestamp": ts(4, 5, 30)},
    {"role": "user",      "content": "Good. Can I pay next week?", "timestamp": ts(4, 5, 20)},
    {"role": "assistant", "content": "Absolutely. I'll keep your case open and add a reminder for next week.", "timestamp": ts(4, 5, 15)},
]

CONV_COMPANY_ECOM = [
    {"role": "assistant", "content": "Hello Marcus, I can help with your company accounts. What's your company name and current issue?", "timestamp": ts(6, 2, 0)},
    {"role": "user",      "content": "Nexa Commerce Ltd. We missed deadlines and got penalty letters.", "timestamp": ts(6, 1, 55)},
    {"role": "assistant", "content": "Thanks for sharing. We handle late filing recovery often. Please upload the penalty letters and your latest bookkeeping export.", "timestamp": ts(6, 1, 50)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000008_00:CompaniesHouse_penalty_letter.pdf:document]", "timestamp": ts(6, 1, 47)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000008_01:Nexa_Xero_export_Q1-Q4.xlsx:document]", "timestamp": ts(6, 1, 46)},
    {"role": "assistant", "content": "Received ✅\n\nPlan from our side:\n1) File overdue accounts first\n2) Submit CT600\n3) Draft penalty mitigation letter\n\nWe'll likely need director ID and UTR next.", "timestamp": ts(6, 1, 40)},
    {"role": "user",      "content": "Okay, send me the total fee first.", "timestamp": ts(6, 1, 30)},
    {"role": "assistant", "content": "For a late-filing recovery case like this: **£1,150** fixed. Includes Companies House filing, CT return, and one mitigation attempt.", "timestamp": ts(6, 1, 25)},
    {"role": "user",      "content": "Understood. I'll confirm internally tomorrow.", "timestamp": ts(6, 1, 20)},
]

CONV_STUDENT_UZ_FAMILY = [
    {"role": "assistant", "content": "Assalomu alaykum, Madina! Student visa bo'yicha yordam beraman. Qaysi universitetga kirgansiz?", "timestamp": ts(1, 7, 0)},
    {"role": "user",      "content": "Salom. Leeds universitetiga Foundation year uchun offer oldim.", "timestamp": ts(1, 6, 55)},
    {"role": "assistant", "content": "Tabriklayman 🎉 CAS hali chiqmadimi?", "timestamp": ts(1, 6, 52)},
    {"role": "user",      "content": "Yo'q, hali yo'q. Lekin men bilan 8 yoshli farzandim ham borishi mumkinmi?", "timestamp": ts(1, 6, 50)},
    {"role": "assistant", "content": "Foundation/undergraduate bosqichida odatda dependent olib borish cheklangan. Bu joyini aniq tekshirib beramiz, chunki kurs turi va sponsor litsenziyasiga bog'liq.", "timestamp": ts(1, 6, 45)},
    {"role": "user",      "content": "Tushunarli. Passportimni yuboraman.", "timestamp": ts(1, 6, 40)},
    {"role": "user",      "content": "[FILE:DEMO_UNIQUE_100000009_00:madina_passport.pdf:document]", "timestamp": ts(1, 6, 39)},
    {"role": "assistant", "content": "Oldim ✅\n\nKeyingi qadamlar:\n- CAS chiqishini kutamiz\n- Moliyaviy hujjatlarni tayyorlaymiz\n- Dependent eligibility'ni yozma tekshirib beramiz", "timestamp": ts(1, 6, 33)},
    {"role": "user",      "content": "Rahmat, iltimos dependent masalasini birinchi tekshirib bering.", "timestamp": ts(1, 6, 28)},
    {"role": "assistant", "content": "Albatta. Bugun ichida consultantdan javob olib case ichiga qoldiraman.", "timestamp": ts(1, 6, 25)},
]

USERS = [
    {
        "tg_id": 100000001,
        "language": "uz",
        "created_at": ts(10),
        "service": "student",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_STUDENT,
        "docs": [
            {"doc_type": "passport", "filename": "passport_amir_karimov.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Amir Karimov",
            "nationality": "Uzbek",
            "country_of_residence": "Uzbekistan",
            "phone": "+998 90 123 4567",
            "email": "amir.karimov@gmail.com",
            "age": "24",
            "service_interest": "UK Student Visa — MSc Computer Science, University of Manchester",
            "uk_visa_status": "None — applying",
            "employment_type": "Student",
            "budget": "£299 consulting fee + £27,750 tuition",
            "urgency": "Application by June 2026",
            "notes": "IELTS 7.0, passport valid 2031. Parental sponsorship £35,000. Awaiting CAS from Manchester."
        }
    },
    {
        "tg_id": 100000002,
        "language": "en",
        "created_at": ts(5),
        "service": "paye",
        "status": "active",
        "payment_status": "received",
        "conversation": CONV_PAYE,
        "docs": [
            {"doc_type": "p60_2022", "filename": "P60_2022-23_Sarah.pdf", "media_type": "document"},
            {"doc_type": "p60_2023", "filename": "P60_2023-24_Sarah.pdf", "media_type": "document"},
            {"doc_type": "p60_2024", "filename": "P60_2024-25_Sarah.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Sarah Johnson",
            "nationality": "British",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7700 900123",
            "email": "sarah.j@hotmail.co.uk",
            "age": "31",
            "service_interest": "PAYE Tax Refund — 3 tax years",
            "uk_visa_status": "British Citizen",
            "employment_type": "Employed (retail) — previously 2 jobs simultaneously",
            "budget": "15% of refund (~£180–225)",
            "urgency": "ASAP — wants refund",
            "notes": "NI: AB 123456C. Two jobs during COVID causing likely overtaxation. Estimated refund £1,200–£1,500. Bank: Sort 20-45-67, Acc 12345678."
        }
    },
    {
        "tg_id": 100000003,
        "language": "en",
        "created_at": ts(8),
        "service": "self",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_SELF,
        "docs": [
            {"doc_type": "invoices", "filename": "freelance_invoices_2023-24.pdf", "media_type": "document"},
            {"doc_type": "receipts", "filename": "expense_receipts.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Dmitry Petrov",
            "nationality": "Russian",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7711 223344",
            "email": "dmitry.petrov.dev@gmail.com",
            "age": "34",
            "service_interest": "Self-Employed Tax Return 2023-24",
            "uk_visa_status": "Skilled Worker Visa",
            "employment_type": "IT Freelancer / Sole Trader",
            "budget": "£149 standard self-assessment fee",
            "urgency": "Deadline: 31 Jan 2025 — urgent",
            "notes": "UTR: 1234567890. Income: £67,500. Payments on account £13,000 already made. Estimated balancing payment ~£2,200."
        }
    },
    {
        "tg_id": 100000004,
        "language": "en",
        "created_at": ts(2),
        "service": "company",
        "status": "active",
        "payment_status": "received",
        "conversation": CONV_COMPANY,
        "docs": [
            {"doc_type": "bank_statements", "filename": "ZaraLtd_bank_statements_2023-24.pdf", "media_type": "document"},
            {"doc_type": "spreadsheet", "filename": "ZaraLtd_accounts_spreadsheet.xlsx", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Elena Volkov",
            "nationality": "Russian",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7890 112233",
            "email": "elena@zaraltd.co.uk",
            "age": "38",
            "service_interest": "Company Accounts + CT600 + VAT Registration — Zara Ltd",
            "uk_visa_status": "Indefinite Leave to Remain",
            "employment_type": "Company Director — Zara Ltd (marketing consultancy)",
            "budget": "£799 full package",
            "urgency": "Urgent — CT payment deadline Dec 2024",
            "notes": "Company no. 14567890. Revenue £120k, 2 directors, first filing. VAT registration needed. Dividends £30k each."
        }
    },
    {
        "tg_id": 100000005,
        "language": "ru",
        "created_at": ts(12),
        "service": "student",
        "status": "completed",
        "payment_status": "received",
        "conversation": CONV_STUDENT_RU,
        "docs": [
            {"doc_type": "passport", "filename": "pasport_kamilya.jpg", "media_type": "photo"},
            {"doc_type": "ielts", "filename": "IELTS_certificate_7.5.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Камилла Исмоилова",
            "nationality": "Узбекистан",
            "country_of_residence": "Узбекистан",
            "phone": "+998 91 987 6543",
            "email": "kamilya.i@mail.ru",
            "age": "23",
            "service_interest": "Студенческая виза UK — MA International Relations, UCL",
            "uk_visa_status": "Нет — подаёт впервые",
            "employment_type": "Студент",
            "budget": "£299 + £23,000 обучение",
            "urgency": "Подача в июне 2026",
            "notes": "IELTS 7.5. Стипендия UCL £5000. Спонсорство родителей £40,000. Документы загружены."
        }
    },
    {
        "tg_id": 100000006,
        "language": "en",
        "created_at": ts(3),
        "service": "paye",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_PAYE_UKRAINIAN,
        "docs": [
            {"doc_type": "p60_2022", "filename": "Olena_P60_2022-23.pdf", "media_type": "document"},
            {"doc_type": "p60_2023", "filename": "Olena_P60_2023-24.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Olena Marchenko",
            "nationality": "Ukrainian",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7458 203911",
            "email": "olena.marchenko@gmail.com",
            "age": "29",
            "service_interest": "PAYE refund after job change",
            "uk_visa_status": "Homes for Ukraine",
            "employment_type": "Employed",
            "budget": "15% of refund",
            "urgency": "Medium",
            "notes": "Likely tax code mismatch in 2023 employer transition. Awaiting P45."
        }
    },
    {
        "tg_id": 100000007,
        "language": "uz",
        "created_at": ts(4),
        "service": "self",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_SELF_DELIVEROO,
        "docs": [
            {"doc_type": "income_summary", "filename": "Deliveroo_annual_summary.pdf", "media_type": "document"},
            {"doc_type": "expense_pack", "filename": "Courier_expenses_photos.zip", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Jamshid Ergashev",
            "nationality": "Uzbek",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7791 110045",
            "email": "jamshid.ergashev@mail.com",
            "age": "27",
            "service_interest": "Self-employed return (courier)",
            "uk_visa_status": "Skilled Worker dependent",
            "employment_type": "Courier (Deliveroo/Uber Eats)",
            "budget": "£149",
            "urgency": "High before deadline",
            "notes": "Income around £31k; expense evidence mostly photos. Needs category cleanup."
        }
    },
    {
        "tg_id": 100000008,
        "language": "en",
        "created_at": ts(6),
        "service": "company",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_COMPANY_ECOM,
        "docs": [
            {"doc_type": "penalty_notice", "filename": "CompaniesHouse_penalty_letter.pdf", "media_type": "document"},
            {"doc_type": "books_export", "filename": "Nexa_Xero_export_Q1-Q4.xlsx", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Marcus Reed",
            "nationality": "British",
            "country_of_residence": "United Kingdom",
            "phone": "+44 7702 450118",
            "email": "marcus@nexa-commerce.co.uk",
            "age": "36",
            "service_interest": "Late filing recovery + CT",
            "uk_visa_status": "British Citizen",
            "employment_type": "Director",
            "budget": "£1,150",
            "urgency": "Critical (penalties already issued)",
            "notes": "Needs triage for overdue accounts and CT600 with mitigation letter."
        }
    },
    {
        "tg_id": 100000009,
        "language": "uz",
        "created_at": ts(1),
        "service": "student",
        "status": "active",
        "payment_status": "pending",
        "conversation": CONV_STUDENT_UZ_FAMILY,
        "docs": [
            {"doc_type": "passport", "filename": "madina_passport.pdf", "media_type": "document"},
        ],
        "profile": {
            "full_name": "Madina Raximova",
            "nationality": "Uzbek",
            "country_of_residence": "Uzbekistan",
            "phone": "+998 97 441 8899",
            "email": "madina.rakhimova@gmail.com",
            "age": "30",
            "service_interest": "Student visa + dependent eligibility check",
            "uk_visa_status": "Applying first time",
            "employment_type": "Prospective student",
            "budget": "£299",
            "urgency": "Wants dependency decision first",
            "notes": "Main concern is whether child can join under planned course route."
        }
    },
]

ADMINS = [
    {
        "username": "superadmin",
        "password": "Brightway2026!",
        "display_name": "Super Admin",
        "role": "master",
    },
    {
        "username": "consultant1",
        "password": "Consult123!",
        "display_name": "James Carter",
        "role": "consultant",
    },
    {
        "username": "consultant2",
        "password": "Consult456!",
        "display_name": "Priya Sharma",
        "role": "consultant",
    },
]

def seed():
    conn = connect()
    cur = conn.cursor()

    # Ensure tables exist (run migrations inline)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        role TEXT DEFAULT 'consultant',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS admin_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        assigned_at TEXT NOT NULL,
        FOREIGN KEY(admin_id) REFERENCES admin_users(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(admin_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS user_ai_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        extracted_data TEXT DEFAULT '{}',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS ai_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        stats TEXT DEFAULT '{}',
        ai_conclusion TEXT,
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()

    # Ensure columns exist
    for col_sql in [
        "ALTER TABLE cases ADD COLUMN conversation_history TEXT DEFAULT '[]'",
        "ALTER TABLE cases ADD COLUMN context TEXT DEFAULT '{}'",
        "ALTER TABLE documents ADD COLUMN filename TEXT",
        "ALTER TABLE documents ADD COLUMN media_type TEXT DEFAULT 'document'",
    ]:
        try:
            cur.execute(col_sql)
            conn.commit()
        except Exception:
            pass

    print("🌱 Seeding demo data...")

    # ── INSERT USERS ──────────────────────────────────────────────
    inserted_user_ids = []
    for u in USERS:
        # Upsert user
        existing = cur.execute("SELECT id FROM users WHERE tg_id=?", (u["tg_id"],)).fetchone()
        if existing:
            user_db_id = existing[0]
            cur.execute("UPDATE users SET language=?, created_at=? WHERE id=?",
                        (u["language"], u["created_at"], user_db_id))
        else:
            cur.execute(
                "INSERT INTO users (tg_id, language, chat_mode, created_at) VALUES (?,?,?,?)",
                (u["tg_id"], u["language"], "chat", u["created_at"])
            )
            user_db_id = cur.lastrowid
        conn.commit()

        # ── INSERT CASE ─────────────────────────────────────────
        existing_case = cur.execute(
            "SELECT id FROM cases WHERE user_id=? AND service=?", (user_db_id, u["service"])
        ).fetchone()
        conv_json = json.dumps(u["conversation"])
        if existing_case:
            case_id = existing_case[0]
            cur.execute("""UPDATE cases SET status=?, payment_status=?, conversation_history=?, updated_at=?
                           WHERE id=?""",
                        (u["status"], u["payment_status"], conv_json, ts(), case_id))
        else:
            cur.execute("""INSERT INTO cases
                (user_id, service, status, payment_status, conversation_history, context, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (user_db_id, u["service"], u["status"], u["payment_status"],
                 conv_json, "{}", u["created_at"], ts()))
            case_id = cur.lastrowid
        conn.commit()

        # ── INSERT DOCUMENTS ────────────────────────────────────
        for i, doc in enumerate(u.get("docs", [])):
            fake_file_id = f"DEMO_FILE_{u['tg_id']}_{i:02d}"
            fake_unique_id = f"DEMO_UNIQUE_{u['tg_id']}_{i:02d}"
            existing_doc = cur.execute(
                "SELECT id FROM documents WHERE file_unique_id=?", (fake_unique_id,)
            ).fetchone()
            if not existing_doc:
                cur.execute("""INSERT INTO documents
                    (case_id, doc_type, filename, media_type, file_id, file_unique_id, created_at)
                    VALUES (?,?,?,?,?,?,?)""",
                    (case_id, doc["doc_type"], doc["filename"], doc["media_type"],
                     fake_file_id, fake_unique_id, ts(0, i, 0)))
        conn.commit()

        # ── INSERT AI PROFILE ───────────────────────────────────
        prof_json = json.dumps(u["profile"])
        existing_prof = cur.execute(
            "SELECT id FROM user_ai_profiles WHERE user_id=?", (user_db_id,)
        ).fetchone()
        if existing_prof:
            cur.execute("UPDATE user_ai_profiles SET extracted_data=?, updated_at=? WHERE user_id=?",
                        (prof_json, ts(), user_db_id))
        else:
            cur.execute("INSERT INTO user_ai_profiles (user_id, extracted_data, updated_at) VALUES (?,?,?)",
                        (user_db_id, prof_json, ts()))
        conn.commit()
        inserted_user_ids.append((user_db_id, u["tg_id"]))

    # ── INSERT ADMIN USERS ─────────────────────────────────────────
    admin_ids = {}
    for a in ADMINS:
        existing = cur.execute("SELECT id FROM admin_users WHERE username=?", (a["username"],)).fetchone()
        pw_hash = generate_password_hash(a["password"])
        if existing:
            cur.execute("UPDATE admin_users SET password_hash=?, display_name=?, role=? WHERE username=?",
                        (pw_hash, a["display_name"], a["role"], a["username"]))
            admin_ids[a["username"]] = existing[0]
        else:
            cur.execute("""INSERT INTO admin_users (username, password_hash, display_name, role, created_at)
                           VALUES (?,?,?,?,?)""",
                        (a["username"], pw_hash, a["display_name"], a["role"], ts()))
            admin_ids[a["username"]] = cur.lastrowid
        conn.commit()

    # ── ASSIGN USERS TO CONSULTANTS ────────────────────────────────
    c1_id = admin_ids.get("consultant1")
    c2_id = admin_ids.get("consultant2")
    # Assign all seeded users in round-robin (keeps demo realistic)
    assignments = []
    consultant_cycle = [x for x in (c1_id, c2_id) if x]
    if consultant_cycle:
        for idx, (user_id, _) in enumerate(inserted_user_ids):
            assignments.append((consultant_cycle[idx % len(consultant_cycle)], user_id))
    for admin_id, user_id in assignments:
        if admin_id:
            try:
                cur.execute("INSERT INTO admin_assignments (admin_id, user_id, assigned_at) VALUES (?,?,?)",
                            (admin_id, user_id, ts()))
                conn.commit()
            except Exception:
                pass  # Already assigned

    # ── INSERT SAMPLE REPORT ────────────────────────────────────────
    existing_report = cur.execute("SELECT id FROM ai_reports LIMIT 1").fetchone()
    if not existing_report:
        stats = {
            "new_users": 12, "new_cases": 18, "paid": 5, "completed": 3,
            "active": 15, "docs": 22,
            "by_service": {"student": 7, "paye": 5, "self": 4, "company": 2}
        }
        conclusion = (
            "This month marks a strong start for Brightway Consulting's digital operations. "
            "With 12 new users and 18 cases opened, the platform is gaining traction rapidly — "
            "particularly in student visa services, which account for 39% of all cases. "
            "This aligns with the typical pre-academic-year surge.\n\n"
            "Revenue conversion remains healthy: 5 of 18 cases have received payment, "
            "representing a 28% same-month conversion rate. PAYE refund cases show the highest "
            "conversion (4/5 paid) due to the clear value proposition and no upfront cost structure.\n\n"
            "Recommendation: consider a targeted outreach campaign for self-employed clients "
            "ahead of the January 31st Self Assessment deadline — this segment (4 cases) has the "
            "most urgency and lowest current representation."
        )
        cur.execute("""INSERT INTO ai_reports
            (report_type, period_start, period_end, stats, ai_conclusion, created_at)
            VALUES (?,?,?,?,?,?)""",
            ("monthly", ts(30), ts(), json.dumps(stats), conclusion, ts(1)))
        conn.commit()

    conn.close()

    print("\n✅ Demo data seeded successfully!\n")
    print("=" * 55)
    print("  ADMIN LOGINS")
    print("=" * 55)
    for a in ADMINS:
        role_icon = "👑" if a["role"] == "master" else "👤"
        print(f"  {role_icon} {a['role'].upper():<12}  {a['username']:<16}  {a['password']}")
    print("=" * 55)
    print(f"  URL: http://127.0.0.1:8080/admin/login")
    print("=" * 55)
    print(f"\n  Also works: env admin  →  admin / admin123")
    print()
    print("  DEMO USERS seeded:")
    for db_id, tg_id in inserted_user_ids:
        u = next(x for x in USERS if x["tg_id"] == tg_id)
        name = u["profile"].get("full_name", "?")
        print(f"  • DB#{db_id}  @{tg_id}  {name}  ({u['service']}, {u['status']})")
    print()


if __name__ == "__main__":
    seed()
