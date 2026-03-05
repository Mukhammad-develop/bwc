import json
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages

from panel.decorators import login_required
from .helpers import session_ctx, is_elevated, can_view_user, get_tg_file_url, is_voice_doc
from core.models import Case, Document, AdminAssignment, ServiceDefinition, ServiceStep, CaseProgress, AdminUser


@login_required
def cases_list(request):
    elevated = is_elevated(request)
    service  = request.GET.get("service", "")
    status   = request.GET.get("status", "")
    payment  = request.GET.get("payment", "")

    qs = Case.objects.select_related("user").order_by("-created_at")
    if not elevated:
        admin_id = request.session.get("admin_id")
        assigned = AdminAssignment.objects.filter(admin_id=admin_id).values_list("user_id", flat=True)
        qs = qs.filter(user_id__in=assigned)
    if service:
        qs = qs.filter(service=service)
    if status:
        qs = qs.filter(status=status)
    if payment:
        qs = qs.filter(payment_status=payment)

    all_services = list(ServiceDefinition.objects.filter(is_active=True).order_by("order", "name"))
    ctx = session_ctx(request)
    ctx.update({
        "cases":          qs,
        "filter_service": service,
        "filter_status":  status,
        "filter_payment": payment,
        "is_master":      request.session.get("admin_role") == "master",
        "is_elevated":    elevated,
        "all_services":   all_services,
    })
    return render(request, "panel/cases.html", ctx)


@login_required
def case_detail(request, case_id):
    case = get_object_or_404(Case.objects.select_related("user"), pk=case_id)
    if not can_view_user(request, case.user_id):
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:cases"))

    try:
        conversation = json.loads(case.conversation_history or "[]")
    except Exception:
        conversation = []

    documents = Document.objects.filter(case=case).order_by("created_at")
    docs_with_url   = []
    docs_by_uid     = {}
    docs_by_fname   = {}
    for doc in documents:
        url   = get_tg_file_url(doc.file_id)
        entry = {"doc": doc, "url": url}
        docs_with_url.append(entry)
        docs_by_uid[doc.file_unique_id] = entry
        fname = doc.filename or doc.doc_type or ""
        if fname and fname not in docs_by_fname:
            docs_by_fname[fname] = entry
    docs_for_files = [e for e in docs_with_url if not is_voice_doc(e["doc"])]

    # Progress bar
    try:
        sdef = ServiceDefinition.objects.get(slug=case.service, is_active=True)
        steps = list(sdef.steps.all())
    except ServiceDefinition.DoesNotExist:
        sdef  = None
        steps = []
    try:
        prog = case.progress
        current_step_id = prog.current_step_id
    except CaseProgress.DoesNotExist:
        current_step_id = None

    current_idx = next((i for i, s in enumerate(steps) if s.pk == current_step_id), -1)

    ctx = session_ctx(request)
    ctx.update({
        "case":              case,
        "conversation":      conversation,
        "docs_with_url":     docs_with_url,
        "docs_for_files":    docs_for_files,
        "docs_by_unique_id": docs_by_uid,
        "docs_by_filename":  docs_by_fname,
        "is_master":         request.session.get("admin_role") == "master",
        "sdef":              sdef,
        "steps":             steps,
        "current_step_id":   current_step_id,
        "current_idx":       current_idx,
    })
    return render(request, "panel/case_detail.html", ctx)


@login_required
def case_update(request, case_id):
    if request.method != "POST":
        return redirect(reverse("panel:case_detail", args=[case_id]))
    case = get_object_or_404(Case, pk=case_id)
    if not can_view_user(request, case.user_id):
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:cases"))
    status  = request.POST.get("status")
    payment = request.POST.get("payment_status")
    if status:
        case.status = status
    if payment:
        case.payment_status = payment
    case.save()
    messages.success(request, "Case updated.")
    return redirect(reverse("panel:case_detail", args=[case_id]))


@login_required
def case_progress(request, case_id):
    if request.method != "POST":
        return redirect(reverse("panel:case_detail", args=[case_id]))
    case = get_object_or_404(Case, pk=case_id)
    if not can_view_user(request, case.user_id):
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:cases"))
    step_id  = request.POST.get("step_id", type=int) or None
    admin_id = request.session.get("admin_id")
    author   = AdminUser.objects.filter(pk=admin_id).first() if admin_id else None
    if step_id:
        step = get_object_or_404(ServiceStep, pk=step_id)
        prog, _ = CaseProgress.objects.get_or_create(case=case)
        prog.current_step = step
        prog.updated_by   = author
        prog.save()
        messages.success(request, f"Progress updated to: {step.label}")
    else:
        CaseProgress.objects.filter(case=case).delete()
        messages.success(request, "Progress cleared.")
    return redirect(reverse("panel:case_detail", args=[case_id]))
