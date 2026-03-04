from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from core.models import AdminUser


def _get_admin(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    try:
        return AdminUser.objects.get(pk=admin_id)
    except AdminUser.DoesNotExist:
        return None


def login_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        if _get_admin(request) is not None:
            return view(request, *args, **kwargs)
        if request.session.get("admin_logged_in"):
            return view(request, *args, **kwargs)  # env master (no admin_id)
        return redirect(reverse("panel:login"))
    return inner


def master_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        admin = _get_admin(request)
        if admin is not None and admin.role == "master":
            return view(request, *args, **kwargs)
        if request.session.get("admin_logged_in") and request.session.get("admin_role") == "master":
            return view(request, *args, **kwargs)  # env master
        return redirect(reverse("panel:dashboard"))
    return inner


def is_elevated(request):
    """Master or Admin role — can see all users."""
    admin = _get_admin(request)
    if admin and admin.role in ("master", "admin"):
        return True
    return request.session.get("admin_role") in ("master", "admin")


def can_view_user(request, user_id):
    """Check if the logged-in admin can view this user."""
    from core.models import AdminAssignment
    admin = _get_admin(request)
    role = admin.role if admin else request.session.get("admin_role")
    if role in ("master", "admin"):
        return True
    if not admin:
        return False
    return AdminAssignment.objects.filter(admin=admin, user_id=user_id).exists()
