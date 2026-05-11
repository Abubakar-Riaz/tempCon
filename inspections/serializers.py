# inspections/serializers.py

from rest_framework import serializers

from inspections.models import Inspection, InspectionItem, InspectionItemAttachment, Trade


class TradeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Trade
        fields = (
            "id",
            "key",
            "label",
            "description",
            "order_index",
        )


class InspectionItemAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    caption = serializers.CharField(required=False, allow_blank=True, max_length=255)
    metadata = serializers.JSONField(required=False)


class InspectionAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    filename = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    caption = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = InspectionItemAttachment
        fields = (
            "id",
            "filename",
            "url",
            "caption",
            "uploaded_by",
            "created_at",
        )

    def get_filename(self, obj):
        file = obj.attachment.file
        return file.name.rsplit("/", 1)[-1] if file else None

    def get_url(self, obj):
        file = obj.attachment.file
        return file.url if file else None

    def get_caption(self, obj):
        return (obj.attachment.metadata or {}).get("caption") or None

    def get_uploaded_by(self, obj):
        user = obj.attachment.uploaded_by

        if not user:
            return None

        return {
            "id": user.public_id,
            "email": user.email,
            "name": user.display_name,
        }


class InspectionItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    trade = serializers.SerializerMethodField()
    attachments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InspectionItem
        fields = (
            "id",
            "trade",
            "trade_label",
            "label",
            "status",
            "notes",
            "attachments_count",
            "created_at",
            "updated_at",
        )

    def get_trade(self, obj):
        return {
            "id": obj.trade.public_id,
            "key": obj.trade.key,
            "label": obj.trade.label,
        }


class InspectionDetailSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    inspector = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = (
            "id",
            "status",
            "started_at",
            "completed_at",
            "notes",
            "items_total",
            "items_ok",
            "items_needs_attention",
            "inspector",
            "items",
            "permissions",
        )

    def get_inspector(self, obj):
        if not obj.inspector:
            return None

        return {
            "id": obj.inspector.public_id,
            "email": obj.inspector.email,
            "name": obj.inspector.display_name,
        }

    def get_items(self, obj):
        return InspectionItemSerializer(
            obj.items_with_counts,
            many=True,
        ).data

    def get_permissions(self, obj):
        return self.context.get("permissions", {})