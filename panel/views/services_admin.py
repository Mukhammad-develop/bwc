import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST

from panel.decorators import login_required
from .helpers import session_ctx, is_elevated
from core.models import ServiceDefinition, ServiceStep


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:50]


@login_required
def services_list(request):
    elevated = is_elevated(request)
    is_master = request.session.get("admin_role") == "master"
    services = ServiceDefinition.objects.prefetch_related("steps").all()
    ctx = session_ctx(request)
    ctx.update({
        "services":   services,
        "is_master":  is_master,
        "is_elevated": elevated,
    })
    return render(request, "panel/services_admin.html", ctx)


@login_required
def service_add(request):
    if request.session.get("admin_role") != "master":
        messages.error(request, "Only master admins can add services.")
        return redirect(reverse("panel:services_list"))

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        slug = request.POST.get("slug", "").strip() or _slugify(name)
        description = request.POST.get("description", "").strip()
        ai_prompt = request.POST.get("ai_prompt", "").strip()
        is_active = request.POST.get("is_active") == "on"
        order = int(request.POST.get("order", 0) or 0)

        if not name:
            messages.error(request, "Service name is required.")
        elif ServiceDefinition.objects.filter(slug=slug).exists():
            messages.error(request, f"A service with slug '{slug}' already exists.")
        else:
            with transaction.atomic():
                sdef = ServiceDefinition.objects.create(
                    slug=slug, name=name, description=description,
                    ai_prompt=ai_prompt, is_active=is_active, order=order,
                )
                _save_steps(sdef, request.POST)
            messages.success(request, f"Service '{name}' created.")
            return redirect(reverse("panel:services_list"))

    ctx = session_ctx(request)
    ctx.update({"service": None, "is_master": True, "default_prompt": _default_prompt()})
    return render(request, "panel/service_edit.html", ctx)


@login_required
def service_edit(request, slug):
    elevated = is_elevated(request)
    if not elevated:
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:services_list"))

    sdef = get_object_or_404(ServiceDefinition, slug=slug)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        ai_prompt = request.POST.get("ai_prompt", "").strip()
        is_active = request.POST.get("is_active") == "on"
        order = int(request.POST.get("order", 0) or 0)

        if not name:
            messages.error(request, "Service name is required.")
        else:
            with transaction.atomic():
                sdef.name = name
                sdef.description = description
                sdef.ai_prompt = ai_prompt
                sdef.is_active = is_active
                sdef.order = order
                sdef.save()
                _save_steps(sdef, request.POST)
            messages.success(request, f"Service '{name}' saved.")
            return redirect(reverse("panel:services_list"))

    ctx = session_ctx(request)
    ctx.update({
        "service": sdef,
        "steps":   list(sdef.steps.all()),
        "is_master": request.session.get("admin_role") == "master",
        "default_prompt": _default_prompt(),
    })
    return render(request, "panel/service_edit.html", ctx)


@login_required
@require_POST
def service_delete(request, slug):
    if request.session.get("admin_role") != "master":
        messages.error(request, "Only master admins can delete services.")
        return redirect(reverse("panel:services_list"))

    sdef = get_object_or_404(ServiceDefinition, slug=slug)
    name = sdef.name
    sdef.delete()
    messages.success(request, f"Service '{name}' deleted.")
    return redirect(reverse("panel:services_list"))


@login_required
@require_POST
def service_toggle(request, slug):
    elevated = is_elevated(request)
    if not elevated:
        messages.error(request, "Access denied.")
        return redirect(reverse("panel:services_list"))
    sdef = get_object_or_404(ServiceDefinition, slug=slug)
    sdef.is_active = not sdef.is_active
    sdef.save(update_fields=["is_active"])
    return redirect(reverse("panel:services_list"))


def _save_steps(sdef, post_data):
    """Parse step form data and rebuild all steps for a service."""
    labels = post_data.getlist("step_label")
    descs  = post_data.getlist("step_description")
    sdef.steps.all().delete()
    for i, label in enumerate(labels):
        label = label.strip()
        if not label:
            continue
        desc = descs[i].strip() if i < len(descs) else ""
        ServiceStep.objects.create(service=sdef, label=label, description=desc, order=i)


def _default_prompt():
    return """You work at Brightway Consulting, a UK firm.
You are chatting with a client on Telegram about [SERVICE NAME].

YOUR JOB — gather this info through natural conversation, one thing at a time:
- [item 1]
- [item 2]

DOCUMENTS you'll need from them (ask when the moment feels right, not all at once):
- [document 1]

Once docs are uploaded: tell them the team will review and send payment info + next steps within 24-48h.
If they ask price: say the team confirms the exact fee after reviewing — it's competitive for what's included.

TONE AND STYLE:
- Sound like a real consultant in a live chat, not a scripted assistant.
- Professional, warm, and direct.
- Ask exactly ONE clear question per message.
- Keep replies short (1-3 short sentences) unless sharing a document list.

AVOID BOT-LIKE PHRASES:
- "Thank you for your message."
- "Kindly provide..."

LANGUAGE: Reply in the user's language. Keep messages short and focused."""
