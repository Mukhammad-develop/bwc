import json
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from panel.decorators import login_required, master_required
from .helpers import (
    session_ctx, is_elevated, can_view_user, get_tg_file_url,
    is_voice_doc, extract_user_profile, call_ai,
)
from core.models import (
    TgUser, Case, Document, AdminUser, AdminAssignment,
    UserAiProfile, PendingSend, ClientNote,
    ServiceDefinition, CaseProgress,
)


def _dedupe_conv(conv):
    out = []
    for m in conv:
        if (out
                and out[-1].get("role") == m.get("role")
                and out[-1].get("content") == m.get("content")
                and out[-1].get("timestamp") == m.get("timestamp")):
            continue
        out.append(m)
    return out


@login_required
def users_list(request):
    elevated = is_elevated(request)
    from django.db.models import Count, OuterRef, Subquery
    from core.models import UserAiProfile

    qs = TgUser.objects.annotate(
        case_count=Count("cases", distinct=True),
        doc_count=Count("cases__documents", distinct=True),
    ).order_by("-created_at")

    if not elevated:
        admin_id = request.session.get("admin_id")
        assigned = AdminAssignment.objects.filter(admin_id=admin_id).values_list("user_id", flat=True)
        qs = qs.filter(pk__in=assigned)

    users_with_profile = []
    for u in qs:
        try:
            profile_data = json.loads(u.ai_profile.extracted_data or "{}")
        except Exception:
            profile_data = {}
        users_with_profile.append({"user": u, "profile": profile_data})

    ctx = session_ctx(request)
    ctx.update({
        "users":       users_with_profile,
        "is_master":   request.session.get("admin_role") == "master",
        "is_elevated": elevated,
    })
    return render(request, "panel/users.html", ctx)


@login_required
def user_profile(request, user_db_id):
    if not can_view_user(request, user_db_id):
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:users"))

    user = get_object_or_404(TgUser, pk=user_db_id)
    raw_cases = list(Case.objects.filter(user=user).order_by("created_at"))
    cases = []
    for c in raw_cases:
        try:
            conv = json.loads(c.conversation_history or "[]")
        except Exception:
            conv = []
        c.conversation_history = json.dumps(_dedupe_conv(conv))
        cases.append(c)

    all_docs = Document.objects.filter(case__user=user).select_related("case").order_by("created_at")
    docs_with_url     = []
    all_docs_by_uid   = {}
    all_docs_by_fname = {}
    for d in all_docs:
        url   = get_tg_file_url(d.file_id)
        entry = {"doc": d, "url": url}
        docs_with_url.append(entry)
        all_docs_by_uid[d.file_unique_id] = entry
        fname = d.filename or d.doc_type or ""
        if fname and fname not in all_docs_by_fname:
            all_docs_by_fname[fname] = entry
    docs_for_files = [e for e in docs_with_url if not is_voice_doc(e["doc"])]

    profile = {}
    profile_updated = None
    try:
        ai_p = user.ai_profile
        profile = json.loads(ai_p.extracted_data or "{}")
        profile_updated = str(ai_p.updated_at)[:16]
    except UserAiProfile.DoesNotExist:
        pass

    all_admins  = list(AdminUser.objects.order_by("role", "username"))
    assignments = list(
        AdminUser.objects.filter(assignments__user=user).order_by("role", "username")
    )

    profile_fields = [
        ("Nationality",          profile.get("nationality")),
        ("Country of Residence", profile.get("country_of_residence")),
        ("Phone",                profile.get("phone")),
        ("Email",                profile.get("email")),
        ("Age",                  profile.get("age")),
        ("Service Interest",     profile.get("service_interest")),
        ("UK Visa Status",       profile.get("uk_visa_status")),
        ("Employment Type",      profile.get("employment_type")),
        ("Budget",               profile.get("budget")),
        ("Urgency",              profile.get("urgency")),
    ]

    # Client notes
    notes = list(ClientNote.objects.filter(user=user).select_related("author").order_by("-created_at"))

    # Per-case progress data
    case_progress_data = {}
    for c in cases:
        try:
            sdef  = ServiceDefinition.objects.get(slug=c.service, is_active=True)
            steps = list(sdef.steps.all())
        except ServiceDefinition.DoesNotExist:
            sdef  = None
            steps = []
        try:
            prog = c.progress
            current_step_id = prog.current_step_id
        except CaseProgress.DoesNotExist:
            current_step_id = None
        current_idx = next((i for i, s in enumerate(steps) if s.pk == current_step_id), -1)
        case_progress_data[c.pk] = {
            "sdef": sdef, "steps": steps,
            "current_step_id": current_step_id, "current_idx": current_idx,
        }

    ctx = session_ctx(request)
    ctx.update({
        "user":                 user,
        "cases":                cases,
        "docs_with_url":        docs_with_url,
        "docs_for_files":       docs_for_files,
        "profile":              profile,
        "profile_fields":       profile_fields,
        "profile_updated":      profile_updated,
        "is_master":            request.session.get("admin_role") == "master",
        "is_elevated":          is_elevated(request),
        "all_admins":           all_admins,
        "assignments":          assignments,
        "all_docs_by_unique_id": all_docs_by_uid,
        "all_docs_by_filename": all_docs_by_fname,
        "notes":                notes,
        "case_progress_data":   case_progress_data,
        "current_admin_id":     request.session.get("admin_id"),
        "current_admin_role":   request.session.get("admin_role"),
    })
    return render(request, "panel/user_profile.html", ctx)


@login_required
def send_message(request, user_db_id):
    if not can_view_user(request, user_db_id):
        return JsonResponse({"error": "Access denied"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    import json as _json
    body = _json.loads(request.body or b"{}")
    text = (body.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "Empty message"}, status=400)

    ts         = datetime.utcnow().isoformat()
    admin_name = request.session.get("admin_display") or request.session.get("admin_username", "Admin")

    user = get_object_or_404(TgUser, pk=user_db_id)
    account_index = user.linked_account if user.linked_account in (0, 1) else 0

    PendingSend.objects.create(
        user_tg_id=str(user.tg_id),
        message=text,
        sender_name=admin_name,
        account_index=account_index,
        created_at=ts,
    )

    case = Case.objects.filter(user=user).order_by("-id").first()
    if case:
        conv = case.get_conversation()
        conv.append({"role": "admin", "content": text, "timestamp": ts, "sender": admin_name})
        case.set_conversation(conv)
        case.save(update_fields=["conversation_history", "updated_at"])

    return JsonResponse({
        "ok": True,
        "tg_sent": True,
        "timestamp": ts[:16].replace("T", " "),
        "sender": admin_name,
    })


@login_required
def poll_messages(request, user_db_id):
    if not can_view_user(request, user_db_id):
        return JsonResponse({"error": "Access denied"}, status=403)

    since = request.GET.get("since", "")
    cases = list(Case.objects.filter(user_id=user_db_id).order_by("created_at"))

    new_msgs = []
    for case in cases:
        try:
            conv = json.loads(case.conversation_history or "[]")
        except Exception:
            continue
        for msg in conv:
            ts = msg.get("timestamp", "")
            if not since or ts > since:
                new_msgs.append({
                    "role":    msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": ts,
                    "sender":  msg.get("sender", ""),
                    "case_id": case.pk,
                })

    new_msgs.sort(key=lambda m: m["timestamp"])

    unique_ids = set()
    for m in new_msgs:
        c = m.get("content", "") or ""
        if c.startswith("[FILE:") and ":" in c[6:]:
            parts = c[6:].split(":")
            if parts:
                unique_ids.add(parts[0])

    file_docs = {}
    if unique_ids and cases:
        case_ids = [c.pk for c in cases]
        rows = Document.objects.filter(case_id__in=case_ids, file_unique_id__in=unique_ids)
        for row in rows:
            file_docs[row.file_unique_id] = {
                "id":            row.pk,
                "file_id":       row.file_id,
                "filename":      row.filename or "",
                "transcription": row.transcription or "",
            }

    return JsonResponse({"messages": new_msgs, "file_docs": file_docs})


@login_required
def extract_profile(request, user_db_id):
    if request.method != "POST":
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    if not can_view_user(request, user_db_id):
        return JsonResponse({"error": "Access denied"}, status=403)
    from django.conf import settings
    if not settings.OPENAI_API_KEY:
        messages.error(request, "OpenAI API key not set.")
        return redirect(reverse("panel:user_profile", args=[user_db_id]))

    user = get_object_or_404(TgUser, pk=user_db_id)
    data = extract_user_profile(user)
    ai_p, _ = UserAiProfile.objects.get_or_create(user=user)
    ai_p.extracted_data = json.dumps(data)
    ai_p.save()
    messages.success(request, "Profile extracted by AI.")
    return redirect(reverse("panel:user_profile", args=[user_db_id]))


@master_required
def assign_user(request, user_db_id):
    if request.method != "POST":
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    admin_id = request.POST.get("admin_id", type=int) or request.POST.get("admin_id")
    action   = request.POST.get("action", "assign")
    user     = get_object_or_404(TgUser, pk=user_db_id)
    if action == "assign":
        AdminAssignment.objects.get_or_create(admin_id=admin_id, user=user)
        messages.success(request, "User assigned.")
    else:
        AdminAssignment.objects.filter(admin_id=admin_id, user=user).delete()
        messages.success(request, "Assignment removed.")
    return redirect(reverse("panel:user_profile", args=[user_db_id]))


# ── Client Notes ──────────────────────────────────────────────────────────────

@login_required
def note_add(request, user_db_id):
    if request.method != "POST":
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    if not can_view_user(request, user_db_id):
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:users"))
    body = request.POST.get("body", "").strip()
    if not body:
        messages.error(request, "Note cannot be empty.")
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    user      = get_object_or_404(TgUser, pk=user_db_id)
    author_id = request.session.get("admin_id")
    author    = AdminUser.objects.filter(pk=author_id).first() if author_id else None
    ClientNote.objects.create(user=user, author=author, body=body)
    messages.success(request, "Note added.")
    return redirect(reverse("panel:user_profile", args=[user_db_id]) + "#notes")


@login_required
def note_edit(request, user_db_id, note_id):
    if request.method != "POST":
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    note = get_object_or_404(ClientNote, pk=note_id, user_id=user_db_id)
    admin_id = request.session.get("admin_id")
    role     = request.session.get("admin_role")
    is_own   = admin_id and note.author_id == admin_id
    if not is_own and role not in ("master", "admin"):
        messages.error(request, "You can only edit your own notes.")
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    body = request.POST.get("body", "").strip()
    if body:
        note.body = body
        note.save(update_fields=["body", "updated_at"])
        messages.success(request, "Note updated.")
    return redirect(reverse("panel:user_profile", args=[user_db_id]) + "#notes")


@login_required
def note_delete(request, user_db_id, note_id):
    if request.method != "POST":
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    note = get_object_or_404(ClientNote, pk=note_id, user_id=user_db_id)
    admin_id = request.session.get("admin_id")
    role     = request.session.get("admin_role")
    is_own   = admin_id and note.author_id == admin_id
    if not is_own and role not in ("master", "admin"):
        messages.error(request, "You can only delete your own notes.")
        return redirect(reverse("panel:user_profile", args=[user_db_id]))
    note.delete()
    messages.success(request, "Note deleted.")
    return redirect(reverse("panel:user_profile", args=[user_db_id]) + "#notes")
