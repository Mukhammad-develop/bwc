import json
from datetime import datetime, timedelta

from django.shortcuts import render
from django.db.models import Count

from panel.decorators import login_required
from .helpers import session_ctx, is_elevated
from core.models import TgUser, Case, AiReport, AdminAssignment


@login_required
def dashboard(request):
    elevated = is_elevated(request)

    total_users  = TgUser.objects.count()
    total_cases  = Case.objects.count()
    active_cases = Case.objects.filter(status="active").count()
    paid_cases   = Case.objects.filter(payment_status="received").count()

    by_service = (
        Case.objects.values("service")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    qs = Case.objects.select_related("user").order_by("-created_at")
    if not elevated:
        admin_id = request.session.get("admin_id")
        assigned = AdminAssignment.objects.filter(admin_id=admin_id).values_list("user_id", flat=True)
        qs = qs.filter(user_id__in=assigned)
    recent_cases = qs[:10]

    if elevated:
        my_users_count = total_users
    else:
        my_users_count = AdminAssignment.objects.filter(admin_id=request.session.get("admin_id")).count()

    latest_report = AiReport.objects.order_by("-created_at").first()

    ctx = session_ctx(request)
    ctx.update({
        "total_users":    total_users,
        "total_cases":    total_cases,
        "active_cases":   active_cases,
        "paid_cases":     paid_cases,
        "by_service":     list(by_service),
        "recent_cases":   recent_cases,
        "my_users_count": my_users_count,
        "latest_report":  latest_report,
        "is_master":      request.session.get("admin_role") == "master",
        "is_elevated":    elevated,
    })
    return render(request, "panel/dashboard.html", ctx)
