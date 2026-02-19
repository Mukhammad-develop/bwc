# Brightway Consulting AI Telegram Bot

This bot uses AI to guide clients conversationally through student visas, PAYE tax refunds, self-employment tax, and company accounting services.

## What changed (Feb 2026)

The bot now operates as a **fully AI-driven conversational assistant**:
- ✅ No more rigid step-by-step questionnaires
- ✅ The AI asks questions naturally, adapts to user responses, and guides them through info gathering, document uploads, and payment
- ✅ Each service (student, PAYE, self-employed, company) has a tailored AI prompt with specific instructions
- ✅ All conversation history is saved in the database for context

## Setup

1. Create a `.env` file in the project root (`bwc/.env`) with:

```bash
BOT_TOKEN=your_telegram_bot_token
DB_PATH=bot.db
TIMEZONE_OFFSET_HOURS=0
ADMIN_CHAT_ID=your_admin_telegram_id
OPENAI_API_KEY=your_openai_api_key
```

2. Install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run:

```bash
cd tg_bot
python bot.py
```

## How it works

1. **User selects language** (English, Uzbek, Russian) and **service** (student, PAYE, self-employed, company)
2. **Bot creates a case** and starts a conversation with the AI
3. **AI collects info conversationally** — no fixed questions, adapts to user's answers
4. **AI guides document uploads** — tells user what documents are needed based on their service
5. **AI mentions payment** when appropriate
6. **User can upload documents anytime** — the AI acknowledges and continues
7. **"Back to menu" button** available throughout

## Structure

- `bot.py` — main AI-driven bot logic (simplified, conversation-based)
- `db.py` — SQLite schema with conversation_history and context storage
- `config.py` — environment variables
- `bot_old.py` — backup of previous rigid-flow bot (for reference)

## Commands

- `/start` — reset and show welcome
- `/help` — show help text
- `/case` or `/mycase` — show current case status

## Security

⚠️ **NEVER commit API keys to the repo.** If you exposed a key, revoke it immediately at https://platform.openai.com/api-keys and generate a new one. Use `.env` only.

## Notes

- SQLite is used by default (`bot.db`)
- The AI is powered by OpenAI's `gpt-4o-mini` model
- Conversation history is limited to the last 15 messages when calling the API (to stay within token limits)
- The AI system prompt is tailored per service and includes disclaimers about visa/tax outcomes
