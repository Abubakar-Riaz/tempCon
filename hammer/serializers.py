# hammer/serializers.py

from decimal import Decimal

from rest_framework import serializers

from hammer.models import HammerLineItem, HammerSession, HammerSessionStatus


class HammerLineUpsertSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    est_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
    )
    est_time_minutes = serializers.IntegerField(required=False, min_value=0, default=0)
    attributes = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class HammerUpsertSerializer(serializers.Serializer):
    lines = HammerLineUpsertSerializer(many=True, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    calculator = serializers.JSONField(required=False)
    finalize = serializers.BooleanField(required=False, default=False)


class HammerLineItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    inspection_item = serializers.SerializerMethodField()

    class Meta:
        model = HammerLineItem
        fields = (
            "id",
            "inspection_item",
            "est_cost",
            "est_time_minutes",
            "attributes",
            "notes",
            "created_at",
            "updated_at",
        )

    def get_inspection_item(self, obj):
        item = obj.inspection_item

        return {
            "id": item.public_id,
            "label": item.label,
            "status": item.status,
            "trade": {
                "id": item.trade.public_id,
                "key": item.trade.key,
                "label": item.trade.label,
            },
        }


class HammerSessionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    manager = serializers.SerializerMethodField()
    lines = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = HammerSession
        fields = (
            "id",
            "status",
            "est_cost_total",
            "est_time_total_minutes",
            "derived",
            "notes",
            "started_at",
            "completed_at",
            "manager",
            "lines",
            "permissions",
        )

    def get_manager(self, obj):
        if not obj.manager:
            return None

        return {
            "id": obj.manager.public_id,
            "email": obj.manager.email,
            "name": obj.manager.display_name,
        }

    def get_lines(self, obj):
        return HammerLineItemSerializer(
            obj.lines_with_items,
            many=True,
        ).data

    def get_permissions(self, obj):
        return self.context.get("permissions", {})