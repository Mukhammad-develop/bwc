"""Shared helpers used across panel views."""
import json
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path

import requests as _requests
from django.conf import settings
from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from openai import OpenAI

from core.models import AdminUser

# ── Audio helpers ─────────────────────────────────────────────────────────────
_WHISPER_SUPPORTED_EXT = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")
_VOICE_EXTENSIONS      = (".oga", ".ogg", ".mp3", ".m4a", ".webm")


def mimetype_for(filename):
    if not filename:
        return None
    mt, _ = mimetypes.guess_type(filename)
    if mt:
        return mt
    ext = (Path(filename).suffix or "").lower()
    if ext in (".oga", ".ogg"):
        return "audio/ogg"
    if ext == ".m4a":
        return "audio/mp4"
    if ext == ".webm":
        return "audio/webm"
    return None


def is_voice_doc(doc):
    if not doc:
        return False
    if hasattr(doc, "media_type"):
        if (doc.media_type or "").lower() == "voice":
            return True
        fname = (doc.filename or doc.doc_type or "").lower()
    else:
        d = dict(doc) if hasattr(doc, "keys") else doc
        if (d.get("media_type") or "").lower() == "voice":
            return True
        fname = (d.get("filename") or d.get("doc_type") or "").lower()
    return fname.endswith(_VOICE_EXTENSIONS)


def convert_audio_to_wav(data: bytes, input_ext: str):
    if not data:
        return None
    ext = (input_ext or "").lower()
    if not ext.startswith("."):
        ext = "." + ext
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as fin:
            fin.write(data)
            in_path = fin.name
        out_path = in_path + ".wav"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", in_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out_path],
                check=True, capture_output=True, timeout=60,
            )
            if os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    out_data = f.read()
                os.unlink(out_path)
                return (out_data, "audio.wav")
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return None


# ── Telegram file helpers ─────────────────────────────────────────────────────

def get_tg_file_url(file_id, request=None):
    if not file_id:
        return None
    if file_id.startswith("local:"):
        filename = file_id[6:]
        from django.urls import reverse
        return reverse("panel:local_file", args=[filename])
    token = settings.BOT_TOKEN
    if not token:
        return None
    try:
        r = _requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id}, timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            return f"https://api.telegram.org/file/bot{token}/{data['result']['file_path']}"
    except Exception as e:
        print(f"[TG] file url error: {e}")
    return None


def serve_local_file(filename, as_attachment=False, download_name=None):
    safe = settings.UPLOADS_DIR / Path(filename).name
    if not safe.exists():
        return None
    mt = mimetype_for(filename)
    if as_attachment:
        response = FileResponse(open(safe, "rb"), as_attachment=True, filename=download_name or safe.name)
    else:
        response = FileResponse(open(safe, "rb"), content_type=mt or "application/octet-stream")
    return response


def proxy_tg_file(file_id, as_attachment=False, download_name=None):
    url = get_tg_file_url(file_id)
    if not url:
        return None
    try:
        r = _requests.get(url, timeout=30, stream=True)
        ct = r.headers.get("Content-Type", "application/octet-stream")
        if as_attachment:
            resp = StreamingHttpResponse(r.iter_content(8192), content_type=ct)
            resp["Content-Disposition"] = f'attachment; filename="{download_name or "file"}"'
        else:
            resp = StreamingHttpResponse(r.iter_content(8192), content_type=ct)
        return resp
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=500)


# ── AI helpers ────────────────────────────────────────────────────────────────

def call_ai(system_prompt, user_content, max_tokens=800):
    key = settings.OPENAI_API_KEY
    if not key:
        return None
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            max_tokens=max_tokens, temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[AI] {type(e).__name__}: {e}")
        return None


def extract_user_profile(user_obj):
    cases = list(user_obj.cases.all())
    if not cases:
        return {}
    lines = []
    for case in cases:
        msgs = case.get_conversation()
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


# ── Stats helpers ─────────────────────────────────────────────────────────────

def compute_stats(start, end):
    from django.utils import timezone
    from datetime import datetime
    from core.models import TgUser, Case, Document

    new_users   = TgUser.objects.filter(created_at__range=(start, end)).count()
    new_cases   = Case.objects.filter(created_at__range=(start, end)).count()
    paid        = Case.objects.filter(payment_status="received", updated_at__range=(start, end)).count()
    completed   = Case.objects.filter(status="completed", updated_at__range=(start, end)).count()
    active      = Case.objects.filter(status="active").count()
    docs        = Document.objects.filter(created_at__range=(start, end)).count()
    from django.db.models import Count
    by_service  = (
        Case.objects.filter(created_at__range=(start, end))
        .values("service").annotate(cnt=Count("id"))
    )
    return {
        "new_users": new_users,
        "new_cases": new_cases,
        "paid": paid,
        "completed": completed,
        "active": active,
        "docs": docs,
        "by_service": {r["service"]: r["cnt"] for r in by_service},
    }


# ── Password helpers ──────────────────────────────────────────────────────────

def check_password(stored_hash, password):
    from django.contrib.auth.hashers import check_password as _check
    return _check(password, stored_hash)


def hash_password(password):
    from django.contrib.auth.hashers import make_password
    return make_password(password)


# ── Notification helpers ──────────────────────────────────────────────────────

def notify_masters(title, message, link=None, exclude_id=None):
    from core.models import AdminUser, Notification
    from django.utils import timezone
    masters = AdminUser.objects.filter(role="master")
    if exclude_id:
        masters = masters.exclude(pk=exclude_id)
    for m in masters:
        Notification.objects.create(recipient=m, title=title, message=message, link=link or "")


def get_unread_count(admin_id):
    from core.models import Notification
    if not admin_id:
        return 0
    return Notification.objects.filter(recipient_id=admin_id, is_read=False).count()


# ── Session helpers ───────────────────────────────────────────────────────────

def get_current_admin(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    try:
        return AdminUser.objects.get(pk=admin_id)
    except AdminUser.DoesNotExist:
        return None


def session_ctx(request):
    """Context dict injected into all templates."""
    admin_id = request.session.get("admin_id")
    return {
        "session_admin_logged_in": request.session.get("admin_logged_in", False),
        "session_admin_role":      request.session.get("admin_role", ""),
        "session_admin_username":  request.session.get("admin_username", ""),
        "session_admin_display":   request.session.get("admin_display", ""),
        "session_admin_id":        admin_id,
        "unread_notifications":    get_unread_count(admin_id),
    }


def is_elevated(request):
    return request.session.get("admin_role") in ("master", "admin")


def can_view_user(request, user_db_id):
    from core.models import AdminAssignment
    role = request.session.get("admin_role")
    if role in ("master", "admin"):
        return True
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return False
    return AdminAssignment.objects.filter(admin_id=admin_id, user_id=user_db_id).exists()


def check_admin_login(username, password):
    """Returns (ok, role, admin_id, display_name)."""
    master_u = os.getenv("ADMIN_USERNAME", "admin")
    master_p = os.getenv("ADMIN_PASSWORD", "admin123")
    if username == master_u and password == master_p:
        return True, "master", None, "Master Admin"
    try:
        row = AdminUser.objects.get(username=username)
        if check_password(row.password_hash, password):
            return True, row.role, row.pk, row.display_name or username
    except AdminUser.DoesNotExist:
        pass
    return False, None, None, None
