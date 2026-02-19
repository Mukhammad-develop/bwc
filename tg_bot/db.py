import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    language TEXT DEFAULT 'en',
    chat_mode TEXT DEFAULT 'menu',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    payment_status TEXT DEFAULT 'pending',
    conversation_history TEXT DEFAULT '[]',
    context TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    filename TEXT,
    media_type TEXT DEFAULT 'document',
    file_id TEXT NOT NULL,
    file_unique_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    proof_file_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    due_at TEXT NOT NULL,
    sent INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);
"""


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
        # Migrations for existing DBs
        try:
            conn.execute("ALTER TABLE users ADD COLUMN chat_mode TEXT DEFAULT 'menu'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN conversation_history TEXT DEFAULT '[]'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN context TEXT DEFAULT '{}'")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def get_or_create_user(conn: sqlite3.Connection, tg_id: int) -> int:
    cur = conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    if row:
        return row["id"]
    conn.execute(
        "INSERT INTO users (tg_id, created_at) VALUES (?, ?)",
        (tg_id, _now_iso()),
    )
    conn.commit()
    return conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,)).fetchone()["id"]


def set_language(conn: sqlite3.Connection, tg_id: int, language: str) -> None:
    conn.execute("UPDATE users SET language = ? WHERE tg_id = ?", (language, tg_id))
    conn.commit()


def get_language(conn: sqlite3.Connection, tg_id: int) -> str:
    row = conn.execute("SELECT language FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    return row["language"] if row else "en"


def get_chat_mode(conn: sqlite3.Connection, tg_id: int) -> str:
    row = conn.execute("SELECT chat_mode FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    return (row["chat_mode"] or "menu") if row else "menu"


def set_chat_mode(conn: sqlite3.Connection, tg_id: int, mode: str) -> None:
    conn.execute("UPDATE users SET chat_mode = ? WHERE tg_id = ?", (mode, tg_id))
    conn.commit()


def create_case(conn: sqlite3.Connection, user_id: int, service: str) -> int:
    now = _now_iso()
    conn.execute(
        "INSERT INTO cases (user_id, service, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, service, now, now),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM cases WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()["id"]


def get_active_case(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM cases WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()


def update_case(conn: sqlite3.Connection, case_id: int, **kwargs: Any) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = _now_iso()
    columns = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [case_id]
    conn.execute(f"UPDATE cases SET {columns} WHERE id = ?", values)
    conn.commit()


def add_document(conn: sqlite3.Connection, case_id: int, doc_type: str, file_id: str, file_unique_id: str, filename: str = None, media_type: str = "document") -> None:
    conn.execute(
        "INSERT INTO documents (case_id, doc_type, filename, media_type, file_id, file_unique_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (case_id, doc_type, filename or doc_type, media_type, file_id, file_unique_id, _now_iso()),
    )
    conn.commit()


def list_documents(conn: sqlite3.Connection, case_id: int) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM documents WHERE case_id = ?", (case_id,)).fetchall()


def add_payment(conn: sqlite3.Connection, case_id: int, method: str, status: str, proof_file_id: Optional[str] = None) -> None:
    conn.execute(
        "INSERT INTO payments (case_id, method, proof_file_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (case_id, method, proof_file_id, status, _now_iso()),
    )
    conn.commit()


def add_reminder(conn: sqlite3.Connection, case_id: int, reminder_type: str, due_at: str) -> None:
    conn.execute(
        "INSERT INTO reminders (case_id, type, due_at, created_at) VALUES (?, ?, ?, ?)",
        (case_id, reminder_type, due_at, _now_iso()),
    )
    conn.commit()


def due_reminders(conn: sqlite3.Connection, now_iso: str) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM reminders WHERE sent = 0 AND due_at <= ?", (now_iso,)
    ).fetchall()


def mark_reminder_sent(conn: sqlite3.Connection, reminder_id: int) -> None:
    conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()


def get_missing_docs(conn: sqlite3.Connection, case_id: int) -> List[str]:
    row = conn.execute("SELECT missing_docs FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["missing_docs"] or "[]")
    except json.JSONDecodeError:
        return []


def set_missing_docs(conn: sqlite3.Connection, case_id: int, missing: List[str]) -> None:
    update_case(conn, case_id, missing_docs=json.dumps(missing))


def get_conversation(conn: sqlite3.Connection, case_id: int) -> List[Dict[str, str]]:
    row = conn.execute("SELECT conversation_history FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["conversation_history"] or "[]")
    except json.JSONDecodeError:
        return []


def add_conversation_message(conn: sqlite3.Connection, case_id: int, role: str, content: str) -> None:
    conversation = get_conversation(conn, case_id)
    conversation.append({"role": role, "content": content, "timestamp": _now_iso()})
    update_case(conn, case_id, conversation_history=json.dumps(conversation))
