# hammer/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel, TimestampedModel


class HammerSessionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    FINALIZED = "finalized", "Finalized"


class HammerSession(PublicIDModel, TimestampedModel):
    vehicle = models.OneToOneField(
        "inventory.Vehicle",
        on_delete=models.CASCADE,
        related_name="hammer_session",
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hammer_sessions",
    )

    status = models.CharField(
        max_length=20,
        choices=HammerSessionStatus.choices,
        default=HammerSessionStatus.DRAFT,
        db_index=True,
    )

    est_cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    est_time_total_minutes = models.PositiveIntegerField(default=0)

    derived = models.JSONField(default=dict, blank=True)

    notes = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hammer_hammer_session"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["status", "started_at"]),
            models.Index(fields=["manager", "started_at"]),
        ]

    def __str__(self):
        return f"Hammer for {self.vehicle}"


class HammerLineItem(PublicIDModel, TimestampedModel):
    session = models.ForeignKey(
        HammerSession,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    inspection_item = models.ForeignKey(
        "inspections.InspectionItem",
        on_delete=models.CASCADE,
        related_name="hammer_lines",
    )

    est_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    est_time_minutes = models.PositiveIntegerField(default=0)

    attributes = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hammer_hammer_line_item"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["session"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "inspection_item"],
                name="uniq_hammer_line_per_session_inspection_item",
            ),
        ]

    def __str__(self):
        return f"{self.inspection_item_id} @ {self.session_id}"