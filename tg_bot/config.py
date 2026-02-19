import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from current dir and from project root (bwc/) so key is found when running from tg_bot/
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Create a .env file with BOT_TOKEN=... or export it.")

DB_PATH = os.getenv("DB_PATH", "bot.db")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Timezone offset in hours for reminders, default UK time (GMT/BST handled as fixed offset here)
TIMEZONE_OFFSET_HOURS = int(os.getenv("TIMEZONE_OFFSET_HOURS", "0"))
