# notifications/models.py

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel, TimestampedModel


class Notification(PublicIDModel, TimestampedModel):
    """
    A single in-app notification for one recipient inside one dealership.

    Keep type/category/priority/entity_type as strings so notification behavior
    can evolve from registry/config files without requiring migrations every time
    a new notification type is added.

    Example type values:
    - vehicle.created
    - vehicle.status_changed
    - inspection.assigned
    - inspection.completed
    - buying.decision_made
    - recon.assigned
    - recon.failed
    - vendor.item_updated
    - billing.payment_failed

    Example category values:
    - vehicles
    - inspections
    - buying
    - recon
    - vendors
    - billing
    - system
    """

    dealership = models.ForeignKey(
        "accounts.Dealership",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        help_text="User who caused the notification, if applicable.",
    )

    type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Registry-backed notification type, e.g. vehicle.status_changed.",
    )

    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Registry-backed category, e.g. vehicles, inspections, recon.",
    )

    priority = models.CharField(
        max_length=20,
        default="normal",
        db_index=True,
        help_text="Expected values: low, normal, high, critical.",
    )

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")

    entity_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Optional linked entity type, e.g. vehicle, inspection, recon_case.",
    )

    entity_public_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Public ID of the linked entity, not database ID.",
    )

    target_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Frontend URL to open when the user clicks the notification.",
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Small extra payload for UI/email rendering. Do not store large data here.",
    )

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["recipient", "dealership", "is_read"]),
            models.Index(fields=["recipient", "dealership", "-created_at"]),
            models.Index(fields=["dealership", "category", "-created_at"]),
            models.Index(fields=["dealership", "type", "-created_at"]),
            models.Index(fields=["dealership", "priority", "-created_at"]),
            models.Index(fields=["entity_type", "entity_public_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_id}: {self.type}"

    def mark_read(self, save: bool = True) -> None:
        if self.is_read:
            return

        self.is_read = True
        self.read_at = timezone.now()

        if save:
            self.save(update_fields=["is_read", "read_at", "updated_at"])

    def mark_unread(self, save: bool = True) -> None:
        if not self.is_read:
            return

        self.is_read = False
        self.read_at = None

        if save:
            self.save(update_fields=["is_read", "read_at", "updated_at"])


class NotificationPreference(PublicIDModel, TimestampedModel):
    """
    Per-user notification preferences inside a specific dealership.

    Global channel switches are stable columns.

    Category/type preferences are JSON so new categories and notification types
    can be added without migrations or backfills.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    dealership = models.ForeignKey(
        "accounts.Dealership",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    in_app_enabled = models.BooleanField(default=True)
    websocket_enabled = models.BooleanField(default=True)

    email_enabled = models.BooleanField(default=True)
    email_important_only = models.BooleanField(
        default=True,
        help_text="When true, only high/critical notifications should be emailed.",
    )

    category_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-category channel overrides.",
    )

    type_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-notification-type channel overrides.",
    )

    class Meta:
        db_table = "notifications_notification_preference"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["user", "dealership"]),
            models.Index(fields=["dealership"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dealership"],
                name="uniq_notification_preference_per_user_dealership",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} / {self.dealership_id}"


class NotificationDelivery(PublicIDModel, TimestampedModel):
    """
    Tracks delivery attempts for a notification.

    Expected channel values:
    - in_app
    - websocket
    - email
    - push

    Expected status values:
    - pending
    - sent
    - failed
    - skipped
    """

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )

    channel = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Delivery channel, e.g. in_app, websocket, email, push.",
    )

    status = models.CharField(
        max_length=32,
        default="pending",
        db_index=True,
        help_text="Delivery status, e.g. pending, sent, failed, skipped.",
    )

    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    failure_reason = models.TextField(blank=True, default="")

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Provider response, email message id, websocket group, skip reason, etc.",
    )

    class Meta:
        db_table = "notifications_notification_delivery"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["notification", "channel"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_id} / {self.channel} / {self.status}"

    def mark_sent(self, save: bool = True) -> None:
        self.status = "sent"
        self.sent_at = timezone.now()
        self.failed_at = None
        self.failure_reason = ""

        if save:
            self.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "failed_at",
                    "failure_reason",
                    "updated_at",
                ]
            )

    def mark_failed(self, reason: str = "", save: bool = True) -> None:
        self.status = "failed"
        self.failed_at = timezone.now()
        self.failure_reason = reason or ""

        if save:
            self.save(
                update_fields=[
                    "status",
                    "failed_at",
                    "failure_reason",
                    "updated_at",
                ]
            )

    def mark_skipped(self, reason: str = "", save: bool = True) -> None:
        self.status = "skipped"
        self.failure_reason = reason or ""

        if save:
            self.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "updated_at",
                ]
            )