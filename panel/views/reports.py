import json
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages

from panel.decorators import login_required
from .helpers import session_ctx, is_elevated, compute_stats, call_ai
from core.models import AiReport


def _elevated_required(view):
    from functools import wraps
    @wraps(view)
    def inner(request, *args, **kwargs):
        if not request.session.get("admin_logged_in"):
            return redirect(reverse("panel:login"))
        if not is_elevated(request):
            messages.error(request, "Admin access required.")
            return redirect(reverse("panel:dashboard"))
        return view(request, *args, **kwargs)
    return inner


@login_required
@_elevated_required
def reports_list(request):
    from django.conf import settings
    reports = AiReport.objects.order_by("-created_at")[:20]
    now = datetime.utcnow()
    today_stats = compute_stats(
        (now - timedelta(days=1)).isoformat(),
        now.isoformat(),
    )
    report_types = [
        ("daily",     "Daily",     "Last 24 hours — recent activity summary"),
        ("weekly",    "Weekly",    "Last 7 days — week-over-week trends"),
        ("monthly",   "Monthly",   "Last 30 days — monthly business review"),
        ("quarterly", "Quarterly", "Last 90 days — strategic overview"),
    ]
    ctx = session_ctx(request)
    ctx.update({
        "reports":      reports,
        "today_stats":  today_stats,
        "report_types": report_types,
        "is_master":    request.session.get("admin_role") == "master",
    })
    return render(request, "panel/reports.html", ctx)


@login_required
@_elevated_required
def generate_report(request, report_type):
    if request.method != "POST":
        return redirect(reverse("panel:reports"))
    from django.conf import settings
    DELTA = {
        "daily":     timedelta(days=1),
        "weekly":    timedelta(weeks=1),
        "monthly":   timedelta(days=30),
        "quarterly": timedelta(days=90),
    }
    LABEL = {
        "daily":     "last 24 hours",
        "weekly":    "last 7 days",
        "monthly":   "last 30 days",
        "quarterly": "last 90 days",
    }
    if report_type not in DELTA:
        messages.error(request, "Invalid report type.")
        return redirect(reverse("panel:reports"))

    now   = datetime.utcnow()
    start = (now - DELTA[report_type]).isoformat()
    end   = now.isoformat()
    stats = compute_stats(start, end)

    conclusion = None
    if settings.OPENAI_API_KEY:
        system = """You are a business analyst for Brightway Consulting (UK immigration, tax, accounting).
Write a concise 2-3 paragraph professional summary of the period stats below.
Note any trends, highlight wins, identify potential issues, and give one actionable suggestion."""
        body = (
            f"Period: {LABEL[report_type]}\n"
            f"New users: {stats['new_users']}\n"
            f"New cases: {stats['new_cases']}\n"
            f"Cases by service: {json.dumps(stats['by_service'])}\n"
            f"Payments received: {stats['paid']}\n"
            f"Completed cases: {stats['completed']}\n"
            f"Currently active cases: {stats['active']}\n"
            f"Documents uploaded: {stats['docs']}"
        )
        conclusion = call_ai(system, body, max_tokens=500)

    AiReport.objects.create(
        report_type=report_type,
        period_start=start,
        period_end=end,
        stats=json.dumps(stats),
        ai_conclusion=conclusion,
    )
    messages.success(request, f"{report_type.capitalize()} report generated.")
    return redirect(reverse("panel:reports"))


@login_required
@_elevated_required
def report_detail(request, report_id):
    report = get_object_or_404(AiReport, pk=report_id)
    stats  = report.get_stats()
    stat_items = [
        ("New Users",       stats.get("new_users", 0)),
        ("New Cases",       stats.get("new_cases", 0)),
        ("Payments Rcvd",   stats.get("paid", 0)),
        ("Cases Completed", stats.get("completed", 0)),
        ("Active Cases",    stats.get("active", 0)),
        ("Files Uploaded",  stats.get("docs", 0)),
    ]
    ctx    = session_ctx(request)
    ctx.update({
        "report":     report,
        "stats":      stats,
        "stat_items": stat_items,
        "is_master":  request.session.get("admin_role") == "master",
    })
    return render(request, "panel/report_detail.html", ctx)
