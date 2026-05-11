# webhooks/models/base.py

from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel, TimestampedModel


class WebhookProvider(models.TextChoices):
    STRIPE = "stripe", "Stripe"
    OTHER = "other", "Other"


class WebhookProcessingStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"


class WebhookEvent(PublicIDModel, TimestampedModel):
    provider = models.CharField(
        max_length=32,
        choices=WebhookProvider.choices,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=WebhookProcessingStatus.choices,
        default=WebhookProcessingStatus.RECEIVED,
        db_index=True,
    )

    provider_event_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    event_type = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    signature = models.TextField(blank=True, default="")
    headers = models.JSONField(default=dict, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    failure_reason = models.TextField(blank=True, default="")
    processing_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "webhooks_webhook_event"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["provider", "provider_event_id"]),
            models.Index(fields=["received_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_id"],
                condition=~models.Q(provider_event_id=""),
                name="uniq_webhook_provider_event_id_nonempty",
            ),
        ]

    def __str__(self) -> str:
        ident = self.provider_event_id or self.public_id
        return f"{self.provider}:{ident}"

    def mark_processing(self):
        self.status = WebhookProcessingStatus.PROCESSING
        self.processing_attempts += 1

    def mark_processed(self):
        self.status = WebhookProcessingStatus.PROCESSED
        self.processed_at = timezone.now()

    def mark_failed(self, reason: str = ""):
        self.status = WebhookProcessingStatus.FAILED
        self.failed_at = timezone.now()
        self.failure_reason = reason

    def mark_ignored(self, reason: str = ""):
        self.status = WebhookProcessingStatus.IGNORED
        self.processed_at = timezone.now()
        self.failure_reason = reason