# recon/serializers.py

from rest_framework import serializers

from recon.models import ReconCase, ReconStatus, WorkItem, WorkItemStatus, Priority


class ReconStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[ReconStatus.FAIL, ReconStatus.COMPLETE])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    notes = serializers.CharField(required=False, allow_blank=True)


class AssignVendorSerializer(serializers.Serializer):
    vendor_membership_id = serializers.UUIDField()
    priority = serializers.ChoiceField(choices=Priority.values, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ReconCaseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    recon_manager = serializers.SerializerMethodField()

    class Meta:
        model = ReconCase
        fields = (
            "id",
            "status",
            "fail_reason",
            "notes",
            "opened_at",
            "closed_at",
            "recon_manager",
            "created_at",
            "updated_at",
        )

    def get_recon_manager(self, obj):
        if not obj.recon_manager:
            return None

        return {
            "id": obj.recon_manager.public_id,
            "email": obj.recon_manager.email,
            "name": obj.recon_manager.display_name,
        }


class WorkItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    trade = serializers.SerializerMethodField()
    source_inspection_item = serializers.SerializerMethodField()
    assigned_vendor = serializers.SerializerMethodField()

    class Meta:
        model = WorkItem
        fields = (
            "id",
            "trade",
            "source_inspection_item",
            "assigned_vendor",
            "status",
            "priority",
            "due_date",
            "est_cost",
            "est_time_minutes",
            "actual_cost",
            "actual_time_minutes",
            "completion_date",
            "notes",
            "created_at",
            "updated_at",
        )

    def get_trade(self, obj):
        return {
            "id": obj.trade.public_id,
            "key": obj.trade.key,
            "label": obj.trade.label,
        }

    def get_source_inspection_item(self, obj):
        if not obj.source_inspection_item:
            return None

        return {
            "id": obj.source_inspection_item.public_id,
            "label": obj.source_inspection_item.label,
            "status": obj.source_inspection_item.status,
        }

    def get_assigned_vendor(self, obj):
        membership = obj.assigned_vendor

        if not membership:
            return None

        return {
            "id": membership.public_id,
            "user": {
                "id": membership.user.public_id,
                "email": membership.user.email,
                "name": membership.user.display_name,
            },
        }