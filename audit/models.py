#audit/models.py
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.models import Company, Dealership
from core.models.base import PublicIDModel, TimestampedModel


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    STATUS_CHANGE = "status_change", "Status Change"
    ATTACHMENT_ADD = "attachment_add", "Attachment Added"
    ATTACHMENT_REMOVE = "attachment_remove", "Attachment Removed"
    ASSIGN = "assign", "Assign"
    UNASSIGN = "unassign", "Unassign"
    INVITE_SENT = "invite_sent", "Invite Sent"
    INVITE_ACCEPTED = "invite_accepted", "Invite Accepted"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    OTHER = "other", "Other"


class AuditLog(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")

    action = models.CharField(
        max_length=32,
        choices=AuditAction.choices,
        default=AuditAction.OTHER,
        db_index=True,
    )

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        db_table = "audits_audit_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["dealership", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["target_content_type", "target_object_id", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        target = (
            f"{self.target_content_type.app_label}."
            f"{self.target_content_type.model}#{self.target_object_id}"
        )
        return f"{self.action} on {target} by {self.actor or 'system'}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditLog entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)