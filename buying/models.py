# buying/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone


from core.models.base import PublicIDModel, TimestampedModel


class BuyingDecisionStatus(models.TextChoices):
    WIN = "win", "Win"
    LOSS = "loss", "Loss"
    PENDING = "pending", "Pending"


class BuyingDecision(PublicIDModel, TimestampedModel):
    vehicle = models.OneToOneField(
        "inventory.Vehicle",
        on_delete=models.CASCADE,
        related_name="buying_decision",
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buying_decisions",
    )

    decision = models.CharField(
        max_length=20,
        choices=BuyingDecisionStatus.choices,
        default=BuyingDecisionStatus.PENDING,
        db_index=True,
    )

    decided_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "buying_buying_decision"
        verbose_name = "Buying Decision"
        verbose_name_plural = "Buying Decisions"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["decision", "decided_at"]),
            models.Index(fields=["buyer", "decided_at"]),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.get_decision_display()}"

    @property
    def is_win(self) -> bool:
        return self.decision == BuyingDecisionStatus.WIN