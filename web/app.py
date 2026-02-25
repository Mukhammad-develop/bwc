import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, Response, send_file)
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
MASTER_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
MASTER_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

DB_PATH = os.getenv("DB_PATH", "bot.db")
if not DB_PATH.startswith("/"):
    DB_PATH = str(Path(__file__).parent.parent / "tg_bot" / "bot.db")


# ─────────────────────────── DB HELPERS ───────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_admin_tables():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role         TEXT DEFAULT 'consultant',
            created_at   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admin_assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            assigned_at TEXT NOT NULL,
            FOREIGN KEY(admin_id) REFERENCES admin_users(id),
            FOREIGN KEY(user_id)  REFERENCES users(id),
            UNIQUE(admin_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS user_ai_profiles (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER UNIQUE NOT NULL,
            extracted_data TEXT DEFAULT '{}',
            updated_at     TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS ai_reports (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type    TEXT NOT NULL,
            period_start   TEXT NOT NULL,
            period_end     TEXT NOT NULL,
            stats          TEXT DEFAULT '{}',
            ai_conclusion  TEXT,
            created_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_id INTEGER NOT NULL,
            title        TEXT NOT NULL,
            message      TEXT NOT NULL,
            link         TEXT,
            is_read      INTEGER DEFAULT 0,
            created_at   TEXT NOT NULL,
            FOREIGN KEY(recipient_id) REFERENCES admin_users(id) ON DELETE CASCADE
        );
        """)
        conn.commit()
        for col, defval in [
            ("conversation_history", "'[]'"),
            ("context", "'{}'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE cases ADD COLUMN {col} TEXT DEFAULT {defval}")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        for col, defval in [("filename", "NULL"), ("media_type", "'document'")]:
            try:
                conn.execute(f"ALTER TABLE documents ADD COLUMN {col} TEXT DEFAULT {defval}")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("UPDATE documents SET filename = doc_type WHERE filename IS NULL")
            conn.commit()
        except Exception:
            pass


init_admin_tables()


def seed_master_admin():
    """Create a DB-backed master admin account on first run if it doesn't exist."""
    username = os.getenv("MASTER2_USERNAME", "bwmaster")
    password = os.getenv("MASTER2_PASSWORD", "Brightway2025!")
    display  = os.getenv("MASTER2_DISPLAY",  "Brightway Master")
    now      = datetime.utcnow().isoformat()
    try:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM admin_users WHERE username=?", (username,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO admin_users (username, password_hash, display_name, role, created_at) VALUES (?,?,?,?,?)",
                    (username, generate_password_hash(password), display, "master", now)
                )
                conn.commit()
    except Exception:
        pass


seed_master_admin()


# ─────────────────────────── NOTIFICATIONS ────────────────────────

def notify_masters(title, message, link=None, exclude_id=None):
    """Send a notification to every DB master admin (except the actor themselves)."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        masters = conn.execute(
            "SELECT id FROM admin_users WHERE role='master'"
        ).fetchall()
        for m in masters:
            if exclude_id and m["id"] == exclude_id:
                continue
            conn.execute(
                "INSERT INTO notifications (recipient_id, title, message, link, created_at) VALUES (?,?,?,?,?)",
                (m["id"], title, message, link, now)
            )
        conn.commit()


def notify_user(recipient_id, title, message, link=None):
    """Send a notification to a specific DB admin user."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO notifications (recipient_id, title, message, link, created_at) VALUES (?,?,?,?,?)",
            (recipient_id, title, message, link, now)
        )
        conn.commit()


def get_unread_count():
    """Return unread notification count for the current session user (0 for env master)."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return 0
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE recipient_id=? AND is_read=0",
            (admin_id,)
        ).fetchone()
        return row[0] if row else 0


@app.context_processor
def inject_notifications():
    if session.get("admin_logged_in"):
        return {"unread_notifications": get_unread_count()}
    return {"unread_notifications": 0}


@app.template_filter("fromjson")
def fromjson_filter(s):
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


@app.template_filter("parse_file_tag")
def parse_file_tag(content):
    """
    Parse [FILE:unique_id:filename:media_type] tags.
    Returns dict with keys: is_file, unique_id, filename, media_type
    Also handles legacy [Uploaded document: filename] format.
    """
    import re
    if content.startswith("[FILE:"):
        # New format: [FILE:unique_id:filename:media_type]
        inner = content[6:].rstrip("]")
        parts = inner.split(":", 2)
        if len(parts) == 3:
            return {"is_file": True, "unique_id": parts[0], "filename": parts[1], "media_type": parts[2]}
    m = re.match(r'^\[Uploaded document: (.+)\]$', content.strip())
    if m:
        fname = m.group(1)
        return {"is_file": True, "unique_id": None, "filename": fname,
                "media_type": "photo" if fname.lower().endswith(('.jpg','.jpeg','.png','.gif','.webp')) else "document"}
    return {"is_file": False}


# ─────────────────────────── AUTH ─────────────────────────────────

def check_admin_login(username, password):
    """Returns (ok, role, admin_id, display_name)."""
    if username == MASTER_USERNAME and password == MASTER_PASSWORD:
        return True, "master", None, "Master Admin"
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return True, row["role"], row["id"], row["display_name"] or username
    return False, None, None, None


def login_required(f):
    @wraps(f)
    def inner(*a, **kw):
        if not session.get("admin_logged_in"):
            flash("Please log in.", "warning")
            return redirect(url_for("admin_login"))
        return f(*a, **kw)
    return inner


def master_required(f):
    """Only the hardcoded .env master or DB master-role users."""
    @wraps(f)
    def inner(*a, **kw):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        if session.get("admin_role") != "master":
            flash("Master admin access required.", "error")
            return redirect(url_for("admin_dashboard"))
        return f(*a, **kw)
    return inner


def elevated_required(f):
    """Master or Admin role — can see all users/cases/reports but NOT manage admins."""
    @wraps(f)
    def inner(*a, **kw):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        if session.get("admin_role") not in ("master", "admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("admin_dashboard"))
        return f(*a, **kw)
    return inner


def can_view_user(user_db_id):
    """Master and Admin can see all users; Consultant only sees assigned users."""
    role = session.get("admin_role")
    if role in ("master", "admin"):
        return True
    admin_id = session.get("admin_id")
    if not admin_id:
        return False
    with get_db() as conn:
        return bool(conn.execute(
            "SELECT 1 FROM admin_assignments WHERE admin_id=? AND user_id=?",
            (admin_id, user_db_id)
        ).fetchone())


def is_elevated():
    return session.get("admin_role") in ("master", "admin")


# ─────────────────────────── AI HELPERS ───────────────────────────

def call_ai(system_prompt, user_content, max_tokens=800):
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[AI] {type(e).__name__}: {e}")
        return None


def extract_user_profile(user_db_id):
    with get_db() as conn:
        cases = conn.execute(
            "SELECT * FROM cases WHERE user_id = ?", (user_db_id,)
        ).fetchall()
    if not cases:
        return {}
    lines = []
    for case in cases:
        msgs = json.loads(case["conversation_history"] or "[]")
        for m in msgs:
            lines.append(f"{'User' if m['role']=='user' else 'AI'}: {m['content']}")
    if not lines:
        return {}
    conversation_text = "\n".join(lines[-80:])
    system = """You are a data extractor for Brightway Consulting, a UK immigration and tax firm.
Extract structured client information from their chat with the AI assistant.
Return ONLY valid JSON (no markdown, no explanation) with these keys:
{
  "full_name": "",
  "nationality": "",
  "country_of_residence": "",
  "phone": "",
  "email": "",
  "age": "",
  "service_interest": "",
  "uk_visa_status": "",
  "employment_type": "",
  "budget": "",
  "urgency": "",
  "notes": ""
}
If a field is not mentioned, leave it as empty string."""
    raw = call_ai(system, f"Conversation:\n{conversation_text}", max_tokens=500)
    if not raw:
        return {}
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```")
    try:
        return json.loads(raw)
    except Exception:
        return {}


def save_user_profile(user_db_id, data):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM user_ai_profiles WHERE user_id=?", (user_db_id,)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE user_ai_profiles SET extracted_data=?, updated_at=? WHERE user_id=?",
                (json.dumps(data), now, user_db_id)
            )
        else:
            conn.execute(
                "INSERT INTO user_ai_profiles (user_id, extracted_data, updated_at) VALUES (?,?,?)",
                (user_db_id, json.dumps(data), now)
            )
        conn.commit()


UPLOADS_DIR = Path(__file__).resolve().parent.parent / "tg_bot" / "uploads"


def get_tg_file_url(file_id):
    if not file_id:
        return None
    # Files downloaded by the userbot are stored locally
    if file_id.startswith("local:"):
        filename = file_id[6:]
        return url_for("admin_local_file", filename=filename)
    if not BOT_TOKEN:
        return None
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id}, timeout=10
        )
        data = r.json()
        if data.get("ok"):
            fp = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    except Exception as e:
        print(f"[TG] file url error: {e}")
    return None


@app.route("/admin/files/local/<path:filename>")
@login_required
def admin_local_file(filename):
    """Serve a file that was downloaded by the userbot."""
    safe = UPLOADS_DIR / Path(filename).name   # prevent directory traversal
    if not safe.exists():
        return "File not found", 404
    return send_file(str(safe), as_attachment=False)


# ─────────────────────────── STATS & REPORTS ──────────────────────

def compute_stats(start_iso, end_iso):
    with get_db() as conn:
        def q(sql, *p):
            return conn.execute(sql, p).fetchone()[0]

        new_users     = q("SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?", start_iso, end_iso)
        new_cases     = q("SELECT COUNT(*) FROM cases WHERE created_at BETWEEN ? AND ?", start_iso, end_iso)
        paid          = q("SELECT COUNT(*) FROM cases WHERE payment_status='received' AND updated_at BETWEEN ? AND ?", start_iso, end_iso)
        completed     = q("SELECT COUNT(*) FROM cases WHERE status='completed' AND updated_at BETWEEN ? AND ?", start_iso, end_iso)
        active        = q("SELECT COUNT(*) FROM cases WHERE status='active'")
        docs          = q("""SELECT COUNT(*) FROM documents d
                              JOIN cases c ON d.case_id=c.id
                              WHERE d.created_at BETWEEN ? AND ?""", start_iso, end_iso)
        by_service    = conn.execute(
            "SELECT service, COUNT(*) cnt FROM cases WHERE created_at BETWEEN ? AND ? GROUP BY service",
            (start_iso, end_iso)
        ).fetchall()
    return {
        "new_users": new_users, "new_cases": new_cases,
        "paid": paid, "completed": completed, "active": active,
        "docs": docs,
        "by_service": {r["service"]: r["cnt"] for r in by_service},
    }


def generate_report(report_type):
    now = datetime.utcnow()
    delta = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1),
             "monthly": timedelta(days=30), "quarterly": timedelta(days=90)}
    label = {"daily": "last 24 hours", "weekly": "last 7 days",
             "monthly": "last 30 days", "quarterly": "last 90 days"}
    if report_type not in delta:
        return None
    start = (now - delta[report_type]).isoformat()
    end   = now.isoformat()
    stats = compute_stats(start, end)

    conclusion = None
    if OPENAI_API_KEY:
        system = """You are a business analyst for Brightway Consulting (UK immigration, tax, accounting).
Write a concise 2-3 paragraph professional summary of the period stats below.
Note any trends, highlight wins, identify potential issues, and give one actionable suggestion."""
        body = f"""Period: {label[report_type]}
New users: {stats['new_users']}
New cases: {stats['new_cases']}
Cases by service: {json.dumps(stats['by_service'])}
Payments received: {stats['paid']}
Completed cases: {stats['completed']}
Currently active cases: {stats['active']}
Documents uploaded: {stats['docs']}"""
        conclusion = call_ai(system, body, max_tokens=500)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO ai_reports (report_type,period_start,period_end,stats,ai_conclusion,created_at) VALUES (?,?,?,?,?,?)",
            (report_type, start, end, json.dumps(stats), conclusion, now.isoformat())
        )
        conn.commit()
    return {"stats": stats, "conclusion": conclusion, "period": label[report_type], "start": start, "end": end}


# ─────────────────────────── PUBLIC ROUTES ────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")


# ─────────────────────────── ADMIN AUTH ───────────────────────────

@app.route("/admin/notifications")
@login_required
def admin_notifications():
    admin_id = session.get("admin_id")
    if not admin_id:
        flash("Notifications are not available for the built-in master account.", "warning")
        return redirect(url_for("admin_dashboard"))
    with get_db() as conn:
        notifications = conn.execute(
            "SELECT * FROM notifications WHERE recipient_id=? ORDER BY created_at DESC LIMIT 50",
            (admin_id,)
        ).fetchall()
        conn.execute(
            "UPDATE notifications SET is_read=1 WHERE recipient_id=? AND is_read=0",
            (admin_id,)
        )
        conn.commit()
    return render_template("admin/notifications.html", notifications=notifications)


@app.route("/admin/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def admin_notif_read(notif_id):
    admin_id = session.get("admin_id")
    if admin_id:
        with get_db() as conn:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE id=? AND recipient_id=?",
                (notif_id, admin_id)
            )
            conn.commit()
    return jsonify({"ok": True})


@app.route("/admin/notifications/read-all", methods=["POST"])
@login_required
def admin_notif_read_all():
    admin_id = session.get("admin_id")
    if admin_id:
        with get_db() as conn:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE recipient_id=?",
                (admin_id,)
            )
            conn.commit()
    return redirect(url_for("admin_notifications"))


@app.route("/admin/notifications/preview")
@login_required
def admin_notif_preview():
    """Return 5 latest notifications as JSON for the dropdown."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return jsonify({"items": []})
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE recipient_id=? ORDER BY created_at DESC LIMIT 5",
            (admin_id,)
        ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@app.route("/admin/notifications/mark-preview-read", methods=["POST"])
@login_required
def admin_notif_mark_preview_read():
    """Mark all unread notifications as read (called silently after dropdown opens)."""
    admin_id = session.get("admin_id")
    if admin_id:
        with get_db() as conn:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE recipient_id=? AND is_read=0",
                (admin_id,)
            )
            conn.commit()
    return jsonify({"ok": True})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        ok, role, aid, display = check_admin_login(
            request.form.get("username", "").strip(),
            request.form.get("password", "").strip()
        )
        if ok:
            session["admin_logged_in"] = True
            session["admin_username"]  = request.form.get("username")
            session["admin_role"]      = role
            session["admin_id"]        = aid
            session["admin_display"]   = display
            flash(f"Welcome back, {display}!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


# ─────────────────────────── PROFILE ──────────────────────────────

@app.route("/admin/profile", methods=["GET", "POST"])
@login_required
def admin_profile():
    is_env_master = (session.get("admin_role") == "master" and session.get("admin_id") is None)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "display_name":
            new_name = request.form.get("display_name", "").strip()
            if not new_name:
                flash("Display name cannot be empty.", "error")
            elif is_env_master:
                # For .env master, just update the session display name
                session["admin_display"] = new_name
                flash("Display name updated.", "success")
            else:
                with get_db() as conn:
                    conn.execute(
                        "UPDATE admin_users SET display_name=? WHERE id=?",
                        (new_name, session["admin_id"])
                    )
                    conn.commit()
                session["admin_display"] = new_name
                flash("Display name updated.", "success")

        elif action == "username":
            if is_env_master:
                flash("The built-in admin username is set via the .env file (ADMIN_USERNAME).", "warning")
            else:
                new_username = request.form.get("new_username", "").strip()
                if not new_username:
                    flash("Username cannot be empty.", "error")
                elif len(new_username) < 3:
                    flash("Username must be at least 3 characters.", "error")
                elif new_username == session.get("admin_username"):
                    flash("That is already your current username.", "warning")
                else:
                    try:
                        old_username = session.get("admin_username")
                        actor_role   = session.get("admin_role")
                        actor_display = session.get("admin_display") or old_username
                        actor_id     = session.get("admin_id")
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE admin_users SET username=? WHERE id=?",
                                (new_username, actor_id)
                            )
                            conn.commit()
                        session["admin_username"] = new_username
                        flash(f"Username changed to '{new_username}'.", "success")
                        # Notify all DB masters about the change
                        notify_masters(
                            title="Username changed",
                            message=f"{actor_display} (@{old_username}) changed their username to @{new_username}.",
                            link=url_for("admin_notifications"),
                            exclude_id=actor_id if actor_role != "master" else None
                        )
                    except sqlite3.IntegrityError:
                        flash("That username is already taken.", "error")

        elif action == "password":
            if is_env_master:
                flash("Your password is set via the .env file on the server. Update ADMIN_PASSWORD there.", "warning")
            else:
                current  = request.form.get("current_password", "")
                new_pw   = request.form.get("new_password", "")
                confirm  = request.form.get("confirm_password", "")
                if not current or not new_pw or not confirm:
                    flash("All password fields are required.", "error")
                elif new_pw != confirm:
                    flash("New passwords do not match.", "error")
                elif len(new_pw) < 6:
                    flash("Password must be at least 6 characters.", "error")
                else:
                    with get_db() as conn:
                        row = conn.execute(
                            "SELECT password_hash FROM admin_users WHERE id=?",
                            (session["admin_id"],)
                        ).fetchone()
                        if not row or not check_password_hash(row["password_hash"], current):
                            flash("Current password is incorrect.", "error")
                        else:
                            conn.execute(
                                "UPDATE admin_users SET password_hash=? WHERE id=?",
                                (generate_password_hash(new_pw), session["admin_id"])
                            )
                            conn.commit()
                            flash("Password changed successfully.", "success")

        return redirect(url_for("admin_profile"))

    # GET — load current data
    profile_data = {
        "username":     session.get("admin_username", "admin"),
        "display_name": session.get("admin_display") or session.get("admin_username", "admin"),
        "role":         session.get("admin_role", "consultant"),
    }
    if not is_env_master and session.get("admin_id"):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM admin_users WHERE id=?", (session["admin_id"],)
            ).fetchone()
            if row:
                profile_data["username"]     = row["username"]
                profile_data["display_name"] = row["display_name"] or row["username"]
                profile_data["created_at"]   = row["created_at"][:10] if row["created_at"] else "—"

    return render_template("admin/profile.html",
        profile=profile_data,
        is_env_master=is_env_master,
        is_master=session.get("admin_role") == "master"
    )


# ─────────────────────────── DASHBOARD ────────────────────────────

@app.route("/admin")
@login_required
def admin_dashboard():
    is_master = session.get("admin_role") == "master"
    elevated  = is_elevated()
    with get_db() as conn:
        total_users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_cases  = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        active_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE status='active'").fetchone()[0]
        paid_cases   = conn.execute("SELECT COUNT(*) FROM cases WHERE payment_status='received'").fetchone()[0]
        by_service   = conn.execute("SELECT service, COUNT(*) cnt FROM cases GROUP BY service").fetchall()

        recent_query = """
            SELECT c.id, c.service, c.status, c.payment_status, c.created_at, u.tg_id, u.id as user_db_id
            FROM cases c JOIN users u ON c.user_id=u.id
        """
        if not elevated:
            admin_id = session.get("admin_id")
            recent_query += f" WHERE u.id IN (SELECT user_id FROM admin_assignments WHERE admin_id={admin_id or 0})"
        recent_query += " ORDER BY c.created_at DESC LIMIT 10"
        recent_cases = conn.execute(recent_query).fetchall()

        # Assigned users count for consultants; all for elevated
        if elevated:
            my_users_count = total_users
        else:
            my_users_count = conn.execute(
                "SELECT COUNT(*) FROM admin_assignments WHERE admin_id=?",
                (session.get("admin_id"),)
            ).fetchone()[0]

        # Latest report
        latest_report = conn.execute(
            "SELECT * FROM ai_reports ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    return render_template("admin/dashboard.html",
        total_users=total_users, total_cases=total_cases,
        active_cases=active_cases, paid_cases=paid_cases,
        by_service=by_service, recent_cases=recent_cases,
        my_users_count=my_users_count, latest_report=latest_report,
        is_master=is_master, is_elevated=elevated)


# ─────────────────────────── CASES ────────────────────────────────

@app.route("/admin/cases")
@login_required
def admin_cases():
    is_master = session.get("admin_role") == "master"
    elevated  = is_elevated()
    service = request.args.get("service", "")
    status  = request.args.get("status", "")
    payment = request.args.get("payment", "")

    query = """
        SELECT c.id, c.service, c.status, c.payment_status, c.created_at, c.updated_at,
               u.tg_id, u.language, u.id as user_db_id
        FROM cases c JOIN users u ON c.user_id=u.id WHERE 1=1
    """
    params = []
    if not elevated:
        admin_id = session.get("admin_id")
        query += f" AND u.id IN (SELECT user_id FROM admin_assignments WHERE admin_id=?)"
        params.append(admin_id)
    if service:
        query += " AND c.service=?"; params.append(service)
    if status:
        query += " AND c.status=?";  params.append(status)
    if payment:
        query += " AND c.payment_status=?"; params.append(payment)
    query += " ORDER BY c.created_at DESC"

    with get_db() as conn:
        cases = conn.execute(query, params).fetchall()
    return render_template("admin/cases.html", cases=cases,
        filter_service=service, filter_status=status, filter_payment=payment,
        is_master=is_master, is_elevated=elevated)


@app.route("/admin/cases/<int:case_id>")
@login_required
def admin_case_detail(case_id):
    with get_db() as conn:
        case = conn.execute("""
            SELECT c.*, u.tg_id, u.language, u.id as user_db_id
            FROM cases c JOIN users u ON c.user_id=u.id WHERE c.id=?
        """, (case_id,)).fetchone()
        if not case:
            flash("Case not found.", "error")
            return redirect(url_for("admin_cases"))
        if not can_view_user(case["user_db_id"]):
            flash("Access denied.", "error")
            return redirect(url_for("admin_cases"))

        try:
            conversation = json.loads(case["conversation_history"] or "[]")
        except (IndexError, KeyError, TypeError):
            conversation = []
        documents    = conn.execute(
            "SELECT * FROM documents WHERE case_id=? ORDER BY created_at ASC", (case_id,)
        ).fetchall()

        # Resolve file URLs for inline view
        docs_with_url = []
        # Also build lookup dicts for in-chat file rendering
        docs_by_unique_id = {}   # file_unique_id -> {doc, url}
        docs_by_filename   = {}  # filename -> {doc, url}  (fallback for old format)
        for doc in documents:
            url = get_tg_file_url(doc["file_id"])
            entry = {"doc": doc, "url": url}
            docs_with_url.append(entry)
            docs_by_unique_id[doc["file_unique_id"]] = entry
            fname = doc["filename"] or doc["doc_type"] or ""
            if fname and fname not in docs_by_filename:
                docs_by_filename[fname] = entry

    return render_template("admin/case_detail.html",
        case=case, conversation=conversation,
        docs_with_url=docs_with_url,
        docs_by_unique_id=docs_by_unique_id,
        docs_by_filename=docs_by_filename,
        is_master=session.get("admin_role")=="master")


@app.route("/admin/cases/<int:case_id>/update", methods=["POST"])
@login_required
def admin_case_update(case_id):
    with get_db() as conn:
        case = conn.execute("SELECT user_id FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case or not can_view_user(case["user_id"]):
            flash("Access denied.", "error")
            return redirect(url_for("admin_cases"))
        now = datetime.utcnow().isoformat()
        status  = request.form.get("status")
        payment = request.form.get("payment_status")
        if status:
            conn.execute("UPDATE cases SET status=?, updated_at=? WHERE id=?", (status, now, case_id))
        if payment:
            conn.execute("UPDATE cases SET payment_status=?, updated_at=? WHERE id=?", (payment, now, case_id))
        conn.commit()
    flash("Case updated.", "success")
    return redirect(url_for("admin_case_detail", case_id=case_id))


# ─────────────────────────── FILES ────────────────────────────────

@app.route("/admin/files/view/<file_id>")
@login_required
def admin_file_view(file_id):
    """Proxy a Telegram file inline (for images)."""
    url = get_tg_file_url(file_id)
    if not url:
        return "File not available", 404
    try:
        r = requests.get(url, timeout=30, stream=True)
        ct = r.headers.get("Content-Type", "application/octet-stream")
        return Response(r.iter_content(8192), content_type=ct)
    except Exception as e:
        return f"Error: {e}", 500


@app.route("/admin/files/download/<file_id>")
@login_required
def admin_file_download(file_id):
    """Proxy a Telegram file as a download."""
    filename = request.args.get("name", "file")
    url = get_tg_file_url(file_id)
    if not url:
        return "File not available", 404
    try:
        r = requests.get(url, timeout=30)
        from io import BytesIO
        return send_file(BytesIO(r.content),
                         download_name=filename,
                         as_attachment=True,
                         mimetype=r.headers.get("Content-Type", "application/octet-stream"))
    except Exception as e:
        return f"Error: {e}", 500


# ─────────────────────────── USERS & PROFILES ─────────────────────

@app.route("/admin/users")
@login_required
def admin_users():
    is_master = session.get("admin_role") == "master"
    elevated  = is_elevated()
    with get_db() as conn:
        if elevated:
            users = conn.execute("""
                SELECT u.id, u.tg_id, u.language, u.created_at,
                       COUNT(DISTINCT c.id) case_count,
                       COUNT(DISTINCT d.id) doc_count,
                       p.extracted_data
                FROM users u
                LEFT JOIN cases c ON u.id=c.user_id
                LEFT JOIN documents d ON c.id=d.case_id
                LEFT JOIN user_ai_profiles p ON u.id=p.user_id
                GROUP BY u.id ORDER BY u.created_at DESC
            """).fetchall()
        else:
            admin_id = session.get("admin_id")
            users = conn.execute("""
                SELECT u.id, u.tg_id, u.language, u.created_at,
                       COUNT(DISTINCT c.id) case_count,
                       COUNT(DISTINCT d.id) doc_count,
                       p.extracted_data
                FROM users u
                JOIN admin_assignments aa ON u.id=aa.user_id AND aa.admin_id=?
                LEFT JOIN cases c ON u.id=c.user_id
                LEFT JOIN documents d ON c.id=d.case_id
                LEFT JOIN user_ai_profiles p ON u.id=p.user_id
                GROUP BY u.id ORDER BY u.created_at DESC
            """, (admin_id,)).fetchall()
    return render_template("admin/users.html", users=users, is_master=is_master, is_elevated=elevated)


@app.route("/admin/users/<int:user_db_id>")
@login_required
def admin_user_profile(user_db_id):
    if not can_view_user(user_db_id):
        flash("Access denied.", "error")
        return redirect(url_for("admin_users"))

    with get_db() as conn:
        user  = conn.execute("SELECT * FROM users WHERE id=?", (user_db_id,)).fetchone()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("admin_users"))

        cases = conn.execute(
            "SELECT * FROM cases WHERE user_id=? ORDER BY created_at ASC", (user_db_id,)
        ).fetchall()

        all_docs = conn.execute("""
            SELECT d.*, c.service FROM documents d
            JOIN cases c ON d.case_id=c.id
            WHERE c.user_id=? ORDER BY d.created_at ASC
        """, (user_db_id,)).fetchall()

        profile_row = conn.execute(
            "SELECT * FROM user_ai_profiles WHERE user_id=?", (user_db_id,)
        ).fetchone()

        all_admins = conn.execute(
            "SELECT id, username, display_name, role FROM admin_users ORDER BY role, username"
        ).fetchall()

        assignments = conn.execute("""
            SELECT a.id, a.username, a.display_name, a.role
            FROM admin_users a
            JOIN admin_assignments aa ON a.id=aa.admin_id
            WHERE aa.user_id=?
        """, (user_db_id,)).fetchall()

    profile = {}
    if profile_row:
        try:
            profile = json.loads(profile_row["extracted_data"] or "{}")
        except Exception:
            pass

    docs_with_url = []
    all_docs_by_unique_id = {}
    all_docs_by_filename  = {}
    for d in all_docs:
        url   = get_tg_file_url(d["file_id"])
        entry = {"doc": d, "url": url}
        docs_with_url.append(entry)
        all_docs_by_unique_id[d["file_unique_id"]] = entry
        fname = d["filename"] or d["doc_type"] or ""
        if fname and fname not in all_docs_by_filename:
            all_docs_by_filename[fname] = entry

    return render_template("admin/user_profile.html",
        user=user, cases=cases, docs_with_url=docs_with_url,
        profile=profile, profile_updated=profile_row["updated_at"] if profile_row else None,
        is_master=session.get("admin_role")=="master",
        is_elevated=is_elevated(),
        all_admins=all_admins, assignments=assignments,
        all_docs_by_unique_id=all_docs_by_unique_id,
        all_docs_by_filename=all_docs_by_filename)


@app.route("/admin/users/<int:user_db_id>/send", methods=["POST"])
@login_required
def admin_send_message(user_db_id):
    if not can_view_user(user_db_id):
        return jsonify({"error": "Access denied"}), 403

    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400

    ts         = datetime.utcnow().isoformat()
    admin_name = session.get("admin_display") or session.get("admin_username", "Admin")

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_db_id,)).fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Queue delivery via userbot (personal account)
        conn.execute(
            """INSERT INTO pending_sends (user_tg_id, message, sender_name, sent, created_at)
               VALUES (?, ?, ?, 0, ?)""",
            (str(user["tg_id"]), text, admin_name, ts),
        )

        # Save to the most recent case's conversation history
        case = conn.execute(
            "SELECT * FROM cases WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_db_id,)
        ).fetchone()

        if case:
            conv = []
            try:
                conv = json.loads(case["conversation_history"] or "[]")
            except Exception:
                pass
            conv.append({"role": "admin", "content": text, "timestamp": ts, "sender": admin_name})
            conn.execute(
                "UPDATE cases SET conversation_history=?, updated_at=? WHERE id=?",
                (json.dumps(conv), ts, case["id"])
            )

        conn.commit()

    return jsonify({"ok": True, "tg_sent": True, "timestamp": ts[:16].replace("T", " "), "sender": admin_name})


@app.route("/admin/users/<int:user_db_id>/poll")
@login_required
def admin_poll_messages(user_db_id):
    """Return all messages newer than ?since=<ISO timestamp>."""
    if not can_view_user(user_db_id):
        return jsonify({"error": "Access denied"}), 403

    since = request.args.get("since", "")  # ISO string, may be empty

    with get_db() as conn:
        cases = conn.execute(
            "SELECT * FROM cases WHERE user_id=? ORDER BY created_at ASC", (user_db_id,)
        ).fetchall()

    new_msgs = []
    for case in cases:
        try:
            conv = json.loads(case["conversation_history"] or "[]")
        except Exception:
            continue
        for msg in conv:
            ts = msg.get("timestamp", "")
            if not since or ts > since:
                new_msgs.append({
                    "role":      msg.get("role", "user"),
                    "content":   msg.get("content", ""),
                    "timestamp": ts,
                    "sender":    msg.get("sender", ""),
                    "case_id":   case["id"],
                })

    # Sort by timestamp
    new_msgs.sort(key=lambda m: m["timestamp"])
    return jsonify({"messages": new_msgs})


@app.route("/admin/users/<int:user_db_id>/extract-profile", methods=["POST"])
@login_required
def admin_extract_profile(user_db_id):
    if not can_view_user(user_db_id):
        return jsonify({"error": "Access denied"}), 403
    if not OPENAI_API_KEY:
        flash("OpenAI API key not set — cannot extract profile.", "error")
        return redirect(url_for("admin_user_profile", user_db_id=user_db_id))
    data = extract_user_profile(user_db_id)
    save_user_profile(user_db_id, data)
    flash("Profile extracted successfully by AI.", "success")
    return redirect(url_for("admin_user_profile", user_db_id=user_db_id))


@app.route("/admin/users/<int:user_db_id>/assign", methods=["POST"])
@master_required
def admin_assign_user(user_db_id):
    admin_id = request.form.get("admin_id", type=int)
    action   = request.form.get("action", "assign")
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        if action == "assign":
            try:
                conn.execute(
                    "INSERT INTO admin_assignments (admin_id, user_id, assigned_at) VALUES (?,?,?)",
                    (admin_id, user_db_id, now)
                )
                conn.commit()
                flash("User assigned.", "success")
            except sqlite3.IntegrityError:
                flash("Already assigned.", "warning")
        else:
            conn.execute(
                "DELETE FROM admin_assignments WHERE admin_id=? AND user_id=?",
                (admin_id, user_db_id)
            )
            conn.commit()
            flash("Assignment removed.", "success")
    return redirect(url_for("admin_user_profile", user_db_id=user_db_id))


# ─────────────────────────── ADMIN MANAGEMENT ─────────────────────

@app.route("/admin/admins")
@master_required
def admin_admins():
    with get_db() as conn:
        admins = conn.execute("""
            SELECT a.*, COUNT(aa.user_id) as assigned_count
            FROM admin_users a
            LEFT JOIN admin_assignments aa ON a.id=aa.admin_id
            GROUP BY a.id ORDER BY a.created_at DESC
        """).fetchall()
        all_users = conn.execute("""
            SELECT u.id, u.tg_id, u.language,
                   p.extracted_data
            FROM users u
            LEFT JOIN user_ai_profiles p ON u.id=p.user_id
            ORDER BY u.created_at DESC
        """).fetchall()
    return render_template("admin/admins.html", admins=admins, all_users=all_users)


@app.route("/admin/admins/add", methods=["POST"])
@master_required
def admin_add_admin():
    username     = request.form.get("username", "").strip()
    password     = request.form.get("password", "").strip()
    display_name = request.form.get("display_name", "").strip()
    role         = request.form.get("role", "consultant")
    if not username or not password:
        flash("Username and password required.", "error")
        return redirect(url_for("admin_admins"))
    pw_hash = generate_password_hash(password)
    now = datetime.utcnow().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, display_name, role, created_at) VALUES (?,?,?,?,?)",
                (username, pw_hash, display_name or username, role, now)
            )
            conn.commit()
        flash(f"Admin '{username}' created.", "success")
    except sqlite3.IntegrityError:
        flash("Username already exists.", "error")
    return redirect(url_for("admin_admins"))


@app.route("/admin/admins/<int:admin_id>/delete", methods=["POST"])
@master_required
def admin_delete_admin(admin_id):
    with get_db() as conn:
        conn.execute("DELETE FROM admin_assignments WHERE admin_id=?", (admin_id,))
        conn.execute("DELETE FROM admin_users WHERE id=?", (admin_id,))
        conn.commit()
    flash("Admin deleted.", "success")
    return redirect(url_for("admin_admins"))


# ─────────────────────────── REPORTS ──────────────────────────────

@app.route("/admin/reports")
@elevated_required
def admin_reports():
    with get_db() as conn:
        reports = conn.execute(
            "SELECT * FROM ai_reports ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    now = datetime.utcnow()
    today_stats = compute_stats((now - timedelta(days=1)).isoformat(), now.isoformat())
    return render_template("admin/reports.html", reports=reports, today_stats=today_stats,
                           is_master=session.get("admin_role")=="master")


@app.route("/admin/reports/generate/<report_type>", methods=["POST"])
@elevated_required
def admin_generate_report(report_type):
    result = generate_report(report_type)
    if result:
        flash(f"{report_type.capitalize()} report generated.", "success")
    else:
        flash("Failed to generate report.", "error")
    return redirect(url_for("admin_reports"))


@app.route("/admin/reports/<int:report_id>")
@elevated_required
def admin_report_detail(report_id):
    with get_db() as conn:
        report = conn.execute("SELECT * FROM ai_reports WHERE id=?", (report_id,)).fetchone()
    if not report:
        flash("Report not found.", "error")
        return redirect(url_for("admin_reports"))
    stats = json.loads(report["stats"] or "{}")
    return render_template("admin/report_detail.html", report=report, stats=stats)


# ─────────────────────────── MAIN ─────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"Starting Brightway web app...")
    print(f"Database:   {DB_PATH}")
    print(f"Bot token:  {'✓' if BOT_TOKEN else '✗ missing'}")
    print(f"OpenAI key: {'✓' if OPENAI_API_KEY else '✗ missing'}")
    print(f"\n🌐  http://127.0.0.1:{port}/")
    print(f"🔐  http://127.0.0.1:{port}/admin/login\n")
    app.run(debug=True, host="0.0.0.0", port=port)
