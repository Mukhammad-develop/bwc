# Brightway Consulting (BWC) — Django

A full-stack Django application for **Brightway Consulting**: a Telegram bot ecosystem plus a web admin panel. Clients interact via Telegram (main bot and/or userbot); staff manage cases, users, documents, AI reports, and live chat from the panel.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [Running the Application](#running-the-application)
- [Admin Panel](#admin-panel)
- [Telegram Bot](#telegram-bot)
- [Userbot](#userbot)
- [Development & Deployment](#development--deployment)

---

## Overview

- **Web panel**: Django app for staff to log in, view dashboard stats, manage cases and Telegram users, view/send messages, handle files (view/download/transcribe voice), generate AI reports, manage admins and notifications, and queue chat imports.
- **Main bot** (`bot/bot.py`): Public Telegram bot (pyTelegramBotAPI) for `/start`, language selection, service selection, document uploads, and AI-assisted conversation; all data stored via Django ORM.
- **Userbot** (`bot/userbot.py`): Up to two personal Telegram accounts (Telethon) that mirror the same flows in private chats, process admin-sent messages from the panel, and run background queues (pending messages, chat import). Uses the same Django database.

All components share a single SQLite database and Django models; no separate bot-specific DB.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Web framework | Django 4.2+ |
| Database | SQLite (Django ORM) |
| Telegram Bot API | pyTelegramBotAPI |
| Telegram userbot | Telethon |
| AI / transcription | OpenAI API (GPT-4o-mini, Whisper) |
| Config | python-dotenv, `.env` |
| Audio conversion | ffmpeg (system binary, for Whisper) |

---

## Project Structure

```
bwc/
├── manage.py                 # Django CLI entrypoint
├── requirements.txt         # Python dependencies
├── .env                     # Secrets (not in git)
├── db.sqlite3               # SQLite DB (created after migrate)
├── uploads/                 # Uploaded files (media root)
├── sessions/                # Telethon session files (userbot)
├── static/                  # Static assets
│   └── css/
│       └── admin.css
├── templates/
│   └── panel/               # Admin panel templates
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── cases.html, case_detail.html
│       ├── users.html, user_profile.html
│       ├── profile.html
│       ├── reports.html, report_detail.html
│       ├── admins.html
│       ├── notifications.html
│       └── import_chat.html
├── bwc/                     # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                    # Shared Django app (models only)
│   ├── models.py            # TgUser, Case, Document, Payment, Reminder,
│   │                        # PendingSend, ImportRequest, AdminUser,
│   │                        # AdminAssignment, UserAiProfile, AiReport,
│   │                        # Notification
│   └── migrations/
├── panel/                   # Admin web panel app
│   ├── urls.py              # All panel routes
│   ├── decorators.py        # login_required, master_required
│   ├── templatetags/
│   │   └── panel_tags.py    # Custom filters (fromjson, parse_file_tag, etc.)
│   └── views/
│       ├── auth.py          # Login, logout, profile
│       ├── dashboard.py     # Stats, recent cases
│       ├── cases.py         # Case list, detail, update
│       ├── users.py         # User list, profile, send/poll messages, assign
│       ├── files.py         # Local file, Telegram file view/download, transcribe
│       ├── reports.py       # AI reports list, generate, detail
│       ├── admins.py        # Master: add/delete admins, assignments
│       ├── notifications.py # Notifications list, read, preview
│       ├── import_chat.py   # Queue import, status
│       └── helpers.py       # Shared helpers (AI, file proxy, session, etc.)
└── bot/                     # Telegram processes (Django ORM)
    ├── bot.py               # Main bot (polling)
    ├── userbot.py           # Userbot (up to 2 accounts)
    └── services.py          # Translations, AI (ask_ai, detect_service)
```

---

## Prerequisites

- **Python 3.10+** (tested with 3.10–3.14)
- **ffmpeg** installed and on `PATH` (for voice message transcription)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Telegram API credentials** for userbot: [my.telegram.org](https://my.telegram.org) → API development tools → `api_id` and `api_hash`
- **OpenAI API key** (optional but required for AI replies and Whisper transcription)

---

## Installation

1. **Clone and enter the project**
   ```bash
   git clone <repo-url> bwc && cd bwc
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Copy environment template and edit**
   ```bash
   cp .env.example .env
   # Edit .env with your BOT_TOKEN, TG_API_ID, TG_API_HASH, etc.
   ```
   If there is no `.env.example`, create `.env` with the variables listed in [Environment Variables](#environment-variables).

4. **Run migrations and (optionally) create first admin**
   ```bash
   python manage.py migrate
   # Create first admin user (master) — use a script or Django shell to insert
   # into core.AdminUser with hashed password; or use panel login view which
   # accepts first-time setup via ADMIN_USERNAME / ADMIN_PASSWORD in .env.
   ```

5. **Collect static files (production)**
   ```bash
   python manage.py collectstatic --noinput
   ```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes (for bot) | Telegram Bot API token from @BotFather |
| `OPENAI_API_KEY` | For AI/Whisper | OpenAI API key for GPT and Whisper |
| `TG_API_ID` | For userbot | Telegram API ID (integer) |
| `TG_API_HASH` | For userbot | Telegram API hash |
| `TG_PHONE` | For userbot | Phone for first account (e.g. +44…) |
| `TG_PHONE_2` | Optional | Phone for second userbot account |
| `DJANGO_SECRET_KEY` | Production | Secret key for Django (or set `FLASK_SECRET_KEY` as fallback) |
| `DEBUG` | Optional | `true` / `false` (default `false`) |
| `ALLOWED_HOSTS` | Production | Comma-separated hosts (e.g. `yourdomain.com`) |
| `ADMIN_USERNAME` | Optional | First-time admin login username |
| `ADMIN_PASSWORD` | Optional | First-time admin login password |

`.env` is loaded in `bwc/settings.py` via `python-dotenv`. Do not commit `.env`.

---

## Database

- **Engine**: SQLite, file `db.sqlite3` at project root.
- **Migrations**: All models live in `core`; run `python manage.py migrate` after pull.
- **Tables**: `users`, `cases`, `documents`, `payments`, `reminders`, `pending_send`, `import_requests`, `admin_users`, `admin_assignments`, `user_ai_profiles`, `ai_reports`, `notifications` (see `core/models.py` and `db_table` in each model).

---

## Running the Application

From the project root with `venv` activated:

| Component | Command | Notes |
|-----------|---------|--------|
| **Web panel** | `python manage.py runserver [port]` | Default port 8000. Login at `/admin/login` or `/`. |
| **Main bot** | `python bot/bot.py` | Uses `BOT_TOKEN`; long-polling. |
| **Userbot** | `python bot/userbot.py` | Runs both accounts if configured. First-time auth below. |

**Userbot first-time auth (one-time per account):**
```bash
python bot/userbot.py --auth   # Account 1 → sessions/userbot.session
python bot/userbot.py --auth2  # Account 2 → sessions/userbot2.session
```

All three can run at once (e.g. panel on 8000, bot and userbot in separate terminals). They share `db.sqlite3`.

---

## Admin Panel

- **Base URL**: `/` or `/admin` (dashboard after login).
- **Login**: `/admin/login` (or `/`). Session-based; optional first-time setup via `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`.

**Main sections:**

| Section | URL | Description |
|---------|-----|-------------|
| Dashboard | `/admin` | Stats (users, cases, by service), recent cases, latest report link. |
| Cases | `/admin/cases` | List/filter cases; open case detail with conversation and documents. |
| Users | `/admin/users` | List Telegram users with AI profile snippets; open user profile. |
| User profile | `/admin/users/<id>` | Full chat history, AI profile, files; send message, poll for new messages, transcribe voice, assign to admin. |
| Files | Via case/user views | View/download local or Telegram files; transcribe document by ID. |
| Reports | `/admin/reports` | List AI reports; generate by type; view report detail. |
| Admins | `/admin/admins` | Master only: add/delete admins, manage user assignments. |
| Notifications | `/admin/notifications` | List, mark read, preview. |
| Import chat | `/admin/import-chat` | Queue and check status of Telegram chat import. |
| Profile | `/admin/profile` | Change password, etc. |

**Roles:** Admin vs Master. Masters can manage other admins and assignments; both can access cases/users/reports according to assignment and permissions (see `panel/decorators.py` and `panel/views/helpers.py`).

---

## Telegram Bot

- **Entrypoint**: `bot/bot.py` (Django must be bootstrapped; it sets `DJANGO_SETTINGS_MODULE` and runs `django.setup()`).
- **Library**: pyTelegramBotAPI (long polling).
- **Features**: `/start`, `/help`, language selection, service selection (Student, PAYE, Self-Employed, Company, General), document/photo upload, AI conversation via `bot/services.py` (`ask_ai`), case creation and conversation history stored in Django ORM.

---

## Userbot

- **Entrypoint**: `bot/userbot.py` (same Django bootstrap).
- **Library**: Telethon; up to two accounts (`TG_PHONE`, `TG_PHONE_2`).
- **Features**: Same conversational flow as the main bot in private chats; links users to account index (`linked_account`); processes `PendingSend` queue (messages composed in panel); runs import queue for `ImportRequest`; saves files to `uploads/` and documents in DB. Session files in `sessions/` (e.g. `userbot.session`, `userbot2.session`).

---

## Development & Deployment

- **Static files**: Development uses `STATICFILES_DIRS`; production run `collectstatic` and serve `/static/` from `staticfiles/` (or CDN).
- **Media files**: Served at `/uploads/` in dev via `bwc/urls.py`; in production use the same path and document root or a separate media server.
- **Security**: Set `DEBUG=False`, a long random `SECRET_KEY`, and `ALLOWED_HOSTS`. Consider HTTPS, `SECURE_*` and `SESSION_COOKIE_SECURE` (see Django docs).
- **Checks**: `python manage.py check` and `python manage.py check --deploy` before deploy.
- **Branch**: This README describes the **Django** branch; the old Flask + standalone bot layout is not present on this branch.

---

## License

Proprietary / as per repository.
