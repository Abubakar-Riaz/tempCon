from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel, TimestampedModel
from inventory.models import _sanitize_filename


class ReconStatus(models.TextChoices):
    OPEN = "open", "Open"
    FAIL = "fail", "Fail"
    COMPLETE = "complete", "Complete"


class WorkItemStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    DONE = "done", "Done"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class VendorAttachmentKind(models.TextChoices):
    BILL = "bill", "Bill"
    INVOICE = "invoice", "Invoice"
    PHOTO = "photo", "Photo"
    OTHER = "other", "Other"


class ReconCase(PublicIDModel, TimestampedModel):
    vehicle = models.OneToOneField(
        "inventory.Vehicle",
        on_delete=models.CASCADE,
        related_name="recon_case",
    )

    recon_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_recon_cases",
    )

    status = models.CharField(
        max_length=20,
        choices=ReconStatus.choices,
        default=ReconStatus.OPEN,
        db_index=True,
    )

    fail_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "recon_recon_case"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["status", "opened_at"]),
            models.Index(fields=["recon_manager", "status"]),
        ]

    def __str__(self):
        return f"ReconCase for Vehicle#{self.vehicle_id} ({self.status})"


class WorkItem(PublicIDModel, TimestampedModel):
    recon_case = models.ForeignKey(
        ReconCase,
        on_delete=models.CASCADE,
        related_name="work_items",
    )

    trade = models.ForeignKey(
        "inspections.Trade",
        on_delete=models.PROTECT,
        related_name="recon_work_items",
    )

    source_inspection_item = models.ForeignKey(
        "inspections.InspectionItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recon_work_items",
    )

    assigned_vendor = models.ForeignKey(
        "accounts.DealershipMembership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_work_items",
    )

    status = models.CharField(
        max_length=20,
        choices=WorkItemStatus.choices,
        default=WorkItemStatus.NOT_STARTED,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )

    due_date = models.DateField(null=True, blank=True)

    est_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    est_time_minutes = models.PositiveIntegerField(default=0)

    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "recon_work_item"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["recon_case", "status"]),
            models.Index(fields=["assigned_vendor", "status", "due_date"]),
            models.Index(fields=["trade"]),
            models.Index(fields=["priority", "due_date"]),
        ]

    def __str__(self):
        return f"WorkItem#{self.pk} v{self.recon_case.vehicle_id} [{self.trade_id}]"

    @property
    def is_done(self) -> bool:
        return self.status == WorkItemStatus.DONE


def _vendor_attachment_upload_path(instance, filename):
    d = timezone.now()
    kind = (getattr(instance, "kind", "") or "other").lower()
    safe_name = _sanitize_filename(filename, randomize=True)
    return f"vendor_attachments/{d:%Y/%m/%d}/{kind}/workitem_{instance.work_item_id}/{safe_name}"


class VendorAttachment(PublicIDModel, TimestampedModel):
    work_item = models.ForeignKey(
        WorkItem,
        on_delete=models.CASCADE,
        related_name="vendor_attachments",
    )

    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recon_attachments",
    )

    file = models.FileField(upload_to=_vendor_attachment_upload_path)

    kind = models.CharField(
        max_length=20,
        choices=VendorAttachmentKind.choices,
        default=VendorAttachmentKind.OTHER,
        db_index=True,
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "recon_vendor_attachment"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["work_item", "kind", "created_at"]),
        ]

    def __str__(self):
        return f"Att#{self.pk} on WorkItem#{self.work_item_id}"