# Brightway Consulting — Full Project Specification Prompt

## Overview

You are building **Brightway Consulting** — a complete client relationship and case management platform for a UK consulting firm that specialises in student visas, PAYE tax refunds, self-employed tax returns, and company accounting. The system has three major parts that all share a single SQLite database via Django ORM:

1. **Django web admin panel** — the internal staff portal (admins, consultants, master admins)
2. **Telegram bot** (`bot/bot.py`, pyTelegramBotAPI) — the public-facing AI chat interface clients use
3. **Telegram userbot** (`bot/userbot.py`, Telethon) — a personal Telegram account that bridges real Telegram messages into the panel for live chat

The project lives at `/Users/abdurakhmon/Desktop/bwc` on the `django` branch.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | Django 4.x |
| Database | SQLite via Django ORM |
| Telegram bot | pyTelegramBotAPI (polling mode) |
| Telegram userbot | Telethon (async, MTProto) |
| AI | OpenAI `gpt-4o-mini` (chat) + Whisper (voice transcription) |
| Audio conversion | `ffmpeg` via `subprocess` (`.oga` → `.wav`) |
| Templates | Django Template Language |
| CSS | Custom `static/css/admin.css` (dark theme, modern card layout) |
| JavaScript | Vanilla JS (no framework), `fetch` for polling |
| Auth | Custom session-based (no Django auth app) |
| Env vars | `python-dotenv` → `bwc/settings.py` |

---

## File Structure

```
bwc/
├── bwc/
│   ├── settings.py          # Django settings (reads .env)
│   ├── urls.py              # Root URL config
│   └── wsgi.py
├── core/
│   └── models.py            # All Django ORM models
├── panel/
│   ├── urls.py              # All /admin/* URL patterns
│   ├── decorators.py        # login_required, master_required, is_elevated, can_view_user
│   ├── templatetags/
│   │   └── panel_tags.py    # Custom filters: fromjson, parse_file_tag, endswith, get_item, replace, split
│   └── views/
│       ├── auth.py          # login, logout, profile
│       ├── dashboard.py     # /admin dashboard
│       ├── users.py         # /admin/users — user list, user profile, send message, poll messages, assign
│       ├── cases.py         # /admin/cases — case list, case detail, case update
│       ├── files.py         # /admin/files — local file serve, TG proxy, download, transcribe
│       ├── admins.py        # /admin/admins — list, add, delete admin accounts
│       ├── reports.py       # /admin/reports — AI-generated analytics reports
│       ├── notifications.py # /admin/notifications — bell icon, mark read
│       ├── import_chat.py   # /admin/import-chat — Telethon chat import
│       ├── services_admin.py # /admin/services — dynamic service & step management (NEW)
│       └── helpers.py       # shared utilities (AI, file proxy, auth helpers, password hash)
├── bot/
│   ├── bot.py               # pyTelegramBotAPI polling bot
│   ├── userbot.py           # Telethon userbot (async)
│   └── services.py          # AI prompts, service detection, translations
├── static/
│   └── css/
│       └── admin.css        # All panel CSS
├── templates/
│   └── panel/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── users.html
│       ├── user_profile.html
│       ├── cases.html
│       ├── case_detail.html
│       ├── admins.html
│       ├── reports.html
│       ├── report_detail.html
│       ├── notifications.html
│       ├── import_chat.html
│       ├── profile.html
│       ├── services_admin.html  # (NEW)
│       └── service_edit.html    # (NEW)
├── manage.py
├── requirements.txt
├── .env
└── README.md
```

---

## Environment Variables (`.env`)

```
SECRET_KEY=change-this-to-random-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

BOT_TOKEN=<telegram bot token from BotFather>
TG_API_ID=28367729
TG_API_HASH=9d3ced645ec2f8453ad250a95d18c580
TG_PHONE=+<primary userbot phone>
TG_PHONE_2=                     # optional second Telegram account

OPENAI_API_KEY=<openai key>

ADMIN_USERNAME=admin             # hardcoded master admin, no DB entry needed
ADMIN_PASSWORD=admin123
```

---

## Database Models (`core/models.py`)

### Existing Models

#### `TgUser`
Stores every Telegram user who has ever contacted the bot.
- `tg_id` BigIntegerField unique
- `language` CharField (en / uz / ru, default en)
- `chat_mode` CharField (menu / ai, default menu)
- `linked_account` IntegerField (0 or 1 — which userbot account handles them)
- `created_at` DateTimeField

#### `Case`
One consulting engagement per user (can have multiple cases over time).
- `user` FK → TgUser
- `service` CharField choices: student / paye / self / company / general — **this list is now also driven by `ServiceDefinition` at runtime**
- `status` CharField: active / completed / cancelled
- `payment_status` CharField: pending / received / refunded
- `conversation_history` TextField (JSON array of chat messages)
- `context` TextField (JSON dict for arbitrary per-case state)
- `created_at`, `updated_at`
- Methods: `get_conversation()`, `set_conversation(conv)`, `add_message(role, content, sender=None)`

#### `Document`
Files/voice messages uploaded inside a case.
- `case` FK → Case
- `doc_type` CharField
- `filename` CharField nullable
- `media_type` CharField (document / voice / photo)
- `file_id` TextField (Telegram file_id for proxying)
- `file_unique_id` CharField
- `transcription` TextField nullable (Whisper result for voice messages)
- `created_at`

#### `Payment`
- `case` FK → Case
- `method` CharField
- `proof_file_id` TextField nullable
- `status` CharField
- `created_at`

#### `Reminder`
- `case` FK → Case
- `type` CharField
- `due_at` DateTimeField
- `sent` BooleanField
- `created_at`

#### `PendingSend`
Queue of outbound messages the userbot should send.
- `user_tg_id` CharField
- `message` TextField
- `sender_name` CharField (display name for attribution)
- `sent` BooleanField
- `account_index` IntegerField (0 or 1)
- `created_at`, `sent_at`

#### `ImportRequest`
Tracks requests to import existing Telegram chats via Telethon.
- `user_tg_id` CharField
- `label` CharField
- `status` CharField: pending / processing / done / error
- `message_count` IntegerField
- `error_msg` TextField nullable
- `created_at`, `completed_at`

#### `AdminUser`
Web panel staff accounts (stored in DB; env master has no DB entry).
- `username` unique CharField
- `password_hash` TextField (werkzeug-style pbkdf2 hash)
- `display_name` CharField nullable
- `role` CharField: master / admin / consultant
- `created_at`

#### `AdminAssignment`
Maps consultants to specific clients.
- `admin` FK → AdminUser
- `user` FK → TgUser
- unique_together (admin, user)

#### `UserAiProfile`
AI-extracted structured profile for a client.
- `user` OneToOne → TgUser
- `extracted_data` TextField (JSON)
- `updated_at`

#### `AiReport`
Saved AI analytics reports.
- `report_type` CharField
- `period_start`, `period_end` DateTimeField
- `stats` TextField (JSON)
- `ai_conclusion` TextField nullable
- `created_at`

#### `Notification`
In-panel bell notifications for admin staff.
- `recipient` FK → AdminUser
- `title` CharField
- `message` TextField
- `link` CharField nullable
- `is_read` BooleanField
- `created_at`

---

### New Models (to be added)

#### `ClientNote`
Staff-written notes attached to a client (TgUser), not tied to a specific case.
Meant for phone-call summaries, internal observations, follow-up reminders, etc.

```python
class ClientNote(models.Model):
    user        = models.ForeignKey(TgUser, on_delete=models.CASCADE, related_name="notes")
    author      = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, related_name="notes_written")
    body        = models.TextField()
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_notes"
        ordering = ["-created_at"]
```

Any logged-in staff member (consultant, admin, master) can create, edit, and delete their own notes. Masters and admins can delete any note.

#### `ServiceDefinition`
Replaces the hardcoded `SERVICE_CHOICES` and `SERVICE_INFO` dict in `services.py`. Services are now fully dynamic and managed from the admin panel.

```python
class ServiceDefinition(models.Model):
    slug        = models.SlugField(unique=True)           # e.g. "paye", "student"
    name        = models.CharField(max_length=200)        # e.g. "PAYE Tax Refund"
    description = models.TextField(blank=True)            # short public description
    ai_prompt   = models.TextField()                      # full system prompt for GPT
    is_active   = models.BooleanField(default=True)
    order       = models.IntegerField(default=0)          # display ordering
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_definitions"
        ordering = ["order", "name"]
```

#### `ServiceStep`
Each `ServiceDefinition` has an ordered list of progress steps that appear on the client profile's progress bar.

```python
class ServiceStep(models.Model):
    service     = models.ForeignKey(ServiceDefinition, on_delete=models.CASCADE, related_name="steps")
    label       = models.CharField(max_length=200)        # e.g. "Payment Received"
    order       = models.IntegerField(default=0)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "service_steps"
        ordering = ["order"]
```

Example steps for PAYE: `Payment Received` → `Documents Checked` → `Consultant Accepted` → `Submitted to HMRC` → `Refund Received` → `Done`.
Admins can add/remove/reorder/rename steps per service from the Services admin page.

#### `CaseProgress`
Tracks which step a particular case has currently reached.

```python
class CaseProgress(models.Model):
    case        = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="progress")
    current_step = models.ForeignKey(ServiceStep, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)
    updated_by  = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "case_progress"
```

---

## Admin Panel — Role System

Three roles with escalating privileges:

| Role | Scope |
|---|---|
| **master** | Full access to everything. Can manage admins, services, steps, system config. Can see all users/cases. |
| **admin** | Can see all users/cases. Cannot manage admin accounts or services. |
| **consultant** | Sees only users assigned to them via `AdminAssignment`. Can write notes, update progress. |

The **env master** (from `.env` `ADMIN_USERNAME` / `ADMIN_PASSWORD`) is a master-level account with no database entry. It is detected via `request.session["admin_logged_in"]` + `request.session["admin_role"] == "master"` when no `admin_id` is in the session.

### Decorators (`panel/decorators.py`)
- `@login_required` — any authenticated staff member
- `@master_required` — only master role (env master or DB master)
- `is_elevated(request)` → bool — master or admin role
- `can_view_user(request, user_db_id)` → bool — elevated or assigned consultant

---

## Admin Panel — URL Routes

```
GET/POST  /                          → login (redirect to /admin if logged in)
GET/POST  /admin/login               → login
GET       /admin/logout              → logout
GET/POST  /admin/profile             → own profile + password change
GET       /admin                     → dashboard
GET       /admin/cases               → case list (filter by service/status/search)
GET       /admin/cases/<id>          → case detail (conversation history, documents, payment)
POST      /admin/cases/<id>/update   → update case status/payment_status
GET       /admin/users               → user list
GET       /admin/users/<id>          → user profile (chat, docs, notes, progress bar)
POST      /admin/users/<id>/send     → send message via userbot queue
GET       /admin/users/<id>/poll     → AJAX long-poll for new messages
POST      /admin/users/<id>/extract-profile → trigger AI profile extraction
POST      /admin/users/<id>/assign   → assign/unassign consultant
GET       /admin/files/local/<path>  → serve local static file
GET       /admin/files/view/<id>     → proxy Telegram file (inline view)
GET       /admin/files/download/<id> → proxy Telegram file (download)
POST      /admin/documents/<id>/transcribe → Whisper transcribe a voice doc
GET       /admin/reports             → report list
POST      /admin/reports/generate/<type> → generate AI report
GET       /admin/reports/<id>        → report detail
GET       /admin/admins              → admin list (master only)
POST      /admin/admins/add          → create new admin (master only)
POST      /admin/admins/<id>/delete  → delete admin (master only)
GET       /admin/notifications       → notification list
POST      /admin/notifications/<id>/read → mark read
POST      /admin/notifications/read-all → mark all read
GET       /admin/notifications/preview  → AJAX dropdown preview
POST      /admin/notifications/mark-preview-read → mark preview items read
GET/POST  /admin/import-chat         → import Telegram chat via Telethon
GET       /admin/import-chat/<id>/status → AJAX poll import status

# ── NEW ────────────────────────────────────────────────────────────────────
GET       /admin/services            → service list (master + admin)
GET/POST  /admin/services/add        → create new service (master only)
GET/POST  /admin/services/<slug>/edit → edit service name, description, AI prompt, steps (master only)
POST      /admin/services/<slug>/delete → delete service (master only)
POST      /admin/services/<slug>/steps/add    → add a step to service (master + admin)
POST      /admin/services/<slug>/steps/<step_id>/edit   → rename/reorder step (master + admin)
POST      /admin/services/<slug>/steps/<step_id>/delete → delete step (master + admin)

# Notes on user profile (accessible within user_profile view, no separate URL needed for simple cases)
POST      /admin/users/<id>/notes/add          → create ClientNote
POST      /admin/users/<id>/notes/<note_id>/edit   → edit ClientNote (own note or elevated)
POST      /admin/users/<id>/notes/<note_id>/delete → delete ClientNote (own note or elevated)

# Progress on case
POST      /admin/cases/<id>/progress  → set CaseProgress.current_step (any staff assigned to user)
```

---

## Admin Panel — Page-by-Page UI Design

The panel uses a single dark-themed CSS file (`static/css/admin.css`) with CSS custom properties:

```css
--primary: #4f8ef7;
--bg: #0f1117;
--surface: #1a1d27;
--surface2: #22263a;
--border: #2e3350;
--text: #e8ecf4;
--text-muted: #7a84a8;
--danger: #e05b5b;
--success: #4caf7d;
--warning: #e0a84a;
```

All pages extend `base.html` which provides:
- Left sidebar with nav links (Dashboard, Users, Cases, Services, Reports, Admins (master only), Notifications bell)
- Top bar with logged-in admin name + role badge + logout
- `{% block content %}` main area
- `{% block extra_js %}` for page-level JS

### Login page (`login.html`)
- Centered card, dark background, Brightway Consulting logo/name
- Username + password fields
- Error message if invalid
- No registration link (staff accounts only)

### Dashboard (`dashboard.html`)
- Stat cards: Total Users, Total Cases, Active Cases, Paid Cases
- "Cases by Service" horizontal bar chart (data driven by `ServiceDefinition` slugs, bars filled via `data-pct` + JS)
- Recent cases table (10 rows): user tg_id, service, status, payment, date
- Quick link to generate AI report
- Shows "My Users" count for consultants

### Users list (`users.html`)
- Search box (tg_id / name / email from AI profile)
- Table: TG ID, name, language, cases count, docs count, joined date, profile button
- Elevated admins see all users; consultants see only assigned users

### User Profile (`user_profile.html`)
Full-featured client view. Contains several collapsible or tabbed sections:

**Header**
- Avatar circle with initials (first letter of full name, or first digit of tg_id if no name)
- Full name (from AI profile), Telegram ID, language badge, joined date
- "Extract AI Profile" button — triggers GPT to analyse the conversation and fill structured fields (name, email, phone, country, employment type, tax year etc.)

**AI Profile card**
- Rendered key-value pairs from `UserAiProfile.extracted_data`
- Last updated timestamp

**Assign consultant** (elevated only)
- Dropdown of AdminUser objects with role=consultant, current assignment shown

**Client Notes section** ← NEW
- Chronological list of `ClientNote` objects for this user
- Each note shows: author display name, role badge, timestamp, body text
- Edit/delete buttons (own note: any staff; any note: master/admin)
- "Add Note" button opens an inline form or modal with a textarea
- POST to `/admin/users/<id>/notes/add`
- Notes are plain text, multi-line

**Service Progress** ← NEW
- Shown per-case if the case's service has a `ServiceDefinition` with steps
- Linear horizontal progress bar: each step is a node with a label underneath
- Completed steps are filled (solid primary colour), current step pulses/highlighted, future steps are grey
- Admin staff can click any step node to set it as the current step
- POST to `/admin/cases/<id>/progress`
- The bar adapts dynamically to however many steps are defined for that service

**Conversation / unified chat**
- All cases for this user displayed in one scrollable timeline
- Each message bubble: role (user/assistant/admin), timestamp, content
- Voice messages render as `<audio>` HTML5 player + "Transcribe" button → calls Whisper
- File/document messages render as download link + file icon
- Message send box at bottom: textarea + "Send" button → POST to `/admin/users/<id>/send`, queues into `PendingSend` for userbot delivery
- JS polls `/admin/users/<id>/poll` every 2 seconds to fetch new messages without page reload (long-poll style with `fetch`)

**Documents tab / sidebar**
- All documents for this user (across all cases)
- Grouped by media type: voice messages, documents, photos
- Each entry: filename, type, date, view/download buttons

**Cases list** (compact)
- Each case: service, status, payment badge, created date, "Open Case" link

### Case Detail (`case_detail.html`)
- Full conversation history rendered as chat bubbles
- Sidebar: case metadata, status/payment dropdowns with save button
- Documents list for this case
- Progress bar (same component as on user profile) ← NEW
- Notes for the case's user also shown here ← NEW (read-only, link to full profile)

### Cases list (`cases.html`)
- Filter bar: service dropdown (populated from `ServiceDefinition`, not hardcoded), status, payment, date range
- Sortable table: case ID, user, service, status, payment, docs count, updated date

### Services Admin (`services_admin.html`) ← ENTIRELY NEW PAGE

Accessible by masters and admins. Linked in sidebar.

**Service list view**
- Table of all `ServiceDefinition` rows: name, slug, active toggle, steps count, edit/delete buttons
- "Add Service" button (master only)

**Service edit view / add view** (`service_edit.html`)
- Form fields:
  - **Slug** (auto-generated from name, read-only after creation)
  - **Name** (e.g. "PAYE Tax Refund")
  - **Description** (short text, shown in bot intro and reports)
  - **Active** checkbox
  - **Display order** integer
  - **AI System Prompt** — large `<textarea>` (full GPT system prompt for this service)
    - This is what `build_system_prompt()` in `bot/services.py` returns for this service
    - Placeholder/default text shown on creation: standard tone rules + service template
    - Masters can paste any prompt; AI will use it verbatim as the `system` message
  - **Progress Steps** — inline drag-and-drop ordered list
    - Each step: label text field, description field, drag handle, delete button
    - "Add Step" button appends new row
    - Steps are saved in order (JS sends ordered array via AJAX or form)
- Save button (POST)

**Step management inline on service edit page**
- Sorted list of `ServiceStep` objects for this service
- Drag to reorder (HTML5 drag or Sortable.js-style pure JS)
- Each row: order number (auto), label input, description input, delete (×) button
- "Add Step" appends a new empty row
- On save, steps are POSTed as a JSON array `[{label, description, order}, ...]`
- Backend recreates steps (delete all + bulk_create, or update_or_create by label+service)

### Admins page (`admins.html`) — master only
- Table: username, display name, role badge, created date, delete button
- "Add Admin" form: username, display name, password, role select (admin / consultant)
- Cannot delete the env master account (no DB entry for it)

### Reports page (`reports.html`)
- List of previously generated reports
- "Generate Report" form: report type (weekly / monthly / full), date range
- Reports call OpenAI with aggregated stats (case counts, service breakdown, payment totals) and return a narrative conclusion

### Notifications (`notifications.html`)
- List of all notifications for logged-in admin
- Bell icon in top bar shows unread count (polled via AJAX)
- "Mark all read" button
- Click notification → marks read + follows link

### Import Chat (`import_chat.html`)
- Form: Telegram user ID or username to import chat from, label
- Submits → creates `ImportRequest`, userbot picks it up from queue
- Status polling: AJAX every 3 seconds checks import status, shows progress

### Profile page (`profile.html`)
- Edit own display name
- Change password form

---

## Bot (`bot/bot.py`) — Telegram Public Interface

Uses `pyTelegramBotAPI` in polling mode.

### Handlers

| Command / Update type | Behaviour |
|---|---|
| `/start` | Welcome message + language selection inline keyboard |
| `/help` | Short help text in user's language |
| `/case` | Show current active case info (service, status, payment, doc count) |
| `/language` | Language selection keyboard |
| Callback `lang_en/uz/ru` | Sets `TgUser.language`, confirms, sends intro message |
| Any text message | `detect_service()` on content, `get_or_open_case()`, calls `ask_ai()` with last 20 messages, appends both user and AI messages to `Case.conversation_history` via `add_message()` |
| Photo / document | Saved as `Document(media_type="document")`, acknowledged with `t(lang, "doc_received")` |
| Voice message | Saved as `Document(media_type="voice")`, acknowledged with `t(lang, "doc_received")`. Transcription happens lazily from the panel when an admin clicks "Transcribe". |

### AI Flow
1. `detect_service(text)` — keyword matching against `SERVICE_KEYWORDS` dict (or falls back to DB `ServiceDefinition` slugs)
2. `build_system_prompt(service, lang)` — looks up `ServiceDefinition` by slug, returns `ai_prompt` field (**now DB-driven** instead of hardcoded)
3. `ask_ai(conversation, service, lang)` → `gpt-4o-mini` with system prompt + last 20 conversation turns
4. Reply sent to user, saved to DB

### PAYE Structured Flow
The PAYE service has a guided 7-step conversation flow defined in its `ai_prompt`:
1. Confirm they want PAYE tax refund
2. Employment dates (start/end for each tax year)
3. Employer name(s)
4. NI number
5. Email + phone number
6. UK bank sort code + account number
7. How many times worked in England

This flow text is stored in `ServiceDefinition(slug="paye").ai_prompt` and editable from the Services admin page.

---

## Userbot (`bot/userbot.py`) — Telethon Bridge

Runs as a standalone async process. Bridges real Telegram messages into the Django DB so the admin panel can read them without polling the Telegram Bot API (which only works for bot messages, not real accounts).

### Configuration
- `TG_PHONE` — primary account phone number
- `TG_PHONE_2` — optional second account (skip entirely if not set)
- `TG_API_ID`, `TG_API_HASH` — from my.telegram.org
- Session files stored at `bot/session1.session` and `bot/session2.session`

### Startup
```python
client1 = TelegramClient(SESSION, API_ID, API_HASH)
client2 = TelegramClient(SESSION_2, API_ID, API_HASH) if PHONE_2 else None
```
`main()` starts `client1`, registers handlers, then conditionally starts `client2` only if `PHONE_2` is set. If `client2` fails (e.g. session expired), it logs the error and continues with `client1` only.

### Event Handlers (per client)
- **New message from known user** → find `TgUser` by sender tg_id, find active `Case`, call `ask_ai()`, `add_message()` for both user message and AI reply, `PendingSend.objects.create()` to queue the reply for sending
- **New message from unknown user** → create `TgUser`, create `Case(service="general")`, flow same as above

All Django ORM calls inside async handlers are wrapped:
```python
await loop.run_in_executor(executor, lambda: <orm_operation>)
```

### Background Loops

**`send_queue_loop()`** — every 3 seconds:
```python
rows = PendingSend.objects.filter(sent=False, account_index=account_index)
for row in rows:
    await client.send_message(int(row.user_tg_id), row.message)
    row.sent = True; row.sent_at = now(); row.save()
```

**`import_queue_loop()`** — every 5 seconds:
```python
pending = ImportRequest.objects.filter(status="pending")
for req in pending:
    req.status = "processing"; req.save()
    await process_import(req.pk, req.user_tg_id)
```

**`process_import(req_id, user_tg_id)`**:
- Fetches up to 3000 messages from the Telegram chat identified by `user_tg_id` using `client.get_messages(peer, limit=3000)`
- Maps message roles (outgoing = "admin", incoming = "user")
- Creates or updates `TgUser`, creates `Case(service="general")` with full conversation history
- Updates `ImportRequest.status = "done"`

---

## AI Services (`bot/services.py`)

### Translations (`T` dict)
Three languages: `en`, `uz`, `ru`. Keys: `welcome`, `intro`, `ai_error`, `case_none`, `case_info`, `help_text`, `doc_received`.

### Service Detection
`detect_service(text: str) -> str` — returns service slug or "general". First checks DB `ServiceDefinition` slugs against `SERVICE_KEYWORDS` (static fallback dict), then falls back to "general". Should be updated to also query `ServiceDefinition` names and descriptions for keyword hints.

### `build_system_prompt(service: str, lang: str) -> str`
**Updated logic (DB-driven)**:
1. Try `ServiceDefinition.objects.get(slug=service, is_active=True)`
2. If found, return `sdef.ai_prompt` (with language instruction appended: "Reply in {lang_name}. Keep messages to 1-3 short sentences unless listing documents.")
3. If not found, return `GENERAL_SYSTEM_PROMPT` (hardcoded fallback for "general")

This means editing a service's AI prompt in the web panel immediately changes the bot's behaviour for that service — no code deployment needed.

### Tone Rules
The default AI prompts include enforced style rules stored as Python constants (`TONE_RULES`, `ANTI_BOT_PATTERNS`, `STYLE_EXAMPLES`). Admins can incorporate or override these in custom prompts.

---

## New Feature: Client Notes

### Model: `ClientNote`
Fields: `user`, `author` (AdminUser), `body` (TextField), `created_at`, `updated_at`

### UI: Notes Section on User Profile
Located on the user profile page (`user_profile.html`), between the "AI Profile" card and the "Conversation" section.

**Design:**
- Section heading "Client Notes" with a "+ Add Note" button (right-aligned)
- Each note rendered as a card:
  - Top row: author avatar circle (initials), author name, role badge (colour-coded: master=gold, admin=blue, consultant=green), relative timestamp (e.g. "2 hours ago")
  - Body: plain text, preserving newlines (`white-space: pre-wrap`)
  - Bottom row (if authorised): "Edit" (pencil icon) + "Delete" (trash icon) buttons — shown only to note author or elevated admins
- "Add Note" opens a slide-down form or modal:
  - Textarea (required, min 1 char, max 2000 chars), "Save Note" and "Cancel" buttons
  - POST to `/admin/users/<id>/notes/add`
- "Edit Note" replaces the note body with an inline textarea pre-filled with current body, "Update" and "Cancel" buttons
  - POST to `/admin/users/<id>/notes/<note_id>/edit`
- Delete triggers a JS confirm dialog → POST to `/admin/users/<id>/notes/<note_id>/delete`

**Permissions:**
- Any staff can create notes on any user they can view
- Authors can edit/delete their own notes
- Masters and admins can edit/delete any note

---

## New Feature: Service Progress Tracking

### Models: `ServiceStep`, `CaseProgress`

### UI: Progress Bar on User Profile and Case Detail

**Where it appears:**
- On user profile, once per active/completed case that has a `ServiceDefinition` with steps
- On case detail page, prominently at the top of the sidebar

**Visual design (horizontal linear bar):**
```
[●]────────[●]────────[◐]────────[○]────────[○]
Paid      Docs      Consultant  Submitted  Done
         Checked   Accepted    to HMRC
```
- Filled circle `●` = completed steps (solid `--primary` colour)
- Half-filled / pulsing `◐` = current step (highlighted, primary with glow animation)
- Empty circle `○` = future steps (grey)
- Connecting lines between circles: filled up to current step, grey after

**Implementation:**
- Pure CSS + JS, no external library needed
- The bar is generated from `ServiceStep` objects ordered by `order`
- `CaseProgress.current_step` determines which step is active
- Steps before current (index < current index) = completed
- Staff can click any step bubble to advance or rewind progress → POST to `/admin/cases/<id>/progress` with `step_id`
- On success, bar re-renders (full page reload or JS update of class names)

**Permissions:**
- Any staff who can view the case can update progress
- Progress updates are logged (updated_by = current admin, updated_at auto)

---

## New Feature: Dynamic Services Management

### Model: `ServiceDefinition`, `ServiceStep`

### Page: `/admin/services` (`services_admin.html`)

Only masters and admins can access this page. Linked in the sidebar nav.

**Service list:**
- Table with columns: Name, Slug, Active (toggle), Steps, Last Updated, Actions
- Active toggle is a `<form>` POST with a checkbox — instantly toggles `is_active`
- Edit button → `/admin/services/<slug>/edit`
- Delete button (master only) → confirmation modal → POST `/admin/services/<slug>/delete`
- "Add Service" button (master only) at top right

**Add / Edit service page** (`service_edit.html`):

Form layout (two columns on wide screen, single column on mobile):

Left column:
- **Service Name** text input (required)
- **Slug** — auto-populated from name using JS (slugify: lowercase, replace spaces with `-`, strip special chars); read-only after creation
- **Description** textarea (short, shown in bot intro and reports)
- **Active** checkbox
- **Display Order** number input

Right column (full height):
- **AI System Prompt** — large `<textarea>` (~20 rows)
  - Labelled: "GPT system prompt — what the AI knows about this service and how it behaves"
  - A "Reset to default template" button pre-fills with a standard template including tone rules
  - Syntax is plain text (no code formatting required)

Below both columns:
- **Progress Steps** — inline ordered list
  - Each step row: drag handle (⠿), order number (auto-numbered), Label text input, Description text input, Delete (×) button
  - "+ Add Step" button appends new empty row at the end
  - Steps can be reordered by drag-and-drop (pure JS using HTML5 `draggable` attribute + `dragover` / `drop` events)
  - On form submit, step data serialised as hidden inputs with indexed names: `steps[0][label]`, `steps[0][description]`, `steps[1][label]`, etc.

Save button (bottom): creates/updates service and all steps in one transaction.

**Backend save logic:**
```python
# In services_admin view:
with transaction.atomic():
    sdef, _ = ServiceDefinition.objects.update_or_create(slug=slug, defaults={...})
    sdef.steps.all().delete()
    for i, step_data in enumerate(steps):
        ServiceStep.objects.create(service=sdef, label=step_data['label'], description=step_data.get('description',''), order=i)
```

---

## Authentication Flow

1. `GET /` or `GET /admin/login` — renders login form if not authenticated
2. `POST /admin/login` — `check_admin_login(username, password)`:
   a. First checks env master (`ADMIN_USERNAME` / `ADMIN_PASSWORD`, plain compare)
   b. Then checks `AdminUser.objects.get(username=username)` + `check_password(hash, password)`
   c. On success: `request.session["admin_logged_in"] = True`, `request.session["admin_role"] = role`, `request.session["admin_id"] = user.pk` (or `None` for env master)
3. `@login_required` decorator: allows if `_get_admin(request) is not None` OR `request.session.get("admin_logged_in")` is True
4. `@master_required` decorator: allows if role is master (DB or env master)
5. `GET /admin/logout` → `request.session.flush()`, redirect to login

---

## Live Chat Polling

On the user profile page, a JS `setInterval` polls every 2000ms:

```javascript
fetch(POLL_URL)
  .then(r => r.json())
  .then(data => {
    data.messages.forEach(msg => appendBubble(msg));
    if (data.messages.length) scrollToBottom();
  });
```

`poll_messages` view returns only messages with `timestamp > last_seen` (passed as query param). Messages from `PendingSend` (sent by admins) are also included once `sent=True`.

---

## File Handling

### Voice message transcription
1. Admin clicks "Transcribe" on a voice document → POST to `/admin/documents/<id>/transcribe`
2. Backend fetches file bytes from Telegram via `requests.get(get_tg_file_url(file_id))`
3. `convert_audio_to_wav(data, ".oga")` → spawns `ffmpeg` subprocess: `ffmpeg -i pipe:0 -ar 16000 -ac 1 -f wav pipe:1`
4. WAV bytes POSTed to OpenAI Whisper API → returns transcript text
5. `Document.transcription = transcript_text; doc.save()` → page refresh shows transcript below audio player

### Telegram file proxy
`get_tg_file_url(file_id)` calls `https://api.telegram.org/bot<BOT_TOKEN>/getFile?file_id=<id>` to get `file_path`, then returns `https://api.telegram.org/file/bot<BOT_TOKEN>/<file_path>`.

`file_view` and `file_download` views stream this URL through Django to the browser, so the admin panel doesn't expose the bot token in frontend HTML.

---

## Django Settings Summary (`bwc/settings.py`)

```python
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG", default=False)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "panel",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

USE_TZ = False  # naive datetimes for consistency with bot data

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"

# Custom settings loaded from .env
BOT_TOKEN = env("BOT_TOKEN", default="")
TG_API_ID = int(env("TG_API_ID", default="0"))
TG_API_HASH = env("TG_API_HASH", default="")
TG_PHONE = env("TG_PHONE", default="")
TG_PHONE_2 = env("TG_PHONE_2", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
ADMIN_USERNAME = env("ADMIN_USERNAME", default="admin")
ADMIN_PASSWORD = env("ADMIN_PASSWORD", default="")
```

---

## Installation and Running

```bash
# Clone and setup
cd /path/to/bwc
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env   # fill in tokens, keys, phone numbers

# Database
python manage.py migrate

# Seed default services (if building services management)
python manage.py shell -c "from core.models import ServiceDefinition; ..."

# Run web panel (terminal 1)
python manage.py runserver 8000

# Run bot (terminal 2)
python bot/bot.py

# Run userbot (terminal 3) — will prompt for Telegram auth code on first run
python bot/userbot.py
```

---

## Key Implementation Rules

1. **No hardcoded service list** — services come from `ServiceDefinition` DB table. The hardcoded `SERVICE_CHOICES` in `Case` can remain for backwards compat but the UI service filter dropdowns must query the DB.

2. **`build_system_prompt()` must query DB** — `bot/services.py`'s `build_system_prompt(service, lang)` must try `ServiceDefinition.objects.get(slug=service)` and return `sdef.ai_prompt + f"\nReply in {lang_name}."`. Fall back to `GENERAL_SYSTEM_PROMPT` if not found.

3. **All ORM in async context uses `run_in_executor`** — every Django ORM call inside `userbot.py`'s async functions must be:
   ```python
   await loop.run_in_executor(executor, lambda: OrmModel.objects.filter(...).first())
   ```

4. **No Django admin app** — the project uses a fully custom panel, not `django.contrib.admin`.

5. **No Django auth** — custom session-based auth with `werkzeug`-compatible pbkdf2 password hashing.

6. **Template tags required** — child templates that use custom filters must include `{% load panel_tags %}`.

7. **`USE_TZ = False`** — all datetimes are naive for consistency.

8. **Static files in dev** — `bwc/urls.py` includes `+ static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])`.

9. **Client Notes visibility** — consultants see notes on users they are assigned to; elevated admins see all notes.

10. **Progress bar steps** — if `CaseProgress` doesn't exist for a case, the bar renders with no step highlighted (all grey). Staff clicking any step creates the `CaseProgress` record.

---

## requirements.txt

```
Django>=4.2
python-dotenv
pyTelegramBotAPI
telethon
openai
requests
werkzeug
```
