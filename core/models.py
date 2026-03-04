import json
from django.db import models
from django.utils import timezone


class TgUser(models.Model):
    tg_id           = models.BigIntegerField(unique=True)
    language        = models.CharField(max_length=10, default="en")
    chat_mode       = models.CharField(max_length=20, default="menu")
    linked_account  = models.IntegerField(default=0)   # 0 or 1 — which userbot account
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"@{self.tg_id}"


class Case(models.Model):
    SERVICE_CHOICES = [
        ("student", "Student Visa"),
        ("paye",    "PAYE Tax Refund"),
        ("self",    "Self-Employed Tax"),
        ("company", "Company Accounting"),
        ("general", "General"),
    ]
    STATUS_CHOICES = [
        ("active",    "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("pending",  "Pending"),
        ("received", "Received"),
        ("refunded", "Refunded"),
    ]

    user            = models.ForeignKey(TgUser, on_delete=models.CASCADE, related_name="cases")
    service         = models.CharField(max_length=30, choices=SERVICE_CHOICES, default="general")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    payment_status  = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="pending")
    conversation_history = models.TextField(default="[]")
    context         = models.TextField(default="{}")
    created_at      = models.DateTimeField(default=timezone.now)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cases"
        ordering = ["-created_at"]

    def get_conversation(self):
        try:
            return json.loads(self.conversation_history or "[]")
        except Exception:
            return []

    def set_conversation(self, conv):
        self.conversation_history = json.dumps(conv)

    def add_message(self, role, content, sender=None):
        conv = self.get_conversation()
        entry = {"role": role, "content": content, "timestamp": timezone.now().isoformat()}
        if sender:
            entry["sender"] = sender
        conv.append(entry)
        self.set_conversation(conv)
        self.save(update_fields=["conversation_history", "updated_at"])


class Document(models.Model):
    case            = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    doc_type        = models.CharField(max_length=100)
    filename        = models.CharField(max_length=255, blank=True, null=True)
    media_type      = models.CharField(max_length=50, default="document")
    file_id         = models.TextField()
    file_unique_id  = models.CharField(max_length=255)
    transcription   = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "documents"
        ordering = ["created_at"]

    def __str__(self):
        return self.filename or self.doc_type


class Payment(models.Model):
    case            = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="payments")
    method          = models.CharField(max_length=50)
    proof_file_id   = models.TextField(blank=True, null=True)
    status          = models.CharField(max_length=20)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "payments"


class Reminder(models.Model):
    case            = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="reminders")
    type            = models.CharField(max_length=50)
    due_at          = models.DateTimeField()
    sent            = models.BooleanField(default=False)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "reminders"


class PendingSend(models.Model):
    user_tg_id      = models.CharField(max_length=30)
    message         = models.TextField()
    sender_name     = models.CharField(max_length=100, default="Admin")
    sent            = models.BooleanField(default=False)
    account_index   = models.IntegerField(default=0)
    created_at      = models.DateTimeField(default=timezone.now)
    sent_at         = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "pending_sends"
        ordering = ["created_at"]


class ImportRequest(models.Model):
    STATUS_CHOICES = [
        ("pending",    "Pending"),
        ("processing", "Processing"),
        ("done",       "Done"),
        ("error",      "Error"),
    ]
    user_tg_id      = models.CharField(max_length=30)
    label           = models.CharField(max_length=255, blank=True, default="")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message_count   = models.IntegerField(default=0)
    error_msg       = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(default=timezone.now)
    completed_at    = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "import_requests"
        ordering = ["-created_at"]


# ── Admin panel models ────────────────────────────────────────────────────────

class AdminUser(models.Model):
    ROLE_CHOICES = [
        ("master",     "Master"),
        ("admin",      "Admin"),
        ("consultant", "Consultant"),
    ]
    username        = models.CharField(max_length=100, unique=True)
    password_hash   = models.TextField()
    display_name    = models.CharField(max_length=150, blank=True, null=True)
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default="consultant")
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "admin_users"

    def __str__(self):
        return f"{self.username} ({self.role})"


class AdminAssignment(models.Model):
    admin           = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name="assignments")
    user            = models.ForeignKey(TgUser, on_delete=models.CASCADE, related_name="assigned_admins")
    assigned_at     = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "admin_assignments"
        unique_together = [("admin", "user")]


class UserAiProfile(models.Model):
    user            = models.OneToOneField(TgUser, on_delete=models.CASCADE, related_name="ai_profile")
    extracted_data  = models.TextField(default="{}")
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_ai_profiles"

    def get_data(self):
        try:
            return json.loads(self.extracted_data or "{}")
        except Exception:
            return {}


class AiReport(models.Model):
    report_type     = models.CharField(max_length=50)
    period_start    = models.DateTimeField()
    period_end      = models.DateTimeField()
    stats           = models.TextField(default="{}")
    ai_conclusion   = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "ai_reports"
        ordering = ["-created_at"]

    def get_stats(self):
        try:
            return json.loads(self.stats or "{}")
        except Exception:
            return {}


class Notification(models.Model):
    recipient       = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name="notifications")
    title           = models.CharField(max_length=255)
    message         = models.TextField()
    link            = models.CharField(max_length=500, blank=True, null=True)
    is_read         = models.BooleanField(default=False)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
