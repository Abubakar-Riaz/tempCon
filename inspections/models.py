# inspections/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Company, Dealership
from core.models.base import PublicIDModel, TimestampedModel


class Trade(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="trades",
    )

    key = models.SlugField(max_length=64)
    label = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")

    order_index = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "inspections_trade"
        ordering = ("order_index", "label")
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "order_index"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "key"],
                name="uniq_trade_key_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.label} ({self.company.name})"


class InspectionItemStatus(models.TextChoices):
    OK = "ok", "OK"
    NEEDS_ATTENTION = "needs_attention", "Needs Attention"
    NA = "na", "Not Applicable"


class InspectionItemTemplate(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="inspection_templates",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inspection_templates",
    )

    trade = models.ForeignKey(
        Trade,
        on_delete=models.PROTECT,
        related_name="templates",
    )

    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "inspections_inspection_item_template"
        ordering = ("trade", "order_index", "label")
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "trade", "is_active"]),
            models.Index(fields=["dealership", "trade", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "dealership", "trade", "label"],
                name="uniq_template_per_scope_trade_label",
            ),
        ]

    def __str__(self):
        scope = self.dealership.name if self.dealership_id else self.company.name
        return f"{self.trade.label} - {self.label} ({scope})"


class InspectionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class Inspection(PublicIDModel, TimestampedModel):
    vehicle = models.ForeignKey(
        "inventory.Vehicle",
        on_delete=models.CASCADE,
        related_name="inspections",
    )

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspections",
    )

    status = models.CharField(
        max_length=20,
        choices=InspectionStatus.choices,
        default=InspectionStatus.DRAFT,
        db_index=True,
    )

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    items_total = models.PositiveIntegerField(default=0)
    items_ok = models.PositiveIntegerField(default=0)
    items_needs_attention = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "inspections_inspection"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["inspector", "status"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        return f"Inspection #{self.pk} for {self.vehicle_id}"


class InspectionItem(PublicIDModel, TimestampedModel):
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="items",
    )

    template = models.ForeignKey(
        InspectionItemTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )

    trade = models.ForeignKey(
        Trade,
        on_delete=models.PROTECT,
        related_name="inspection_items",
    )

    trade_label = models.CharField(max_length=128, blank=True, default="")
    label = models.CharField(max_length=255)

    status = models.CharField(
        max_length=24,
        choices=InspectionItemStatus.choices,
        default=InspectionItemStatus.OK,
        db_index=True,
    )

    notes = models.TextField(blank=True, default="")

    attachments = models.ManyToManyField(
        "inventory.Attachment",
        through="InspectionItemAttachment",
        related_name="inspection_items",
        blank=True,
    )

    class Meta:
        db_table = "inspections_inspection_item"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["inspection", "trade"]),
            models.Index(fields=["inspection", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "trade", "label"],
                name="uniq_inspection_item_per_inspection_trade_label",
            ),
        ]

    def __str__(self):
        return f"{self.trade_label} - {self.label} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.trade_label and self.trade_id:
            self.trade_label = self.trade.label
        super().save(*args, **kwargs)


class InspectionItemAttachment(PublicIDModel, TimestampedModel):
    item = models.ForeignKey(
        InspectionItem,
        on_delete=models.CASCADE,
        related_name="item_attachments",
    )

    attachment = models.ForeignKey(
        "inventory.Attachment",
        on_delete=models.CASCADE,
        related_name="item_attachments",
    )

    class Meta:
        db_table = "inspections_inspection_item_attachment"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["item"]),
            models.Index(fields=["attachment"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "attachment"],
                name="uniq_inspection_item_attachment",
            ),
        ]

    def __str__(self):
        return f"Item#{self.item_id} - Att#{self.attachment_id}"