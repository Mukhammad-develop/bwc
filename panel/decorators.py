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
        if not _get_admin(request):
            return redirect(reverse("panel:login"))
        return view(request, *args, **kwargs)
    return inner


def master_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        admin = _get_admin(request)
        if not admin or admin.role != "master":
            return redirect(reverse("panel:dashboard"))
        return view(request, *args, **kwargs)
    return inner


def is_elevated(request):
    """Master or Admin role — can see all users."""
    admin = _get_admin(request)
    return admin and admin.role in ("master", "admin")


def can_view_user(request, user_id):
    """Check if the logged-in admin can view this user."""
    from core.models import AdminAssignment
    admin = _get_admin(request)
    if not admin:
        return False
    if admin.role in ("master", "admin"):
        return True
    return AdminAssignment.objects.filter(admin=admin, user_id=user_id).exists()
