# inventory/models.py

import os
import re
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import Company, Dealership
from core.models.base import PublicIDModel, TimestampedModel


class FolderType(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTO_INSPECTION_DAILY = "auto_inspection_daily", "Auto Daily - Inspection"
    AUTO_BUYING_DAILY = "auto_buying_daily", "Auto Daily - Buying"
    AUTO_RECON_DAILY = "auto_recon_daily", "Auto Daily - Recon"
    AUTO_VENDOR_DAILY = "auto_vendor_daily", "Auto Daily - Vendor"


class VehicleStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    VHR = "vhr", "VHR"
    INSPECTION = "inspection", "Inspection"
    HAMMER = "hammer", "Hammer"
    BUYING = "buying", "Buying"
    RECON = "recon", "Recon"
    RECON_FAIL = "recon_fail", "Recon Fail"
    COMPLETE = "complete", "Complete"


class VehicleSource(models.TextChoices):
    CSV = "csv", "CSV Upload"
    MANUAL = "manual", "Manual Entry"
    AUCTION = "auction", "Auction"


class AttachmentPhase(models.TextChoices):
    VHR = "vhr", "VHR"
    INSPECTION = "inspection", "Inspection"
    HAMMER = "hammer", "Hammer"
    BUYING = "buying", "Buying"
    RECON = "recon", "Recon"
    VENDOR = "vendor", "Vendor"
    OTHER = "other", "Other"


class NoteVisibility(models.TextChoices):
    INTERNAL = "internal", "Internal"
    VENDOR = "vendor", "Vendor-visible"


class VHRFieldType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    DATE = "date", "Date"
    BOOL = "bool", "Boolean"
    ENUM = "enum", "Enum"


class VHRField(PublicIDModel, TimestampedModel):
    key = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    data_type = models.CharField(max_length=12, choices=VHRFieldType.choices)

    group = models.CharField(max_length=64, blank=True, default="")
    help_text = models.CharField(max_length=255, blank=True, default="")

    options = models.JSONField(default=dict, blank=True)

    order_index = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "inventory_vhr_field"
        ordering = ("order_index", "label")
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["is_active", "order_index"]),
            models.Index(fields=["group", "order_index"]),
        ]

    def __str__(self):
        return self.label


class VHRFieldSetting(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vhr_field_settings",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="vhr_field_settings",
    )

    field = models.ForeignKey(
        VHRField,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    required = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)

    constraints = models.JSONField(default=dict, blank=True)
    default_value = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "inventory_vhr_field_setting"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "dealership"]),
            models.Index(fields=["company", "field"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "dealership", "field"],
                name="uniq_vhr_field_setting_per_scope",
            ),
        ]

    def __str__(self):
        scope = self.dealership.name if self.dealership_id else self.company.name
        return f"{scope} - {self.field.label}"


class Folder(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="folders",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="folders",
    )

    name = models.CharField(max_length=255)

    type = models.CharField(
        max_length=32,
        choices=FolderType.choices,
        default=FolderType.MANUAL,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_folders",
    )

    date_bucket = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "inventory_folder"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["dealership", "created_at"]),
            models.Index(fields=["dealership", "name"]),
            models.Index(fields=["dealership", "type", "date_bucket"]),
            models.Index(fields=["dealership", "created_by", "type", "date_bucket"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "dealership", "name"],
                condition=Q(type=FolderType.MANUAL),
                name="uniq_manual_folder_name_per_store",
            ),
            models.UniqueConstraint(
                fields=["company", "dealership", "type", "date_bucket", "created_by"],
                condition=Q(
                    type__in=[
                        FolderType.AUTO_INSPECTION_DAILY,
                        FolderType.AUTO_BUYING_DAILY,
                        FolderType.AUTO_RECON_DAILY,
                        FolderType.AUTO_VENDOR_DAILY,
                    ]
                ),
                name="uniq_auto_daily_per_user_phase_day",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.dealership_id:
            self.company_id = self.dealership.company_id
        super().save(*args, **kwargs)


class Vehicle(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )

    vin = models.CharField(max_length=17)
    stock_no = models.CharField(max_length=64, blank=True, default="")

    year = models.PositiveIntegerField(null=True, blank=True)
    make = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=64, blank=True, default="")
    trim = models.CharField(max_length=64, blank=True, default="")

    run_number = models.CharField(max_length=32, blank=True, default="")
    auction_house = models.CharField(max_length=255, blank=True, default="")
    auction_sale_lane = models.CharField(max_length=64, blank=True, default="")
    auction_start_at = models.DateTimeField(null=True, blank=True)

    main_description = models.CharField(max_length=255, blank=True, default="")
    secondary_description = models.CharField(max_length=255, blank=True, default="")

    title_status = models.CharField(max_length=64, blank=True, default="")
    condition_grade = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    mmr = models.PositiveIntegerField(null=True, blank=True)

    mileage = models.PositiveIntegerField(null=True, blank=True)
    engine = models.CharField(max_length=64, blank=True, default="")
    transmission = models.CharField(max_length=64, blank=True, default="")
    exterior_color = models.CharField(max_length=64, blank=True, default="")
    interior_color = models.CharField(max_length=64, blank=True, default="")

    consignor_name = models.CharField(max_length=255, blank=True, default="")
    consignor_email = models.EmailField(blank=True, default="")
    consignor_address = models.TextField(blank=True, default="")
    auction_notes = models.TextField(blank=True, default="")

    import_payload = models.JSONField(default=dict, blank=True)

    source = models.CharField(
        max_length=16,
        choices=VehicleSource.choices,
        default=VehicleSource.MANUAL,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        default=VehicleStatus.UPLOADED,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vehicles",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_vehicles",
    )

    vhr_at = models.DateTimeField(null=True, blank=True)
    inspection_at = models.DateTimeField(null=True, blank=True)
    hammer_at = models.DateTimeField(null=True, blank=True)
    buying_at = models.DateTimeField(null=True, blank=True)
    recon_at = models.DateTimeField(null=True, blank=True)
    complete_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_vehicle"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "dealership", "status", "updated_at"]),
            models.Index(fields=["dealership", "vin"]),
            models.Index(fields=["dealership", "stock_no"]),
            models.Index(fields=["run_number"]),
            models.Index(fields=["auction_house", "auction_start_at"]),
            models.Index(fields=["dealership", "created_at"]),
            models.Index(fields=["updated_by", "updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["dealership", "vin"],
                name="uniq_vehicle_vin_per_dealership",
            ),
        ]

    def __str__(self):
        label = f"{self.year or ''} {self.make} {self.model}".strip()
        return f"{label} [{self.vin or 'NO-VIN'}]"

    def save(self, *args, **kwargs):
        if self.dealership_id:
            self.company_id = self.dealership.company_id

        if self.vin:
            self.vin = self.vin.strip().upper()

        super().save(*args, **kwargs)


class FolderVehicle(PublicIDModel, TimestampedModel):
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="folder_links",
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="folder_links",
    )

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="folder_vehicle_links",
    )

    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "inventory_folder_vehicle"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["folder", "created_at"]),
            models.Index(fields=["vehicle", "folder"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["folder", "vehicle"],
                name="uniq_folder_vehicle",
            ),
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(is_primary=True),
                name="uniq_primary_folder_per_vehicle",
            ),
        ]

    def __str__(self):
        return f"{self.folder_id} - {self.vehicle_id}"


class VehicleHistoryReport(PublicIDModel, TimestampedModel):
    vehicle = models.OneToOneField(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="vhr",
    )

    data = models.JSONField(default=dict, blank=True)
    required_config_snapshot = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vhrs",
    )

    class Meta:
        db_table = "inventory_vehicle_history_report"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["vehicle", "created_at"]),
        ]

    def __str__(self):
        return f"VHR for {self.vehicle_id}"


class Note(PublicIDModel, TimestampedModel):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="notes",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_notes",
    )

    visibility = models.CharField(
        max_length=16,
        choices=NoteVisibility.choices,
        default=NoteVisibility.INTERNAL,
        db_index=True,
    )

    body = models.TextField()

    class Meta:
        db_table = "inventory_note"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["vehicle", "created_at"]),
            models.Index(fields=["visibility", "created_at"]),
        ]

    def __str__(self):
        return f"Note#{self.pk} on Vehicle#{self.vehicle_id}"


def _sanitize_vin(v: str) -> str:
    s = (v or "").strip().upper()
    s = re.sub(r"[^A-Z0-9]", "-", s)
    return s or "NO-VIN"


def _sanitize_filename(name: str, randomize: bool = False) -> str:
    base, ext = os.path.splitext(os.path.basename(name))

    if randomize:
        base = uuid.uuid4().hex
    else:
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", (base or "file"))

    return (base or "file") + (ext or "")


def _attachment_upload_path(instance, filename):
    d = timezone.now()
    phase = (getattr(instance, "phase_tag", "") or "other").lower()
    vin = _sanitize_vin(getattr(instance.vehicle, "vin", None))
    safe_name = _sanitize_filename(filename, randomize=True)
    return f"vehicle_attachments/{d:%Y/%m/%d}/{phase}/{vin}/{safe_name}"


class Attachment(PublicIDModel, TimestampedModel):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_attachments",
    )

    file = models.FileField(upload_to=_attachment_upload_path)

    phase_tag = models.CharField(
        max_length=16,
        choices=AttachmentPhase.choices,
        default=AttachmentPhase.OTHER,
        db_index=True,
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "inventory_attachment"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["vehicle", "phase_tag", "created_at"]),
        ]

    def __str__(self):
        return f"Att#{self.pk} v{self.vehicle_id} {self.phase_tag}"


class HistoryEventKind(models.TextChoices):
    VEHICLE_CREATED = "vehicle_created", "Vehicle Created"
    STATUS_CHANGED = "status_changed", "Status Changed"

    VHR_STARTED = "vhr_started", "VHR Started"
    VHR_COMPLETED = "vhr_completed", "VHR Completed"

    INSPECTION_STARTED = "inspection_started", "Inspection Started"
    INSPECTION_COMPLETED = "inspection_completed", "Inspection Completed"

    HAMMER_STARTED = "hammer_started", "Hammer Started"
    HAMMER_FINALIZED = "hammer_finalized", "Hammer Finalized"

    BUYING_DECIDED = "buying_decided", "Buying Decided"

    RECON_STARTED = "recon_started", "Recon Started"
    RECON_FAILED = "recon_failed", "Recon Failed"
    RECON_COMPLETED = "recon_completed", "Recon Completed"

    VEHICLE_COMPLETED = "vehicle_completed", "Vehicle Completed"

    NOTE_ADDED = "note_added", "Note Added"
    ATTACHMENT_ADDED = "attachment_added", "Attachment Added"
    FOLDER_ADDED = "folder_added", "Folder Added"
    ASSIGNED = "assigned", "Assigned"
    UNASSIGNED = "unassigned", "Unassigned"

    OTHER = "other", "Other"


class HistoryEvent(PublicIDModel, TimestampedModel):
    """
    Append-only vehicle timeline.

    This powers the vehicle pipeline history. Use `from_status` and `to_status`
    for pipeline movement, and `kind` for non-status timeline events.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vehicle_history_events",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="vehicle_history_events",
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="history",
    )

    kind = models.CharField(
        max_length=40,
        choices=HistoryEventKind.choices,
        default=HistoryEventKind.OTHER,
        db_index=True,
    )

    from_status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        blank=True,
        default="",
        db_index=True,
    )

    to_status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        blank=True,
        default="",
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_events",
    )

    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")

    payload = models.JSONField(default=dict, blank=True)

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "inventory_history_event"
        ordering = ("-occurred_at", "-created_at")
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "occurred_at"]),
            models.Index(fields=["dealership", "occurred_at"]),
            models.Index(fields=["vehicle", "occurred_at"]),
            models.Index(fields=["vehicle", "to_status", "occurred_at"]),
            models.Index(fields=["kind", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.kind} on v{self.vehicle_id} @ {self.occurred_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.vehicle_id:
            self.company_id = self.vehicle.company_id
            self.dealership_id = self.vehicle.dealership_id

        if not self.title:
            self.title = self.get_kind_display()

        super().save(*args, **kwargs)