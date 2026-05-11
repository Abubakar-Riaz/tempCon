# vendors/serializers.py

from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from accounts.models import DealershipMembership
from recon.models import VendorAttachment, VendorAttachmentKind, WorkItem


class DealershipVendorSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = DealershipMembership
        fields = (
            "id",
            "user",
            "status",
            "created_at",
        )

    def get_user(self, obj):
        return {
            "id": obj.user.public_id,
            "email": obj.user.email,
            "name": obj.user.display_name,
        }


class VendorWorkItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    trade = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    attachments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkItem
        fields = (
            "id",
            "vehicle",
            "trade",
            "status",
            "priority",
            "due_date",
            "est_cost",
            "est_time_minutes",
            "actual_cost",
            "actual_time_minutes",
            "completion_date",
            "notes",
            "attachments_count",
            "created_at",
            "updated_at",
        )

    def get_vehicle(self, obj):
        vehicle = obj.recon_case.vehicle

        return {
            "id": vehicle.public_id,
            "vin": vehicle.vin,
            "status": vehicle.status,
        }

    def get_trade(self, obj):
        return {
            "id": obj.trade.public_id,
            "key": obj.trade.key,
            "label": obj.trade.label,
        }


class VendorWorkItemCompleteSerializer(serializers.Serializer):
    actual_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    actual_time_minutes = serializers.IntegerField(
        required=False,
        min_value=0,
        allow_null=True,
    )
    completion_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class VendorAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    kind = serializers.ChoiceField(
        choices=VendorAttachmentKind.values,
        required=False,
        default=VendorAttachmentKind.OTHER,
    )
    metadata = serializers.JSONField(required=False)


class VendorAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    filename = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = VendorAttachment
        fields = (
            "id",
            "kind",
            "filename",
            "url",
            "metadata",
            "uploaded_by",
            "created_at",
        )

    def get_filename(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def get_url(self, obj):
        return obj.file.url if obj.file else None

    def get_uploaded_by(self, obj):
        user = obj.uploaded_by_user

        if not user:
            return None

        return {
            "id": user.public_id,
            "email": user.email,
            "name": user.display_name,
        }