from datetime import datetime

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

from panel.decorators import login_required
from .helpers import session_ctx, is_elevated
from core.models import ImportRequest


def _elevated_required(view):
    from functools import wraps
    @wraps(view)
    def inner(request, *args, **kwargs):
        if not is_elevated(request):
            messages.error(request, "Admin access required.")
            return redirect(reverse("panel:dashboard"))
        return view(request, *args, **kwargs)
    return inner


@login_required
@_elevated_required
def import_chat(request):
    if request.method == "POST":
        raw   = (request.POST.get("tg_id") or "").strip().lstrip("@")
        label = (request.POST.get("label") or "").strip()
        if not raw:
            messages.warning(request, "Please enter a Telegram ID or username.")
            return redirect(reverse("panel:import_chat"))
        ImportRequest.objects.create(user_tg_id=raw, label=label, status="pending")
        messages.success(request, f"Import queued for @{raw}. The userbot will fetch the history shortly.")
        return redirect(reverse("panel:import_chat"))

    imports = ImportRequest.objects.order_by("-created_at")
    ctx = session_ctx(request)
    ctx["imports"] = imports
    return render(request, "panel/import_chat.html", ctx)


@login_required
def import_status(request, req_id):
    try:
        req = ImportRequest.objects.get(pk=req_id)
    except ImportRequest.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({
        "id":            req.pk,
        "user_tg_id":    req.user_tg_id,
        "label":         req.label,
        "status":        req.status,
        "message_count": req.message_count,
        "error_msg":     req.error_msg or "",
        "created_at":    str(req.created_at),
        "completed_at":  str(req.completed_at) if req.completed_at else None,
    })
