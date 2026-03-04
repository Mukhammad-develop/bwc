from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from panel.decorators import login_required
from .helpers import (
    check_admin_login, hash_password, check_password,
    notify_masters, session_ctx, get_current_admin,
)
from core.models import AdminUser


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("admin_logged_in"):
        return redirect(reverse("panel:dashboard"))
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        ok, role, aid, display = check_admin_login(username, password)
        if ok:
            request.session["admin_logged_in"] = True
            request.session["admin_username"]  = username
            request.session["admin_role"]      = role
            request.session["admin_id"]        = aid
            request.session["admin_display"]   = display
            messages.success(request, f"Welcome back, {display}!")
            return redirect(reverse("panel:dashboard"))
        error = "Invalid credentials."
    return render(request, "panel/login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect(reverse("panel:login"))


@login_required
def profile_view(request):
    is_env_master = (
        request.session.get("admin_role") == "master"
        and request.session.get("admin_id") is None
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "display_name":
            new_name = request.POST.get("display_name", "").strip()
            if not new_name:
                messages.error(request, "Display name cannot be empty.")
            elif is_env_master:
                request.session["admin_display"] = new_name
                messages.success(request, "Display name updated.")
            else:
                AdminUser.objects.filter(pk=request.session["admin_id"]).update(display_name=new_name)
                request.session["admin_display"] = new_name
                messages.success(request, "Display name updated.")

        elif action == "username":
            if is_env_master:
                messages.warning(request, "Built-in admin username is set via ADMIN_USERNAME in .env.")
            else:
                new_username = request.POST.get("new_username", "").strip()
                if len(new_username) < 3:
                    messages.error(request, "Username must be at least 3 characters.")
                elif AdminUser.objects.filter(username=new_username).exclude(pk=request.session["admin_id"]).exists():
                    messages.error(request, "That username is already taken.")
                else:
                    old = request.session.get("admin_username")
                    AdminUser.objects.filter(pk=request.session["admin_id"]).update(username=new_username)
                    request.session["admin_username"] = new_username
                    messages.success(request, f"Username changed to '{new_username}'.")
                    notify_masters(
                        title="Username changed",
                        message=f"{request.session.get('admin_display')} (@{old}) changed username to @{new_username}.",
                        link=reverse("panel:notifications"),
                        exclude_id=request.session.get("admin_id"),
                    )

        elif action == "password":
            if is_env_master:
                messages.warning(request, "Your password is set via ADMIN_PASSWORD in .env.")
            else:
                current  = request.POST.get("current_password", "")
                new_pw   = request.POST.get("new_password", "")
                confirm  = request.POST.get("confirm_password", "")
                if not current or not new_pw or not confirm:
                    messages.error(request, "All password fields are required.")
                elif new_pw != confirm:
                    messages.error(request, "New passwords do not match.")
                elif len(new_pw) < 6:
                    messages.error(request, "Password must be at least 6 characters.")
                else:
                    admin = AdminUser.objects.get(pk=request.session["admin_id"])
                    if not check_password(admin.password_hash, current):
                        messages.error(request, "Current password is incorrect.")
                    else:
                        admin.password_hash = hash_password(new_pw)
                        admin.save(update_fields=["password_hash"])
                        messages.success(request, "Password changed successfully.")

        return redirect(reverse("panel:profile"))

    profile_data = {
        "username":     request.session.get("admin_username", "admin"),
        "display_name": request.session.get("admin_display") or request.session.get("admin_username", "admin"),
        "role":         request.session.get("admin_role", "consultant"),
    }
    if not is_env_master and request.session.get("admin_id"):
        try:
            admin = AdminUser.objects.get(pk=request.session["admin_id"])
            profile_data["username"]     = admin.username
            profile_data["display_name"] = admin.display_name or admin.username
            profile_data["created_at"]   = str(admin.created_at)[:10]
        except AdminUser.DoesNotExist:
            pass

    ctx = session_ctx(request)
    ctx.update({
        "profile": profile_data,
        "is_env_master": is_env_master,
        "is_master": request.session.get("admin_role") == "master",
    })
    return render(request, "panel/profile.html", ctx)
