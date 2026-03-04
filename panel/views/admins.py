from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count

from panel.decorators import master_required
from .helpers import session_ctx, hash_password
from core.models import AdminUser, AdminAssignment, TgUser, UserAiProfile


@master_required
def admins_list(request):
    admins = (
        AdminUser.objects
        .annotate(assigned_count=Count("assignments"))
        .order_by("-created_at")
    )
    all_users = TgUser.objects.prefetch_related("ai_profile").order_by("-created_at")

    ctx = session_ctx(request)
    ctx.update({"admins": admins, "all_users": all_users})
    return render(request, "panel/admins.html", ctx)


@master_required
def add_admin(request):
    if request.method != "POST":
        return redirect(reverse("panel:admins"))
    username     = request.POST.get("username", "").strip()
    password     = request.POST.get("password", "").strip()
    display_name = request.POST.get("display_name", "").strip()
    role         = request.POST.get("role", "consultant")
    if not username or not password:
        messages.error(request, "Username and password required.")
        return redirect(reverse("panel:admins"))
    if AdminUser.objects.filter(username=username).exists():
        messages.error(request, "Username already exists.")
        return redirect(reverse("panel:admins"))
    AdminUser.objects.create(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name or username,
        role=role,
    )
    messages.success(request, f"Admin '{username}' created.")
    return redirect(reverse("panel:admins"))


@master_required
def delete_admin(request, admin_id):
    if request.method != "POST":
        return redirect(reverse("panel:admins"))
    AdminAssignment.objects.filter(admin_id=admin_id).delete()
    AdminUser.objects.filter(pk=admin_id).delete()
    messages.success(request, "Admin deleted.")
    return redirect(reverse("panel:admins"))
