from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

from panel.decorators import login_required
from .helpers import session_ctx
from core.models import Notification


@login_required
def notifications_list(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        messages.warning(request, "Notifications are not available for the built-in master account.")
        return redirect(reverse("panel:dashboard"))

    notifications = Notification.objects.filter(recipient_id=admin_id).order_by("-created_at")[:50]
    Notification.objects.filter(recipient_id=admin_id, is_read=False).update(is_read=True)

    ctx = session_ctx(request)
    ctx["notifications"] = notifications
    return render(request, "panel/notifications.html", ctx)


@login_required
def notif_read(request, notif_id):
    if request.method != "POST":
        return JsonResponse({"ok": False})
    admin_id = request.session.get("admin_id")
    if admin_id:
        Notification.objects.filter(pk=notif_id, recipient_id=admin_id).update(is_read=True)
    return JsonResponse({"ok": True})


@login_required
def notif_read_all(request):
    if request.method != "POST":
        return redirect(reverse("panel:notifications"))
    admin_id = request.session.get("admin_id")
    if admin_id:
        Notification.objects.filter(recipient_id=admin_id).update(is_read=True)
    return redirect(reverse("panel:notifications"))


@login_required
def notif_preview(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return JsonResponse({"items": []})
    items = list(
        Notification.objects.filter(recipient_id=admin_id)
        .order_by("-created_at")[:5]
        .values("id", "title", "message", "link", "is_read", "created_at")
    )
    for i in items:
        i["created_at"] = str(i["created_at"])
    return JsonResponse({"items": items})


@login_required
def notif_mark_preview_read(request):
    if request.method != "POST":
        return JsonResponse({"ok": False})
    admin_id = request.session.get("admin_id")
    if admin_id:
        Notification.objects.filter(recipient_id=admin_id, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})
